"""
Download agricultural stress indicators for Iowa corn counties using Google Earth Engine
Handles all projection, resampling, and aggregation automatically

Data Sources (All via Google Earth Engine):

VEGETATION HEALTH:
1. MODIS NDVI/EVI (MOD13A1) - 500m, 16-day composite
   - Normalized Difference Vegetation Index
   - Enhanced Vegetation Index

WATER STRESS INDICATORS:
2. MODIS ET (MOD16A2GF) - 500m, 8-day composite
   - Evapotranspiration (ET)
   - Potential Evapotranspiration (PET)

3. CHIRPS Precipitation - 5km, daily (aggregated to 8-day)
   - Rainfall amount
   - Climate Hazards Group InfraRed Precipitation

HEAT STRESS INDICATORS:
4. MODIS LST (MOD11A2) - 1km, 8-day composite
   - Land Surface Temperature Day
   - Land Surface Temperature Night

5. gridMET VPD - 4km, daily (aggregated to 8-day)
   - Vapor Pressure Deficit
   - Atmospheric dryness indicator

Workflow:
- Load Iowa county boundaries from GCS
- Use GEE to aggregate indicators to county level
- Skip products that already exist in GCS
- Export results to GCS as Parquet files
- Output: One file per indicator per date range
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
import geopandas as gpd

import ee
from tqdm import tqdm

from utils.gcs_utils import GCSManager, get_gcs_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GEEMODISDownloader:
    """Download and process agricultural indicators using Google Earth Engine"""
    
    # Available products
    PRODUCTS = {
        'vegetation': ['ndvi', 'evi'],  # Vegetation health
        'water_stress': ['et'],  # Water indicators
        'heat_stress': ['lst']  # Temperature indicators
    }
    
    def __init__(
        self,
        temp_dir: str = "./temp",
        gcs_manager: Optional[GCSManager] = None,
        gcp_project: Optional[str] = None
    ):
        """
        Initialize GEE MODIS downloader
        
        Args:
            temp_dir: Temporary directory
            gcs_manager: GCS manager for storage
            gcp_project: GCP project ID for Earth Engine
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.gcs_manager = gcs_manager
        self.gcp_project = gcp_project or os.getenv("GCP_PROJECT_ID")
        
        # Initialize Earth Engine
        self._initialize_ee()
        
        # Cache
        self.iowa_counties = None
        self.corn_masks = {}
        
        logger.info(f"Initialized GEEMODISDownloader")
        logger.info(f"  GCP Project: {self.gcp_project}")
    
    def _initialize_ee(self):
        """Initialize Google Earth Engine with service account"""
        try:
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if credentials_path and os.path.exists(credentials_path):
                # Use service account authentication
                logger.info(f"Authenticating with service account: {credentials_path}")
                
                # Read service account email from credentials file
                import json
                with open(credentials_path, 'r') as f:
                    key_data = json.load(f)
                    service_account = key_data.get('client_email')
                
                credentials = ee.ServiceAccountCredentials(
                    service_account,
                    credentials_path
                )
                ee.Initialize(credentials=credentials, project=self.gcp_project)
                logger.info(f"✓ Google Earth Engine initialized with service account")
            elif self.gcp_project:
                # Try project-based authentication
                ee.Initialize(project=self.gcp_project)
                logger.info(f"✓ Google Earth Engine initialized with project: {self.gcp_project}")
            else:
                # Default authentication
                ee.Initialize()
                logger.info("✓ Google Earth Engine initialized with default credentials")
                
        except Exception as e:
            logger.error(f"Failed to initialize Earth Engine: {e}")
            logger.info("\nTroubleshooting:")
            logger.info("1. Make sure Earth Engine API is enabled in your GCP project")
            logger.info("2. Your service account needs 'Earth Engine Resource Viewer' role")
            logger.info("3. Register your GCP project at: https://code.earthengine.google.com/")
            raise
    
    def load_iowa_counties(self) -> gpd.GeoDataFrame:
        """Load Iowa county boundaries from GCS"""
        if self.iowa_counties is not None:
            return self.iowa_counties
        
        logger.info("Loading Iowa county boundaries...")
        
        local_path = self.temp_dir / "iowa_counties.geojson"
        self.gcs_manager.download_file(
            "raw/masks/iowa_counties.geojson",
            str(local_path)
        )
        
        self.iowa_counties = gpd.read_file(local_path)
        logger.info(f"✓ Loaded {len(self.iowa_counties)} Iowa counties")
        return self.iowa_counties
    
    def _check_existing_data(
        self,
        product: str,
        start_date: datetime,
        end_date: datetime
    ) -> Tuple[bool, str]:
        """
        Check if data already exists in GCS for the given product and date range
        
        Args:
            product: Product name (e.g., 'ndvi', 'et')
            start_date: Start date
            end_date: End date
            
        Returns:
            Tuple of (exists: bool, path: str)
        """
        if not self.gcs_manager:
            return False, ""
        
        # Check both possible directory structures (prioritize modis)
        possible_paths = [
            # Primary structure: processed/modis/{product}/
            f"processed/modis/{product}/iowa_counties_{product}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.parquet",
            # Alternative structure: processed/indicators/{product}/
            f"processed/indicators/{product}/iowa_counties_{product}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.parquet",
        ]
        
        # Check for exact date range match
        for path in possible_paths:
            if self.gcs_manager.blob_exists(path):
                logger.info(f"  ✓ Found exact match: {path}")
                return True, path
        
        # Check for files that contain the entire date range
        # List all files for this product in both directories
        prefixes_to_check = [
            f"processed/modis/{product}/",
            f"processed/indicators/{product}/",
        ]
        
        for prefix in prefixes_to_check:
            try:
                # Use GCSManager's list_blobs method
                blob_names = self.gcs_manager.list_blobs(prefix=prefix, suffix=".parquet")
                
                logger.info(f"  Checking {prefix}: found {len(blob_names)} parquet files")
                
                for blob_name in blob_names:
                    # Extract date range from filename
                    # Format: iowa_counties_{product}_YYYYMMDD_YYYYMMDD.parquet
                    filename = blob_name.split('/')[-1]
                    parts = filename.replace('.parquet', '').split('_')
                    
                    logger.info(f"    Examining: {filename}")
                    
                    if len(parts) >= 2:
                        try:
                            # Get the last two parts (should be start and end dates)
                            file_start = datetime.strptime(parts[-2], '%Y%m%d')
                            file_end = datetime.strptime(parts[-1], '%Y%m%d')
                            
                            logger.info(f"      File dates: {file_start.date()} to {file_end.date()}")
                            logger.info(f"      Requested: {start_date.date()} to {end_date.date()}")
                            
                            # Check if file starts on or before requested start date
                            if file_start <= start_date:
                                # Calculate days difference from file end to requested end
                                days_diff = (end_date - file_end).days
                                
                                if days_diff <= 0:
                                    # File contains all requested data
                                    logger.info(f"  ✓ Found containing range: {blob_name}")
                                    logger.info(f"    File range: {file_start.date()} to {file_end.date()}")
                                    logger.info(f"    Requested: {start_date.date()} to {end_date.date()}")
                                    return True, blob_name
                                elif days_diff <= 7:
                                    # File is recent enough (within 7 days)
                                    logger.info(f"  ✓ Found recent data: {blob_name}")
                                    logger.info(f"    File ends {file_end.date()}, requested {end_date.date()} ({days_diff} day(s) difference)")
                                    logger.info(f"    Skipping re-download (close enough for analysis)")
                                    logger.info(f"    → Avoiding re-processing of entire dataset for {days_diff} new day(s)")
                                    return True, blob_name
                                else:
                                    logger.info(f"      File is {days_diff} days old (> 7 day threshold)")
                                    
                        except (ValueError, IndexError) as e:
                            logger.info(f"      Could not parse dates from {filename}: {e}")
                            continue
            except Exception as e:
                logger.warning(f"  Error checking prefix {prefix}: {e}")
                continue
        
        return False, ""
    
    def process_modis_ndvi(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Process MODIS NDVI/EVI using Google Earth Engine
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with county-level NDVI/EVI statistics
        """
        logger.info("\n" + "="*70)
        logger.info("  PROCESSING MODIS NDVI/EVI WITH GOOGLE EARTH ENGINE")
        logger.info("="*70)
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"  Product: MOD13A1.061")
        
        # Load counties
        counties = self.load_iowa_counties()
        
        # Convert counties to Earth Engine FeatureCollection
        counties_ee = self._geodataframe_to_ee(counties)
        
        # Load MODIS NDVI/EVI collection
        modis = ee.ImageCollection('MODIS/061/MOD13A1') \
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
            .select(['NDVI', 'EVI'])
        
        # Scale values
        def scale_modis(image):
            return image.multiply(0.0001).copyProperties(image, ['system:time_start'])
        
        modis_scaled = modis.map(scale_modis)
        
        logger.info(f"  Found {modis_scaled.size().getInfo()} images")
        
        # Aggregate to counties
        results = []
        
        image_list = modis_scaled.toList(modis_scaled.size())
        n_images = image_list.size().getInfo()
        
        for i in tqdm(range(n_images), desc="Processing NDVI/EVI"):
            image = ee.Image(image_list.get(i))
            date_millis = image.get('system:time_start').getInfo()
            date = datetime.fromtimestamp(date_millis / 1000)
            
            # Reduce to counties
            stats = image.reduceRegions(
                collection=counties_ee,
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), '', True
                ).combine(
                    ee.Reducer.minMax(), '', True
                ).combine(
                    ee.Reducer.count(), '', True
                ),
                scale=500
            )
            
            # Extract results
            features = stats.getInfo()['features']
            
            for feature in features:
                props = feature['properties']
                
                # NDVI
                if 'NDVI_mean' in props and props['NDVI_mean'] is not None:
                    results.append({
                        'fips': props['fips'],
                        'county_name': props['NAME'],
                        'date': date,
                        'band': 'NDVI',
                        'product': 'ndvi',
                        'mean': props['NDVI_mean'],
                        'std': props.get('NDVI_stdDev', np.nan),
                        'min': props.get('NDVI_min', np.nan),
                        'max': props.get('NDVI_max', np.nan),
                        'pixel_count': props.get('NDVI_count', 0)
                    })
                
                # EVI
                if 'EVI_mean' in props and props['EVI_mean'] is not None:
                    results.append({
                        'fips': props['fips'],
                        'county_name': props['NAME'],
                        'date': date,
                        'band': 'EVI',
                        'product': 'ndvi',
                        'mean': props['EVI_mean'],
                        'std': props.get('EVI_stdDev', np.nan),
                        'min': props.get('EVI_min', np.nan),
                        'max': props.get('EVI_max', np.nan),
                        'pixel_count': props.get('EVI_count', 0)
                    })
        
        df = pd.DataFrame(results)
        
        # Add median and percentiles (approximate from mean/std)
        if not df.empty:
            df['median'] = df['mean']
            df['p25'] = df['mean'] - 0.67 * df['std']
            df['p75'] = df['mean'] + 0.67 * df['std']
        
        logger.info(f"\n✓ Processed {len(df)} county-date-band records")
        return df
    
    def process_modis_et(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Process MODIS ET using Google Earth Engine
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with county-level ET statistics
        """
        logger.info("\n" + "="*70)
        logger.info("  PROCESSING MODIS ET WITH GOOGLE EARTH ENGINE")
        logger.info("="*70)
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"  Product: MOD16A2.061")
        
        # Load counties
        counties = self.load_iowa_counties()
        counties_ee = self._geodataframe_to_ee(counties)
        
        # Load MODIS ET collection
        modis = ee.ImageCollection('MODIS/061/MOD16A2GF') \
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
            .select(['ET', 'PET'])
        
        # Scale values
        def scale_modis(image):
            return image.multiply(0.1).copyProperties(image, ['system:time_start'])
        
        modis_scaled = modis.map(scale_modis)
        
        logger.info(f"  Found {modis_scaled.size().getInfo()} images")
        
        # Aggregate to counties
        results = []
        
        image_list = modis_scaled.toList(modis_scaled.size())
        n_images = image_list.size().getInfo()
        
        for i in tqdm(range(n_images), desc="Processing ET"):
            image = ee.Image(image_list.get(i))
            date_millis = image.get('system:time_start').getInfo()
            date = datetime.fromtimestamp(date_millis / 1000)
            
            # Reduce to counties
            stats = image.reduceRegions(
                collection=counties_ee,
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), '', True
                ).combine(
                    ee.Reducer.minMax(), '', True
                ).combine(
                    ee.Reducer.count(), '', True
                ),
                scale=500
            )
            
            # Extract results
            features = stats.getInfo()['features']
            
            for feature in features:
                props = feature['properties']
                
                # ET
                if 'ET_mean' in props and props['ET_mean'] is not None:
                    results.append({
                        'fips': props['fips'],
                        'county_name': props['NAME'],
                        'date': date,
                        'band': 'ET',
                        'product': 'et',
                        'mean': props['ET_mean'],
                        'std': props.get('ET_stdDev', np.nan),
                        'min': props.get('ET_min', np.nan),
                        'max': props.get('ET_max', np.nan),
                        'pixel_count': props.get('ET_count', 0)
                    })
                
                # PET
                if 'PET_mean' in props and props['PET_mean'] is not None:
                    results.append({
                        'fips': props['fips'],
                        'county_name': props['NAME'],
                        'date': date,
                        'band': 'PET',
                        'product': 'et',
                        'mean': props['PET_mean'],
                        'std': props.get('PET_stdDev', np.nan),
                        'min': props.get('PET_min', np.nan),
                        'max': props.get('PET_max', np.nan),
                        'pixel_count': props.get('PET_count', 0)
                    })
        
        df = pd.DataFrame(results)
        
        # Add median and percentiles
        if not df.empty:
            df['median'] = df['mean']
            df['p25'] = df['mean'] - 0.67 * df['std']
            df['p75'] = df['mean'] + 0.67 * df['std']
        
        logger.info(f"\n✓ Processed {len(df)} county-date-band records")
        return df
    
    def process_modis_lst(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Process MODIS Land Surface Temperature using Google Earth Engine
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with county-level LST statistics (day and night)
        """
        logger.info("\n" + "="*70)
        logger.info("  PROCESSING MODIS LST (LAND SURFACE TEMPERATURE)")
        logger.info("="*70)
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"  Product: MOD11A2.061 (8-day, 1km)")
        
        counties = self.load_iowa_counties()
        counties_ee = self._geodataframe_to_ee(counties)
        
        # Load MODIS LST collection
        modis = ee.ImageCollection('MODIS/061/MOD11A2') \
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
            .select(['LST_Day_1km', 'LST_Night_1km'])
        
        # Convert from Kelvin to Celsius: K * 0.02 - 273.15
        def scale_lst(image):
            return image.multiply(0.02).subtract(273.15).copyProperties(image, ['system:time_start'])
        
        modis_scaled = modis.map(scale_lst)
        
        logger.info(f"  Found {modis_scaled.size().getInfo()} images")
        
        results = []
        image_list = modis_scaled.toList(modis_scaled.size())
        n_images = image_list.size().getInfo()
        
        for i in tqdm(range(n_images), desc="Processing LST"):
            image = ee.Image(image_list.get(i))
            date_millis = image.get('system:time_start').getInfo()
            date = datetime.fromtimestamp(date_millis / 1000)
            
            stats = image.reduceRegions(
                collection=counties_ee,
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), '', True
                ).combine(
                    ee.Reducer.minMax(), '', True
                ).combine(
                    ee.Reducer.count(), '', True
                ),
                scale=1000
            )
            
            features = stats.getInfo()['features']
            
            for feature in features:
                props = feature['properties']
                
                # Day temperature
                if 'LST_Day_1km_mean' in props and props['LST_Day_1km_mean'] is not None:
                    results.append({
                        'fips': props['fips'],
                        'county_name': props['NAME'],
                        'date': date,
                        'band': 'LST_Day',
                        'product': 'lst',
                        'mean': props['LST_Day_1km_mean'],
                        'std': props.get('LST_Day_1km_stdDev', np.nan),
                        'min': props.get('LST_Day_1km_min', np.nan),
                        'max': props.get('LST_Day_1km_max', np.nan),
                        'pixel_count': props.get('LST_Day_1km_count', 0)
                    })
                
                # Night temperature
                if 'LST_Night_1km_mean' in props and props['LST_Night_1km_mean'] is not None:
                    results.append({
                        'fips': props['fips'],
                        'county_name': props['NAME'],
                        'date': date,
                        'band': 'LST_Night',
                        'product': 'lst',
                        'mean': props['LST_Night_1km_mean'],
                        'std': props.get('LST_Night_1km_stdDev', np.nan),
                        'min': props.get('LST_Night_1km_min', np.nan),
                        'max': props.get('LST_Night_1km_max', np.nan),
                        'pixel_count': props.get('LST_Night_1km_count', 0)
                    })
        
        df = pd.DataFrame(results)
        
        if not df.empty:
            df['median'] = df['mean']
            df['p25'] = df['mean'] - 0.67 * df['std']
            df['p75'] = df['mean'] + 0.67 * df['std']
        
        logger.info(f"\n✓ Processed {len(df)} county-date-band records")
        return df
    
    def process_precipitation(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Process CHIRPS Precipitation using Google Earth Engine
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with county-level precipitation statistics
        """
        logger.info("\n" + "="*70)
        logger.info("  PROCESSING CHIRPS PRECIPITATION")
        logger.info("="*70)
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"  Product: CHIRPS Daily (5km)")
        
        counties = self.load_iowa_counties()
        counties_ee = self._geodataframe_to_ee(counties)
        
        # Load CHIRPS daily precipitation
        chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
            .select('precipitation')
        
        # Aggregate to 8-day periods to match MODIS
        def aggregate_8day(start):
            start_date = ee.Date(start)
            end_date = start_date.advance(8, 'day')
            return chirps.filterDate(start_date, end_date).sum() \
                .set('system:time_start', start_date.millis())
        
        # Create 8-day intervals
        n_days = (end_date - start_date).days
        n_periods = n_days // 8
        dates = [start_date + timedelta(days=i*8) for i in range(n_periods)]
        
        logger.info(f"  Aggregating to {len(dates)} 8-day periods")
        
        results = []
        
        for date in tqdm(dates, desc="Processing Precipitation"):
            try:
                image = ee.Image(aggregate_8day(date.strftime('%Y-%m-%d')))
                
                stats = image.reduceRegions(
                    collection=counties_ee,
                    reducer=ee.Reducer.mean().combine(
                        ee.Reducer.stdDev(), '', True
                    ).combine(
                        ee.Reducer.minMax(), '', True
                    ).combine(
                        ee.Reducer.sum(), '', True
                    ).combine(
                        ee.Reducer.count(), '', True
                    ),
                    scale=5000
                )
                
                features = stats.getInfo()['features']
                
                for feature in features:
                    props = feature['properties']
                    
                    if 'precipitation_mean' in props and props['precipitation_mean'] is not None:
                        results.append({
                            'fips': props['fips'],
                            'county_name': props['NAME'],
                            'date': date,
                            'band': 'Precipitation',
                            'product': 'precipitation',
                            'mean': props['precipitation_mean'],
                            'std': props.get('precipitation_stdDev', np.nan),
                            'min': props.get('precipitation_min', np.nan),
                            'max': props.get('precipitation_max', np.nan),
                            'sum': props.get('precipitation_sum', np.nan),
                            'pixel_count': props.get('precipitation_count', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to process precipitation for {date.date()}: {e}")
                continue
        
        df = pd.DataFrame(results)
        
        if not df.empty and 'mean' in df.columns:
            df['median'] = df['mean']
            df['p25'] = df['mean'] - 0.67 * df['std']
            df['p75'] = df['mean'] + 0.67 * df['std']
        
        logger.info(f"\n✓ Processed {len(df)} county-date records")
        return df
    
    def process_vpd(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Process Vapor Pressure Deficit using gridMET
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with county-level VPD statistics
        """
        logger.info("\n" + "="*70)
        logger.info("  PROCESSING VPD (VAPOR PRESSURE DEFICIT)")
        logger.info("="*70)
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"  Product: gridMET (4km)")
        
        counties = self.load_iowa_counties()
        counties_ee = self._geodataframe_to_ee(counties)
        
        # Load gridMET VPD
        gridmet = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET') \
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
            .select('vpd')
        
        # Aggregate to 8-day periods
        def aggregate_8day(start):
            start_date = ee.Date(start)
            end_date = start_date.advance(8, 'day')
            return gridmet.filterDate(start_date, end_date).mean() \
                .set('system:time_start', start_date.millis())
        
        n_days = (end_date - start_date).days
        n_periods = n_days // 8
        dates = [start_date + timedelta(days=i*8) for i in range(n_periods)]
        
        logger.info(f"  Aggregating to {len(dates)} 8-day periods")
        
        results = []
        
        for date in tqdm(dates, desc="Processing VPD"):
            try:
                image = ee.Image(aggregate_8day(date.strftime('%Y-%m-%d')))
                
                stats = image.reduceRegions(
                    collection=counties_ee,
                    reducer=ee.Reducer.mean().combine(
                        ee.Reducer.stdDev(), '', True
                    ).combine(
                        ee.Reducer.minMax(), '', True
                    ).combine(
                        ee.Reducer.count(), '', True
                    ),
                    scale=4000
                )
                
                features = stats.getInfo()['features']
                
                for feature in features:
                    props = feature['properties']
                    
                    if 'vpd_mean' in props and props['vpd_mean'] is not None:
                        # Convert from Pa to kPa
                        results.append({
                            'fips': props['fips'],
                            'county_name': props['NAME'],
                            'date': date,
                            'band': 'VPD',
                            'product': 'vpd',
                            'mean': props['vpd_mean'] / 1000,  # Pa to kPa
                            'std': props.get('vpd_stdDev', np.nan) / 1000,
                            'min': props.get('vpd_min', np.nan) / 1000,
                            'max': props.get('vpd_max', np.nan) / 1000,
                            'pixel_count': props.get('vpd_count', 0)
                        })
            except Exception as e:
                logger.warning(f"Failed to process VPD for {date.date()}: {e}")
                continue
        
        df = pd.DataFrame(results)
        
        if not df.empty and 'mean' in df.columns:
            df['median'] = df['mean']
            df['p25'] = df['mean'] - 0.67 * df['std']
            df['p75'] = df['mean'] + 0.67 * df['std']
        
        logger.info(f"\n✓ Processed {len(df)} county-date records")
        return df
    
    def _geodataframe_to_ee(self, gdf: gpd.GeoDataFrame) -> ee.FeatureCollection:
        """Convert GeoDataFrame to Earth Engine FeatureCollection"""
        # Convert to WGS84 (EPSG:4326) which EE uses
        gdf_wgs84 = gdf.to_crs('EPSG:4326')
        
        features = []
        for idx, row in gdf_wgs84.iterrows():
            geom = row.geometry.__geo_interface__
            properties = {k: v for k, v in row.items() if k != 'geometry'}
            feature = ee.Feature(ee.Geometry(geom), properties)
            features.append(feature)
        
        return ee.FeatureCollection(features)
    
    def download_all_products(
        self,
        start_date: datetime,
        end_date: datetime,
        products: List[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Download all agricultural indicators using Google Earth Engine
        Skips products that already exist in GCS
        
        Args:
            start_date: Start date
            end_date: End date
            products: List of products to download
                     Options: 'ndvi', 'et', 'lst'
                     Default: all products
            
        Returns:
            Dictionary of DataFrames by product
        """
        if products is None:
            products = ['ndvi', 'et', 'lst']
        
        logger.info("\n" + "="*70)
        logger.info("  IOWA CORN AGRICULTURAL INDICATORS - GOOGLE EARTH ENGINE")
        logger.info("="*70)
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"  Products requested: {', '.join(products)}")
        logger.info(f"  Categories:")
        logger.info(f"    Vegetation Health: NDVI, EVI")
        logger.info(f"    Water Stress: ET")
        logger.info(f"    Heat Stress: LST")
        logger.info("="*70)
        
        # Check which products already exist in GCS
        products_to_download = []
        products_skipped = []
        
        for product in products:
            exists, existing_path = self._check_existing_data(product, start_date, end_date)
            
            if exists:
                logger.info(f"  ✓ {product.upper()}: Data already exists - skipping")
                logger.info(f"    Path: gs://{self.gcs_manager.bucket_name}/{existing_path}")
                products_skipped.append(product)
            else:
                logger.info(f"  → {product.upper()}: Will download")
                products_to_download.append(product)
        
        if not products_to_download:
            logger.info("\n" + "="*70)
            logger.info("  ✅ ALL DATA ALREADY EXISTS - NOTHING TO DOWNLOAD")
            logger.info("="*70)
            logger.info(f"  All {len(products_skipped)} products already in GCS")
            for product in products_skipped:
                exists, existing_path = self._check_existing_data(product, start_date, end_date)
                if exists:
                    logger.info(f"    {product}: gs://{self.gcs_manager.bucket_name}/{existing_path}")
            logger.info("="*70)
            return {}
        
        logger.info(f"\n  📥 Downloading {len(products_to_download)} product(s)")
        logger.info(f"  ↻ Skipping {len(products_skipped)} existing product(s)")
        logger.info("="*70)
        
        results = {}
        
        # Process each product
        product_functions = {
            'ndvi': self.process_modis_ndvi,
            'et': self.process_modis_et,
            'lst': self.process_modis_lst
        }
        
        for product in products_to_download:
            if product in product_functions:
                try:
                    results[product] = product_functions[product](start_date, end_date)
                except Exception as e:
                    logger.error(f"Failed to process {product}: {e}")
                    import traceback
                    traceback.print_exc()
                    results[product] = pd.DataFrame()
            else:
                logger.warning(f"Unknown product: {product}")
        
        # Upload to GCS (using modis directory structure)
        if self.gcs_manager:
            logger.info("\n" + "="*70)
            logger.info("  UPLOADING TO GCS")
            logger.info("="*70)
            
            for product, df in results.items():
                if not df.empty:
                    # Use the modis directory structure
                    output_path = (
                        f"processed/modis/{product}/"
                        f"iowa_counties_{product}_"
                        f"{start_date.strftime('%Y%m%d')}_"
                        f"{end_date.strftime('%Y%m%d')}.parquet"
                    )
                    
                    local_path = self.temp_dir / f"{product}_results.parquet"
                    df.to_parquet(local_path, index=False)
                    
                    self.gcs_manager.upload_file(str(local_path), output_path)
                    logger.info(f"  ✓ {product.upper()}: gs://{self.gcs_manager.bucket_name}/{output_path}")
                    logger.info(f"    Records: {len(df):,} | Size: {local_path.stat().st_size / 1024:.1f} KB")
        
        logger.info("\n" + "="*70)
        logger.info("  ✅ PROCESSING COMPLETE")
        logger.info("="*70)
        logger.info("  Summary by Category:")
        logger.info("  Vegetation Health:")
        if 'ndvi' in results and not results['ndvi'].empty:
            logger.info(f"    NDVI/EVI: {len(results['ndvi']):,} records")
        logger.info("  Water Stress:")
        if 'et' in results and not results['et'].empty:
            logger.info(f"    ET: {len(results['et']):,} records")
        logger.info("  Heat Stress:")
        if 'lst' in results and not results['lst'].empty:
            logger.info(f"    LST: {len(results['lst']):,} records")
        
        if products_skipped:
            logger.info(f"\n  ↻ Skipped (already exist): {', '.join(products_skipped)}")
        
        logger.info("="*70)
        
        return results


def main():
    """Main execution function"""
    
    # Configuration from environment
    start_date_str = os.getenv("START_DATE")
    end_date_str = os.getenv("END_DATE")
    start_year = int(os.getenv("START_YEAR", "2017"))
    
    # Default: Download all corn seasons from START_YEAR to current date
    if not start_date_str or not end_date_str:
        current_date = datetime.now()
        current_year = current_date.year
        
        # Start from May 1 of START_YEAR
        start_date = datetime(start_year, 5, 1)
        
        # End at current date or October 31 of current year (whichever is earlier)
        if current_date.month > 10:  # Past October
            end_date = datetime(current_year, 10, 31)
        else:
            end_date = current_date
        
        logger.info("="*70)
        logger.info(f"  DEFAULT: Downloading ALL corn seasons from {start_year} to present")
        logger.info("="*70)
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"  Years covered: {start_year} through {current_year}")
        logger.info(f"  Corn seasons: May 1 - October 31 each year")
        logger.info("="*70)
    else:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        logger.info(f"Custom date range: {start_date.date()} to {end_date.date()}")
    
    # Option to download specific years (corn seasons)
    years_str = os.getenv("CORN_YEARS")
    if years_str:
        years = [int(y.strip()) for y in years_str.split(",")]
        logger.info("="*70)
        logger.info(f"  CORN_YEARS specified: {years}")
        logger.info("="*70)
        
        # Override start/end dates to cover all specified years
        start_date = datetime(min(years), 5, 1)
        
        # For the last year, end at current date or Oct 31 (whichever is earlier)
        max_year = max(years)
        if max_year == datetime.now().year:
            current_date = datetime.now()
            if current_date.month > 10:
                end_date = datetime(max_year, 10, 31)
            else:
                end_date = current_date
        else:
            end_date = datetime(max_year, 10, 31)
        
        logger.info(f"  Downloading: {start_date.date()} to {end_date.date()}")
    
    products_str = os.getenv("PRODUCTS", "ndvi,et,lst")
    products = [p.strip() for p in products_str.split(",")]
    
    temp_dir = os.getenv("TEMP_DIR", "./temp")
    gcp_project = os.getenv("GCP_PROJECT_ID")
    
    # Initialize GCS manager
    try:
        gcs_manager = get_gcs_manager()
        logger.info(f"✓ Connected to GCS: {gcs_manager.bucket_name}")
    except Exception as e:
        logger.error(f"Failed to initialize GCS: {e}")
        sys.exit(1)
    
    # Initialize downloader
    try:
        downloader = GEEMODISDownloader(
            temp_dir=temp_dir,
            gcs_manager=gcs_manager,
            gcp_project=gcp_project
        )
    except Exception as e:
        logger.error(f"Failed to initialize GEE: {e}")
        logger.info("Make sure you've run: earthengine authenticate")
        sys.exit(1)
    
    # Download all products
    try:
        results = downloader.download_all_products(
            start_date=start_date,
            end_date=end_date,
            products=products
        )
        
        logger.info("\n✨ Success! Data ready in GCS.")
        
    except Exception as e:
        logger.error(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
