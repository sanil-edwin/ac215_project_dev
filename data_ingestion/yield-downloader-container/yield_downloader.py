"""
USDA NASS Quick Stats API - Iowa County Corn Yield Ingestion
Downloads county-level corn yield data for Iowa (2017-current year)
Uploads directly to Google Cloud Storage
Checks GCS first and only downloads missing years
"""

import os
import sys
from pathlib import Path

import requests
import pandas as pd
from typing import List, Optional
from datetime import datetime
import logging

from utils.gcs_utils import GCSManager, get_gcs_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NASSYieldDownloader:
    """Download county-level corn yield data from USDA NASS Quick Stats API"""
    
    BASE_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
    
    def __init__(self, api_key: str):
        """
        Initialize NASS downloader
        
        Args:
            api_key: USDA NASS Quick Stats API key
                    Get free key at: https://quickstats.nass.usda.gov/api
        """
        self.api_key = api_key
        self.session = requests.Session()
    
    def download_corn_yields(
        self,
        state: str = "IOWA",
        years: Optional[List[int]] = None,
        start_year: int = 2017,
        gcs_manager: Optional[GCSManager] = None,
        gcs_prefix: str = "data_raw/yields/"
    ) -> pd.DataFrame:
        """
        Download county-level corn yield data and upload to GCS
        Checks GCS first and only downloads missing years
        
        Args:
            state: State name (default: IOWA)
            years: List of years to download (default: start_year to current year)
            start_year: First year to download if years not specified (default: 2017)
            gcs_manager: GCS manager instance (optional)
            gcs_prefix: GCS path prefix for uploads
            
        Returns:
            DataFrame with yield data
        """
        if years is None:
            # Automatically determine years from start_year to current year
            current_year = datetime.now().year
            years = list(range(start_year, current_year + 1))
            logger.info(f"Auto-detected year range: {start_year}-{current_year}")
            logger.info(f"Note: {current_year} data may not be available yet")
        
        logger.info("\n" + "="*70)
        logger.info("  IOWA CORN YIELDS - Checking GCS Bucket for Existing Data")
        logger.info("="*70)
        logger.info(f"  Bucket: gs://{gcs_manager.bucket_name if gcs_manager else 'N/A'}")
        logger.info(f"  Years to check: {start_year} to {datetime.now().year} ({len(years)} total)")
        logger.info(f"  Location: {gcs_prefix}")
        logger.info("="*70)
        
        # Check which years are missing from GCS
        missing_years = []
        existing_years = []
        
        if gcs_manager:
            logger.info("\n📋 Checking which yield years exist in GCS...")
            logger.info("-" * 70)
            
            # Check combined file exists
            min_year = min(years)
            max_year = max(years)
            combined_path = f"{gcs_prefix}iowa_corn_yields_{min_year}_{max_year}.csv"
            
            for year in years:
                year_path = f"{gcs_prefix}iowa_corn_yields_{year}.csv"
                if gcs_manager.blob_exists(year_path):
                    logger.info(f"  ✓ {year}: Yield data found in GCS")
                    existing_years.append(year)
                else:
                    logger.info(f"  ✗ {year}: Yield data MISSING from GCS")
                    missing_years.append(year)
            logger.info("-" * 70)
            
            # If nothing is missing, we're done!
            if not missing_years:
                logger.info("\n" + "="*70)
                logger.info("  ✅ ALL YIELD DATA ALREADY EXISTS - NOTHING TO DOWNLOAD")
                logger.info("="*70)
                logger.info(f"  All years from {start_year} to {datetime.now().year} are present")
                logger.info(f"  Location: gs://{gcs_manager.bucket_name}/{gcs_prefix}")
                logger.info(f"  Total files: {len(existing_years)} year files")
                logger.info("="*70)
                logger.info("\n✨ No action needed - your data is complete!")
                
                # Try to load existing combined file, or create one from individual files
                try:
                    logger.info("\nLoading existing combined data from GCS...")
                    df = gcs_manager.download_dataframe(combined_path, format='csv')
                    logger.info(f"Loaded {len(df)} records from combined file")
                    return df
                except Exception as e:
                    logger.info(f"Combined file not found, creating from individual files...")
                    # Load all individual year files and combine
                    all_dfs = []
                    for year in existing_years:
                        year_path = f"{gcs_prefix}iowa_corn_yields_{year}.csv"
                        try:
                            year_df = gcs_manager.download_dataframe(year_path, format='csv')
                            all_dfs.append(year_df)
                            logger.info(f"  Loaded {year}: {len(year_df)} records")
                        except Exception as ye:
                            logger.warning(f"Could not load {year}: {ye}")
                    
                    if all_dfs:
                        df = pd.concat(all_dfs, ignore_index=True)
                        df = df.sort_values(['year', 'county']).reset_index(drop=True)
                        logger.info(f"Combined {len(all_dfs)} years into {len(df)} records")
                        
                        # Upload the combined file
                        gcs_manager.upload_dataframe(df, combined_path, format='csv')
                        logger.info(f"Created and uploaded combined file: {combined_path}")
                        return df
                    else:
                        raise ValueError("Could not load any existing data")
            
            logger.info(f"\n📥 Need to download {len(missing_years)} missing year(s):")
            logger.info(f"   Years: {missing_years}")
            
            # Download only missing years
            years_to_download = missing_years
        else:
            logger.warning("⚠️  No GCS manager - will download all years")
            years_to_download = years
        
        logger.info("\n" + "="*70)
        logger.info("  🌽 STARTING YIELD DATA DOWNLOAD FOR IOWA")
        logger.info("="*70)
        logger.info(f"Downloading corn yield data for {state}: {years_to_download}")
        
        # NASS API parameters
        params = {
            "key": self.api_key,
            "source_desc": "SURVEY",
            "sector_desc": "CROPS",
            "group_desc": "FIELD CROPS",
            "commodity_desc": "CORN",
            "statisticcat_desc": "YIELD",
            "unit_desc": "BU / ACRE",
            "agg_level_desc": "COUNTY",
            "state_alpha": "IA",  # Iowa
            "format": "JSON"
        }
        
        all_data = []
        successful_years = []
        failed_years = []
        
        for year in years_to_download:
            logger.info(f"Fetching {year} data...")
            params["year"] = year
            
            try:
                response = self.session.get(self.BASE_URL, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if "data" in data:
                    all_data.extend(data["data"])
                    successful_years.append(year)
                    logger.info(f"  ✓ Retrieved {len(data['data'])} records for {year}")
                else:
                    failed_years.append(year)
                    logger.warning(f"  ⚠ No data returned for {year} (may not be available yet)")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"  ✗ Failed to fetch {year}: {e}")
                failed_years.append(year)
                continue
        
        if not all_data:
            logger.warning("No new yield data retrieved from NASS API")
            # If we have existing years, load those
            if existing_years and gcs_manager:
                logger.info("Loading existing data instead...")
                # Try combined file first
                try:
                    df = gcs_manager.download_dataframe(combined_path, format='csv')
                    logger.info(f"Loaded {len(df)} records from combined file")
                    return df
                except:
                    logger.info("Combined file not found, loading from individual files...")
                    # Load from individual files
                    all_dfs = []
                    for year in existing_years:
                        year_path = f"{gcs_prefix}iowa_corn_yields_{year}.csv"
                        try:
                            year_df = gcs_manager.download_dataframe(year_path, format='csv')
                            all_dfs.append(year_df)
                            logger.info(f"  Loaded {year}: {len(year_df)} records")
                        except Exception as ye:
                            logger.warning(f"Could not load {year}: {ye}")
                    
                    if all_dfs:
                        df = pd.concat(all_dfs, ignore_index=True)
                        df = df.sort_values(['year', 'county']).reset_index(drop=True)
                        logger.info(f"Combined {len(all_dfs)} years into {len(df)} records")
                        
                        # Upload the combined file
                        gcs_manager.upload_dataframe(df, combined_path, format='csv')
                        logger.info(f"Created and uploaded combined file: {combined_path}")
                        return df
                    else:
                        raise ValueError("No yield data available")
            else:
                raise ValueError("No yield data retrieved from NASS API")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        # Clean and process data
        df = self._clean_yield_data(df)
        
        # If we had existing years, load and combine them
        if existing_years and gcs_manager:
            logger.info(f"\nCombining new data with {len(existing_years)} existing years...")
            try:
                existing_df = gcs_manager.download_dataframe(combined_path, format='csv')
                # Combine old and new data
                df = pd.concat([existing_df, df], ignore_index=True)
                # Remove duplicates (in case of re-download)
                df = df.drop_duplicates(subset=['year', 'county'], keep='last')
                df = df.sort_values(['year', 'county']).reset_index(drop=True)
                logger.info(f"Combined dataset now has {len(df)} records")
            except Exception as e:
                logger.warning(f"Could not load existing data for combining: {e}")
        
        # Create filename with actual year range
        if len(df) > 0:
            min_year = df["year"].min()
            max_year = df["year"].max()
            combined_filename = f"iowa_corn_yields_{min_year}_{max_year}.csv"
        else:
            combined_filename = "iowa_corn_yields.csv"
        
        # Upload to GCS if manager provided
        if gcs_manager:
            # Upload main combined file
            combined_path = f"{gcs_prefix}{combined_filename}"
            gcs_manager.upload_dataframe(df, combined_path, format='csv')
            logger.info(f"Uploaded combined yield data to GCS: {combined_path}")
            
            # Upload individual year files (only newly downloaded years)
            for year in successful_years:
                year_df = df[df["year"] == year]
                if len(year_df) > 0:
                    year_path = f"{gcs_prefix}iowa_corn_yields_{year}.csv"
                    gcs_manager.upload_dataframe(year_df, year_path, format='csv')
            
            logger.info(f"Uploaded {len(successful_years)} new annual yield files to GCS")
        else:
            logger.warning("No GCS manager provided - data not uploaded to cloud storage")
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("  YIELD DOWNLOAD SUMMARY")
        logger.info("="*70)
        logger.info(f"  Total years checked: {len(years)}")
        if existing_years:
            logger.info(f"  Already existed: {len(existing_years)} years")
            logger.info(f"    Existing: {existing_years}")
        logger.info(f"  Downloaded: {len(successful_years)} years")
        if successful_years:
            logger.info(f"    New: {successful_years}")
        if failed_years:
            logger.info(f"  Failed: {len(failed_years)} years")
            logger.info(f"    Failed: {failed_years}")
        
        if gcs_manager:
            logger.info(f"\n  ✓ All data in: gs://{gcs_manager.bucket_name}/{gcs_prefix}")
        
        logger.info("="*70)
        
        return df
    
    def _clean_yield_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize yield data"""
        
        # Select relevant columns
        columns_to_keep = [
            "year",
            "state_name",
            "state_fips_code",
            "county_name", 
            "county_code",
            "Value",
            "unit_desc"
        ]
        
        df_clean = df[columns_to_keep].copy()
        
        # Rename columns for clarity
        df_clean = df_clean.rename(columns={
            "Value": "yield_bu_per_acre",
            "state_name": "state",
            "county_name": "county",
            "state_fips_code": "state_fips",
            "county_code": "county_fips",
            "unit_desc": "unit"
        })
        
        # Convert yield to numeric (handle commas and non-numeric values)
        df_clean["yield_bu_per_acre"] = (
            df_clean["yield_bu_per_acre"]
            .str.replace(",", "")
            .astype(float)
        )
        
        # Ensure year is integer
        df_clean["year"] = df_clean["year"].astype(int)
        
        # Sort by year and county
        df_clean = df_clean.sort_values(["year", "county"])
        
        # Add FIPS code (state + county) for joining with spatial data
        df_clean["fips"] = (
            df_clean["state_fips"].astype(str).str.zfill(2) +
            df_clean["county_fips"].astype(str).str.zfill(3)
        )
        
        logger.info(f"Cleaned data: {len(df_clean)} records across "
                   f"{df_clean['county'].nunique()} counties and "
                   f"{df_clean['year'].nunique()} years")
        
        return df_clean
    
    def get_summary_statistics(self, df: pd.DataFrame) -> dict:
        """Generate summary statistics for yield data"""
        
        stats = {
            "total_records": len(df),
            "counties": df["county"].nunique(),
            "years": sorted(df["year"].unique().tolist()),
            "yield_stats": {
                "mean": df["yield_bu_per_acre"].mean(),
                "median": df["yield_bu_per_acre"].median(),
                "min": df["yield_bu_per_acre"].min(),
                "max": df["yield_bu_per_acre"].max(),
                "std": df["yield_bu_per_acre"].std()
            },
            "by_year": df.groupby("year")["yield_bu_per_acre"].agg(["mean", "std"]).to_dict()
        }
        
        return stats


def main():
    """Main execution function"""
    
    # Get API key from environment variable
    api_key = os.getenv("NASS_API_KEY")
    if not api_key:
        raise ValueError(
            "NASS_API_KEY environment variable not set. "
            "Get your free API key at https://quickstats.nass.usda.gov/api"
        )
    
    # Get year configuration
    start_year = int(os.getenv("START_YEAR", "2010"))
    current_year = datetime.now().year
    
    # Allow manual override via environment variable
    years_str = os.getenv("YIELD_YEARS")
    if years_str:
        years = [int(y.strip()) for y in years_str.split(",")]
        logger.info(f"Using manually specified years: {years}")
    else:
        years = None  # Will auto-detect in download_corn_yields
        logger.info(f"Will download data from {start_year} to {current_year}")
    
    # Initialize GCS manager
    try:
        gcs_manager = get_gcs_manager()
        logger.info(f"Connected to GCS bucket: {gcs_manager.bucket_name}")
    except Exception as e:
        logger.error(f"Failed to initialize GCS manager: {e}")
        logger.warning("Proceeding without GCS upload")
        gcs_manager = None
    
    # Initialize downloader
    downloader = NASSYieldDownloader(api_key)
    
    # Download yield data
    df = downloader.download_corn_yields(
        state="IOWA",
        years=years,
        start_year=start_year,
        gcs_manager=gcs_manager,
        gcs_prefix="data_raw/yields/"
    )
    
    # Print summary
    stats = downloader.get_summary_statistics(df)
    logger.info("\n" + "="*50)
    logger.info("YIELD DATA SUMMARY")
    logger.info("="*50)
    logger.info(f"Total records: {stats['total_records']}")
    logger.info(f"Counties: {stats['counties']}")
    logger.info(f"Years: {stats['years']}")
    logger.info(f"\nOverall yield statistics (bu/acre):")
    logger.info(f"  Mean:   {stats['yield_stats']['mean']:.2f}")
    logger.info(f"  Median: {stats['yield_stats']['median']:.2f}")
    logger.info(f"  Min:    {stats['yield_stats']['min']:.2f}")
    logger.info(f"  Max:    {stats['yield_stats']['max']:.2f}")
    logger.info(f"  Std:    {stats['yield_stats']['std']:.2f}")
    
    if gcs_manager:
        logger.info(f"\n✓ Data uploaded to: gs://{gcs_manager.bucket_name}/data_raw/yields/")
    
    logger.info("="*50)
    
    # Display sample data
    logger.info("\nSample data (first 5 rows):")
    print(df.head())


if __name__ == "__main__":
    main()
