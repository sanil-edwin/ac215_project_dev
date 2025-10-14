"""
Download Iowa corn masks and county boundaries
Uploads to Google Cloud Storage
Checks GCS first and only downloads missing years

Data Sources:
1. USDA NASS Cropland Data Layer (CDL) - Corn masks (2017-current year)
2. US Census TIGER/Line - Iowa county boundaries
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import zipfile
import logging
from typing import List, Optional
from datetime import datetime
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from tqdm import tqdm

from utils.gcs_utils import GCSManager, get_gcs_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MaskDownloader:
    """Download and process Iowa corn masks and county boundaries"""
    
    # USDA NASS CDL download URLs
    CDL_BASE_URL = "https://www.nass.usda.gov/Research_and_Science/Cropland/Release/datasets"
    
    # Census TIGER/Line URL for counties
    TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip"
    
    # Iowa state FIPS code
    IOWA_FIPS = "19"
    
    # CDL crop codes
    CORN_CODE = 1
    
    def __init__(self, temp_dir: str = "./temp", gcs_manager: Optional[GCSManager] = None):
        """
        Initialize mask downloader
        
        Args:
            temp_dir: Temporary directory for downloads
            gcs_manager: GCS manager for cloud uploads (optional)
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.gcs_manager = gcs_manager
        
        logger.info(f"Initialized MaskDownloader with temp_dir: {self.temp_dir}")
        if gcs_manager:
            logger.info(f"GCS uploads enabled to: {gcs_manager.bucket_name}")
    
    def download_file(self, url: str, output_path: Path, desc: str = "Downloading") -> Path:
        """
        Download a file with progress bar
        
        Args:
            url: URL to download
            output_path: Local path to save file
            desc: Description for progress bar
            
        Returns:
            Path to downloaded file
        """
        logger.info(f"Downloading from {url}")
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check if we got actual content
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            logger.error(f"Received HTML instead of file. URL may be incorrect.")
            raise ValueError(f"Invalid response from {url}")
        
        total_size = int(response.headers.get('content-length', 0))
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f, tqdm(
            desc=desc,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                pbar.update(size)
        
        logger.info(f"Downloaded to {output_path} ({output_path.stat().st_size} bytes)")
        return output_path
    
    def download_iowa_counties(self) -> gpd.GeoDataFrame:
        """
        Download Iowa county boundaries from Census TIGER/Line
        
        Returns:
            GeoDataFrame with Iowa counties
        """
        logger.info("Downloading Iowa county boundaries...")
        
        # Download TIGER/Line shapefile
        zip_path = self.temp_dir / "counties.zip"
        self.download_file(self.TIGER_URL, zip_path, desc="Downloading US Counties")
        
        # Extract
        extract_dir = self.temp_dir / "counties"
        extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Read shapefile
        shp_file = list(extract_dir.glob("*.shp"))[0]
        gdf = gpd.read_file(shp_file)
        
        # Filter to Iowa (FIPS code 19)
        iowa_counties = gdf[gdf['STATEFP'] == self.IOWA_FIPS].copy()
        
        logger.info(f"Found {len(iowa_counties)} Iowa counties")
        
        # Clean up column names
        iowa_counties = iowa_counties[['STATEFP', 'COUNTYFP', 'NAME', 'geometry']]
        iowa_counties['fips'] = iowa_counties['STATEFP'] + iowa_counties['COUNTYFP']
        
        # Save locally
        output_path = self.temp_dir / "iowa_counties.geojson"
        iowa_counties.to_file(output_path, driver='GeoJSON')
        logger.info(f"Saved Iowa counties to {output_path}")
        
        # Upload to GCS
        if self.gcs_manager:
            gcs_path = "raw/masks/iowa_counties.geojson"
            self.gcs_manager.upload_geodataframe(iowa_counties, gcs_path, format='geojson')
            logger.info(f"Uploaded counties to GCS: gs://{self.gcs_manager.bucket_name}/{gcs_path}")
        
        return iowa_counties
    
    def download_cdl_year(self, year: int, iowa_counties: gpd.GeoDataFrame) -> Optional[Path]:
        """
        Download and process CDL for a specific year
        
        Args:
            year: Year to download (2017-current)
            iowa_counties: Iowa county boundaries for clipping
            
        Returns:
            Path to processed corn mask GeoTIFF (or None if failed)
        """
        logger.info(f"Processing CDL for year {year}...")
        
        # Construct CDL download URL
        cdl_url = f"{self.CDL_BASE_URL}/{year}_30m_cdls.zip"
        
        zip_path = self.temp_dir / f"cdl_{year}.zip"
        
        try:
            # Download CDL
            self.download_file(cdl_url, zip_path, desc=f"CDL {year}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to download CDL for {year}: {e}")
            logger.info("Trying alternative URL pattern...")
            
            # Try alternative URL pattern
            cdl_url_alt = f"{self.CDL_BASE_URL}/{year}_30m_cdls.tif"
            try:
                tif_path = self.temp_dir / f"cdl_{year}.tif"
                self.download_file(cdl_url_alt, tif_path, desc=f"CDL {year} (alt)")
            except Exception as e2:
                logger.error(f"Alternative download also failed: {e2}")
                logger.warning(f"Skipping year {year}")
                return None
        
        # Extract if we got a zip file
        if zip_path.exists():
            extract_dir = self.temp_dir / f"cdl_{year}"
            extract_dir.mkdir(exist_ok=True)
            
            logger.info(f"Extracting {zip_path}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the TIF file
            tif_files = list(extract_dir.glob("*.tif"))
            if not tif_files:
                logger.error(f"No TIF file found in extracted CDL for {year}")
                return None
            
            tif_path = tif_files[0]
        
        # Process raster: clip to Iowa and create corn mask
        logger.info(f"Processing {tif_path.name}...")
        corn_mask_path = self.create_corn_mask(tif_path, iowa_counties, year)
        
        return corn_mask_path
    
    def create_corn_mask(
        self, 
        cdl_path: Path, 
        iowa_counties: gpd.GeoDataFrame, 
        year: int
    ) -> Path:
        """
        Create binary corn mask from CDL data
        
        Args:
            cdl_path: Path to CDL GeoTIFF
            iowa_counties: Iowa county boundaries
            year: Year of data
            
        Returns:
            Path to corn mask GeoTIFF
        """
        logger.info(f"Creating corn mask for {year}...")
        
        with rasterio.open(cdl_path) as src:
            # Reproject Iowa counties to match CDL CRS
            iowa_proj = iowa_counties.to_crs(src.crs)
            
            # Get Iowa bounding box
            minx, miny, maxx, maxy = iowa_proj.total_bounds
            
            # Read CDL data for Iowa extent
            logger.info("Reading and clipping CDL data to Iowa...")
            window = src.window(minx, miny, maxx, maxy)
            cdl_data = src.read(1, window=window)
            
            # Get window transform
            window_transform = src.window_transform(window)
            
            # Create binary corn mask (1 = corn, 0 = other)
            corn_mask = (cdl_data == self.CORN_CODE).astype(np.uint8)
            
            # Count corn pixels
            corn_pixels = np.sum(corn_mask == 1)
            total_pixels = corn_mask.size
            corn_pct = (corn_pixels / total_pixels) * 100
            
            logger.info(f"  Corn coverage: {corn_pct:.2f}% ({corn_pixels:,} pixels)")
            
            # Save corn mask
            output_path = self.temp_dir / f"iowa_corn_mask_{year}.tif"
            
            profile = src.profile.copy()
            profile.update({
                'dtype': 'uint8',
                'count': 1,
                'compress': 'lzw',
                'width': corn_mask.shape[1],
                'height': corn_mask.shape[0],
                'transform': window_transform
            })
            
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(corn_mask, 1)
            
            logger.info(f"Saved corn mask to {output_path}")
            
            # Upload to GCS
            if self.gcs_manager:
                gcs_path = f"raw/masks/corn/iowa_corn_mask_{year}.tif"
                self.gcs_manager.upload_file(str(output_path), gcs_path)
                logger.info(f"Uploaded to GCS: gs://{self.gcs_manager.bucket_name}/{gcs_path}")
            
            return output_path
    
    def download_all_masks(self, years: List[int] = None, start_year: int = 2017) -> dict:
        """
        Download all masks: counties + corn masks for all years
        Checks GCS first and only downloads missing years
        
        Args:
            years: List of years to download (default: start_year to current year)
            start_year: First year to download (default: 2017)
            
        Returns:
            Dictionary with paths and statistics
        """
        if years is None:
            # Automatically determine years from start_year to current year
            current_year = datetime.now().year
            years = list(range(start_year, current_year + 1))
            logger.info(f"Auto-detected year range: {start_year}-{current_year}")
        
        logger.info("\n" + "="*70)
        logger.info("  IOWA CORN MASKS - Checking GCS Bucket for Existing Data")
        logger.info("="*70)
        logger.info(f"  Bucket: gs://{self.gcs_manager.bucket_name if self.gcs_manager else 'N/A'}")
        logger.info(f"  Years to check: {start_year} to {datetime.now().year} ({len(years)} total)")
        logger.info(f"  Location: raw/masks/corn/")
        logger.info("="*70)
        
        results = {
            'counties': None,
            'corn_masks': {},
            'successful_years': [],
            'failed_years': [],
            'skipped_years': [],
            'missing_years': []
        }
        
        # Check which years are missing from GCS
        if self.gcs_manager:
            logger.info("\n📋 Checking which corn mask years exist in GCS...")
            logger.info("-" * 70)
            for year in years:
                mask_gcs_path = f"raw/masks/corn/iowa_corn_mask_{year}.tif"
                if self.gcs_manager.blob_exists(mask_gcs_path):
                    logger.info(f"  ✓ {year}: Corn mask found in GCS")
                    results['skipped_years'].append(year)
                    results['successful_years'].append(year)
                else:
                    logger.info(f"  ✗ {year}: Corn mask MISSING from GCS")
                    results['missing_years'].append(year)
            logger.info("-" * 70)
            
            # If nothing is missing, we're done!
            if not results['missing_years']:
                logger.info("\n" + "="*70)
                logger.info("  ✅ ALL CORN MASKS ALREADY EXIST - NOTHING TO DOWNLOAD")
                logger.info("="*70)
                logger.info(f"  All years from {start_year} to {datetime.now().year} are present")
                logger.info(f"  Location: gs://{self.gcs_manager.bucket_name}/raw/masks/corn/")
                logger.info(f"  Total masks: {len(results['skipped_years'])} corn mask files")
                logger.info("="*70)
                logger.info("\n✨ No action needed - your data is complete!")
                return results
            
            logger.info(f"\n📥 Need to download {len(results['missing_years'])} missing corn mask(s):")
            logger.info(f"   Years: {results['missing_years']}")
        else:
            logger.warning("⚠️  No GCS manager - will download all years")
            results['missing_years'] = years
        
        logger.info("\n" + "="*70)
        logger.info("  🌽 STARTING CORN MASK DOWNLOAD FOR IOWA")
        logger.info("="*70)
        
        # Step 1: Check/Download Iowa counties
        logger.info("\nStep 1: Checking Iowa county boundaries...")
        
        counties_path = "raw/masks/iowa_counties.geojson"
        if self.gcs_manager and self.gcs_manager.blob_exists(counties_path):
            logger.info(f"✓ Counties already exist in GCS")
        
        # Always download counties locally for processing (small file)
        try:
            iowa_counties = self.download_iowa_counties()
            results['counties'] = iowa_counties
            logger.info("✓ Counties ready for processing")
        except Exception as e:
            logger.error(f"✗ Failed to prepare counties: {e}")
            raise
        
        # Step 2: Download only missing years
        years_to_download = results['missing_years']
        logger.info(f"\nStep 2: Downloading {len(years_to_download)} missing corn masks...")
        
        for year in years_to_download:
            logger.info(f"\n--- Processing year {year} ---")
            
            try:
                mask_path = self.download_cdl_year(year, iowa_counties)
                if mask_path:
                    results['corn_masks'][year] = mask_path
                    results['successful_years'].append(year)
                    logger.info(f"✓ Year {year} completed")
                else:
                    results['failed_years'].append(year)
                    logger.warning(f"⚠ Year {year} skipped (download failed)")
            except Exception as e:
                logger.error(f"✗ Year {year} failed: {e}")
                results['failed_years'].append(year)
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("  MASK DOWNLOAD SUMMARY")
        logger.info("="*70)
        logger.info(f"  Total years checked: {len(years)}")
        logger.info(f"  Already existed: {len(results['skipped_years'])} years")
        if results['skipped_years']:
            logger.info(f"    Existing: {results['skipped_years']}")
        downloaded = [y for y in results['successful_years'] if y not in results['skipped_years']]
        logger.info(f"  Downloaded: {len(downloaded)} years")
        if downloaded:
            logger.info(f"    New: {downloaded}")
        if results['failed_years']:
            logger.info(f"  Failed: {len(results['failed_years'])} years")
            logger.info(f"    Failed: {results['failed_years']}")
        
        if self.gcs_manager:
            logger.info(f"\n  ✓ All data in: gs://{self.gcs_manager.bucket_name}/raw/masks/")
        
        logger.info("="*70)
        
        return results


def main():
    """Main execution function"""
    
    # Get configuration from environment
    start_year = int(os.getenv("START_YEAR", "2017"))
    current_year = datetime.now().year
    
    # Allow manual override via environment variable
    years_str = os.getenv("MASK_YEARS")
    if years_str:
        years = [int(y.strip()) for y in years_str.split(",")]
        logger.info(f"Using manually specified years: {years}")
    else:
        years = None  # Will auto-detect in download_all_masks
        logger.info(f"Will download data from {start_year} to {current_year}")
    
    temp_dir = os.getenv("TEMP_DIR", "./temp")
    
    # Initialize GCS manager
    try:
        gcs_manager = get_gcs_manager()
        logger.info(f"✓ Connected to GCS bucket: {gcs_manager.bucket_name}")
    except Exception as e:
        logger.warning(f"Could not initialize GCS: {e}")
        logger.info("Proceeding with local storage only")
        gcs_manager = None
    
    # Initialize downloader
    downloader = MaskDownloader(temp_dir=temp_dir, gcs_manager=gcs_manager)
    
    # Download all masks
    results = downloader.download_all_masks(years=years, start_year=start_year)
    
    # Print final status
    if results['failed_years']:
        logger.warning(f"\n⚠ Some years failed: {results['failed_years']}")
        logger.info("You may need to manually download these years from:")
        logger.info("https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php")
    else:
        logger.info("\n✓ All masks downloaded successfully!")


if __name__ == "__main__":
    main()
