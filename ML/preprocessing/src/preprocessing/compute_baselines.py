"""
Compute historical baselines from MODIS data (2017-2023)

For each county × product × band × day-of-year:
- Calculate mean, std, median, 25th/75th percentiles
- Aggregate by growth stage
- Save baseline statistics for anomaly detection
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
from tqdm import tqdm

from utils.gcs_utils import get_gcs_manager
from utils.config import load_config, get_growth_stage, get_env_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaselineComputer:
    """Compute historical baseline statistics"""
    
    def __init__(self, config: Dict, gcs_manager, start_year: int, end_year: int):
        self.config = config
        self.gcs_manager = gcs_manager
        self.start_year = start_year
        self.end_year = end_year
        
        logger.info(f"Initialized BaselineComputer for {start_year}-{end_year}")
    
    def load_historical_data(self, product: str) -> pd.DataFrame:
        """Load all historical data for a product"""
        logger.info(f"Loading historical {product.upper()} data ({self.start_year}-{self.end_year})...")
        
        # Find all files for this product
        prefix = f"processed/modis/{product}/"
        blob_names = self.gcs_manager.list_blobs(prefix=prefix, suffix=".parquet")
        
        if not blob_names:
            raise ValueError(f"No data found for product: {product}")
        
        # Filter to historical years
        historical_blobs = []
        for blob_name in blob_names:
            for year in range(self.start_year, self.end_year + 1):
                if str(year) in blob_name:
                    historical_blobs.append(blob_name)
                    break
        
        if not historical_blobs:
            raise ValueError(f"No historical data found for {product} ({self.start_year}-{self.end_year})")
        
        logger.info(f"Found {len(historical_blobs)} files to process")
        
        # Load all data
        dfs = []
        for blob_name in tqdm(historical_blobs, desc=f"Loading {product}"):
            df = self.gcs_manager.download_dataframe(blob_name, format='parquet')
            dfs.append(df)
        
        # Combine
        df = pd.concat(dfs, ignore_index=True)
        
        # Process dates
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        df['doy'] = df['date'].dt.dayofyear
        
        # Filter to historical period
        df = df[(df['year'] >= self.start_year) & (df['year'] <= self.end_year)]
        
        logger.info(f"Loaded {len(df):,} records")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"Counties: {df['fips'].nunique()}")
        logger.info(f"Bands: {df['band'].unique().tolist()}")
        
        return df
    
    def compute_daily_baselines(self, df: pd.DataFrame, product: str) -> pd.DataFrame:
        """
        Compute baseline statistics by day of year
        
        Groups by: fips × product × band × doy
        Computes: mean, std, median, p25, p75
        """
        logger.info("Computing daily baselines (by day-of-year)...")
        
        # Group by county, product, band, and day of year
        grouped = df.groupby(['fips', 'county_name', 'product', 'band', 'doy'])
        
        # Calculate statistics
        baselines = grouped['mean'].agg([
            ('baseline_mean', 'mean'),
            ('baseline_std', 'std'),
            ('baseline_median', 'median'),
            ('baseline_p25', lambda x: x.quantile(0.25)),
            ('baseline_p75', lambda x: x.quantile(0.75)),
            ('n_years', 'count')
        ]).reset_index()
        
        # Add growth stage
        baselines['growth_stage'] = baselines['doy'].apply(
            lambda doy: get_growth_stage(doy, self.config)
        )
        
        logger.info(f"Computed {len(baselines):,} daily baseline records")
        
        # Show sample
        logger.info("\nSample daily baselines:")
        logger.info(baselines.head(10).to_string())
        
        return baselines
    
    def compute_stage_baselines(self, df: pd.DataFrame, product: str) -> pd.DataFrame:
        """
        Compute baseline statistics by growth stage
        
        Groups by: fips × product × band × growth_stage
        Computes: mean, std, median, p25, p75
        """
        logger.info("Computing growth stage baselines...")
        
        # Add growth stage
        df['growth_stage'] = df['doy'].apply(
            lambda doy: get_growth_stage(doy, self.config)
        )
        
        # Group by county, product, band, and growth stage
        grouped = df.groupby(['fips', 'county_name', 'product', 'band', 'growth_stage'])
        
        # Calculate statistics
        baselines = grouped['mean'].agg([
            ('baseline_mean', 'mean'),
            ('baseline_std', 'std'),
            ('baseline_median', 'median'),
            ('baseline_p25', lambda x: x.quantile(0.25)),
            ('baseline_p75', lambda x: x.quantile(0.75)),
            ('n_observations', 'count')
        ]).reset_index()
        
        logger.info(f"Computed {len(baselines):,} stage baseline records")
        
        # Show sample
        logger.info("\nSample stage baselines:")
        logger.info(baselines.head(10).to_string())
        
        return baselines
    
    def save_baselines(self, daily_df: pd.DataFrame, stage_df: pd.DataFrame, product: str):
        """Save baseline statistics to GCS"""
        baselines_path = self.config['output']['baselines_path']
        
        # Save daily baselines
        daily_path = f"{baselines_path}/{product}_baseline_daily.parquet"
        self.gcs_manager.upload_dataframe(daily_df, daily_path, format='parquet')
        logger.info(f"✓ Saved daily baselines: gs://{self.gcs_manager.bucket_name}/{daily_path}")
        
        # Save stage baselines
        stage_path = f"{baselines_path}/{product}_baseline_stages.parquet"
        self.gcs_manager.upload_dataframe(stage_df, stage_path, format='parquet')
        logger.info(f"✓ Saved stage baselines: gs://{self.gcs_manager.bucket_name}/{stage_path}")
    
    def process_product(self, product: str):
        """Compute baselines for one product"""
        logger.info(f"\n{'='*70}")
        logger.info(f"  Processing {product.upper()} Baselines")
        logger.info(f"{'='*70}")
        
        # Load historical data
        df = self.load_historical_data(product)
        
        # Compute daily baselines
        daily_baselines = self.compute_daily_baselines(df, product)
        
        # Compute stage baselines
        stage_baselines = self.compute_stage_baselines(df, product)
        
        # Save to GCS
        self.save_baselines(daily_baselines, stage_baselines, product)
        
        logger.info(f"✓ {product.upper()} baselines complete\n")


def main():
    """Main execution"""
    logger.info("="*70)
    logger.info("  AGRIGUARD - BASELINE COMPUTATION")
    logger.info("="*70)
    
    # Load configuration
    config = load_config()
    env_config = get_env_config()
    
    start_year = env_config['start_year']
    end_year = env_config['end_year']
    
    logger.info(f"\nBaseline period: {start_year}-{end_year}")
    
    # Initialize GCS
    try:
        gcs_manager = get_gcs_manager()
        logger.info(f"✓ Connected to GCS: {gcs_manager.bucket_name}\n")
    except Exception as e:
        logger.error(f"Failed to connect to GCS: {e}")
        sys.exit(1)
    
    # Initialize computer
    computer = BaselineComputer(config, gcs_manager, start_year, end_year)
    
    # Process each product
    products = list(config['products'].keys())
    logger.info(f"Products to process: {products}\n")
    
    for product in products:
        try:
            computer.process_product(product)
        except Exception as e:
            logger.error(f"Failed to process {product}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    logger.info("="*70)
    logger.info("  ✅ BASELINE COMPUTATION COMPLETE")
    logger.info("="*70)
    logger.info(f"\nBaselines saved to: gs://{gcs_manager.bucket_name}/{config['output']['baselines_path']}/")
    logger.info(f"\nNext step: Run compute_anomalies.py to detect stress events")


if __name__ == "__main__":
    main()
