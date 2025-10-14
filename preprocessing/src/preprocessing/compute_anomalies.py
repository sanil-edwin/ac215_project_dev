"""
Compute anomalies from MODIS indicators using historical baselines

For each observation:
- Calculate Z-score: (value - baseline_mean) / baseline_std
- Calculate percentile rank
- Classify anomaly severity
- Compute persistence (consecutive anomalous days)
"""

import os
import sys
from pathlib import Path

# Fix path - go up to src/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict
from tqdm import tqdm

from utils.gcs_utils import get_gcs_manager
from utils.config import load_config, classify_anomaly, get_env_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detect anomalies using baseline statistics"""
    
    def __init__(self, config: Dict, gcs_manager, year: int):
        self.config = config
        self.gcs_manager = gcs_manager
        self.year = year
        
        # Load baselines
        self.baselines = {}
        self.stage_baselines = {}
        
        logger.info(f"Initialized AnomalyDetector for year {year}")
    
    def load_baselines(self, product: str):
        """Load baseline statistics for a product"""
        if product in self.baselines:
            return
        
        logger.info(f"Loading {product.upper()} baselines...")
        
        # Daily baselines
        baseline_path = f"{self.config['output']['baselines_path']}/{product}_baseline_daily.parquet"
        self.baselines[product] = self.gcs_manager.download_dataframe(
            baseline_path, format='parquet'
        )
        logger.info(f"  ✓ Loaded {len(self.baselines[product]):,} daily baseline records")
        
        # Growth stage baselines
        stage_path = f"{self.config['output']['baselines_path']}/{product}_baseline_stages.parquet"
        self.stage_baselines[product] = self.gcs_manager.download_dataframe(
            stage_path, format='parquet'
        )
        logger.info(f"  ✓ Loaded {len(self.stage_baselines[product]):,} stage baseline records")
    
    def load_current_data(self, product: str) -> pd.DataFrame:
        """Load current year data for a product"""
        logger.info(f"Loading {self.year} {product.upper()} data...")
        
        # Find files for this year
        prefix = f"processed/modis/{product}/"
        blob_names = self.gcs_manager.list_blobs(prefix=prefix, suffix=".parquet")
        
        # Filter to files containing this year
        year_str = str(self.year)
        relevant_blobs = [b for b in blob_names if year_str in b]
        
        if not relevant_blobs:
            raise ValueError(f"No data found for {product} in {self.year}")
        
        # Load data
        dfs = []
        for blob_name in relevant_blobs:
            df = self.gcs_manager.download_dataframe(blob_name, format='parquet')
            dfs.append(df)
        
        df = pd.concat(dfs, ignore_index=True)
        
        # Convert date and filter to target year
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['date'].dt.year == self.year]
        df['doy'] = df['date'].dt.dayofyear
        
        logger.info(f"  Loaded {len(df):,} records for {self.year}")
        logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        
        return df
    
    def compute_z_scores(self, current_df: pd.DataFrame, baseline_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Z-scores by joining with baselines
        
        Z-score = (value - baseline_mean) / baseline_std
        """
        logger.info("Computing Z-scores...")
        
        # Merge current data with baselines
        merged = current_df.merge(
            baseline_df[['fips', 'product', 'band', 'doy', 
                        'baseline_mean', 'baseline_std', 'baseline_median',
                        'baseline_p25', 'baseline_p75', 'growth_stage']],
            on=['fips', 'product', 'band', 'doy'],
            how='left'
        )
        
        # Calculate Z-score
        merged['z_score'] = (merged['mean'] - merged['baseline_mean']) / merged['baseline_std']
        
        # Calculate percentile (approximate)
        # If value > median: 50 + 25*(value-median)/(p75-median)
        # If value < median: 50 - 25*(median-value)/(median-p25)
        def calc_percentile(row):
            val = row['mean']
            med = row['baseline_median']
            p25 = row['baseline_p25']
            p75 = row['baseline_p75']
            
            if pd.isna(val) or pd.isna(med):
                return np.nan
            
            if val > med:
                if p75 > med:
                    return 50 + 25 * (val - med) / (p75 - med)
                else:
                    return 50
            else:
                if med > p25:
                    return 50 - 25 * (med - val) / (med - p25)
                else:
                    return 50
        
        merged['percentile'] = merged.apply(calc_percentile, axis=1)
        merged['percentile'] = merged['percentile'].clip(0, 100)
        
        # Classify anomaly
        merged['anomaly_flag'] = merged['z_score'].apply(
            lambda z: classify_anomaly(z, self.config) if not pd.isna(z) else 'normal'
        )
        
        logger.info(f"  Computed Z-scores for {len(merged):,} observations")
        logger.info(f"  Missing baselines: {merged['baseline_mean'].isna().sum()}")
        
        # Anomaly distribution
        logger.info("\nAnomaly distribution:")
        anomaly_counts = merged['anomaly_flag'].value_counts()
        for level, count in anomaly_counts.items():
            pct = 100 * count / len(merged)
            logger.info(f"  {level}: {count:,} ({pct:.1f}%)")
        
        return merged
    
    def compute_persistence(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate consecutive days of anomalies
        
        For each observation, count how many consecutive days
        before it also had anomalies
        """
        logger.info("Computing persistence...")
        
        # Sort by county, band, and date
        df = df.sort_values(['fips', 'band', 'date']).reset_index(drop=True)
        
        # For each persistence window
        for window in self.config['persistence_windows']:
            col_name = f'days_persistent_{window}d'
            df[col_name] = 0
            
            # Group by county and band
            for (fips, band), group in tqdm(df.groupby(['fips', 'band']), 
                                            desc=f"Computing {window}d persistence"):
                
                # For each row in group
                for idx in group.index:
                    # Look back up to 'window' days
                    date = df.loc[idx, 'date']
                    lookback = group[
                        (group['date'] < date) & 
                        (group['date'] >= date - pd.Timedelta(days=window))
                    ]
                    
                    # Count consecutive anomalous days (including current)
                    if df.loc[idx, 'anomaly_flag'] != 'normal':
                        consecutive = 1
                        for _, row in lookback.iloc[::-1].iterrows():
                            if row['anomaly_flag'] != 'normal':
                                consecutive += 1
                            else:
                                break
                        df.loc[idx, col_name] = min(consecutive, window)
        
        logger.info("  ✓ Persistence computed")
        
        return df
    
    def add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling window statistics"""
        logger.info("Computing rolling window features...")
        
        df = df.sort_values(['fips', 'band', 'date']).reset_index(drop=True)
        
        for window in [7, 14, 30]:
            # Rolling mean of values
            df[f'rolling_mean_{window}d'] = df.groupby(['fips', 'band'])['mean'].transform(
                lambda x: x.rolling(window, min_periods=1).mean()
            )
            
            # Rolling mean of z-scores
            df[f'rolling_zscore_{window}d'] = df.groupby(['fips', 'band'])['z_score'].transform(
                lambda x: x.rolling(window, min_periods=1).mean()
            )
            
            # Rolling std (volatility)
            df[f'rolling_std_{window}d'] = df.groupby(['fips', 'band'])['mean'].transform(
                lambda x: x.rolling(window, min_periods=1).std()
            )
        
        logger.info("  ✓ Rolling features computed")
        
        return df
    
    def process_product(self, product: str) -> pd.DataFrame:
        """Process anomalies for one product"""
        logger.info(f"\nProcessing {product.upper()} anomalies...")
        
        # Load baselines
        self.load_baselines(product)
        
        # Load current year data
        current_df = self.load_current_data(product)
        
        # Compute Z-scores
        anomaly_df = self.compute_z_scores(
            current_df, 
            self.baselines[product]
        )
        
        # Compute persistence
        anomaly_df = self.compute_persistence(anomaly_df)
        
        # Add rolling features
        anomaly_df = self.add_rolling_features(anomaly_df)
        
        # Select final columns
        output_cols = [
            'fips', 'county_name', 'date', 'doy', 'product', 'band', 'growth_stage',
            'mean', 'std', 'min', 'max', 'median', 'p25', 'p75', 'pixel_count',
            'baseline_mean', 'baseline_std', 'baseline_median', 
            'baseline_p25', 'baseline_p75',
            'z_score', 'percentile', 'anomaly_flag',
        ]
        
        # Add persistence columns
        output_cols.extend([f'days_persistent_{w}d' for w in self.config['persistence_windows']])
        
        # Add rolling columns
        for window in [7, 14, 30]:
            output_cols.extend([
                f'rolling_mean_{window}d',
                f'rolling_zscore_{window}d',
                f'rolling_std_{window}d'
            ])
        
        anomaly_df = anomaly_df[output_cols]
        
        return anomaly_df
    
    def save_anomalies(self, df: pd.DataFrame, product: str):
        """Save anomalies to GCS"""
        output_path = f"{self.config['output']['anomalies_path']}/{product}_anomalies_{self.year}.parquet"
        
        self.gcs_manager.upload_dataframe(df, output_path, format='parquet')
        
        logger.info(f"\n✓ Saved anomalies:")
        logger.info(f"  Path: gs://{self.gcs_manager.bucket_name}/{output_path}")
        logger.info(f"  Records: {len(df):,}")
        logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"  Counties: {df['fips'].nunique()}")
        logger.info(f"  Bands: {df['band'].unique().tolist()}")


def main():
    """Main execution"""
    logger.info("="*70)
    logger.info("  AGRIGUARD - ANOMALY DETECTION")
    logger.info("="*70)
    
    # Load configuration
    config = load_config()
    env_config = get_env_config()
    year = env_config['year']
    
    logger.info(f"\nTarget year: {year}")
    
    # Initialize GCS
    gcs_manager = get_gcs_manager()
    logger.info(f"✓ Connected to GCS: {gcs_manager.bucket_name}")
    
    # Initialize detector
    detector = AnomalyDetector(config, gcs_manager, year)
    
    # Process each product
    products = list(config['products'].keys())
    logger.info(f"\nProcessing products: {products}")
    
    for product in products:
        logger.info("\n" + "="*70)
        logger.info(f"  {product.upper()} ANOMALIES")
        logger.info("="*70)
        
        try:
            # Compute anomalies
            anomaly_df = detector.process_product(product)
            
            # Save to GCS
            detector.save_anomalies(anomaly_df, product)
            
            logger.info(f"✓ {product.upper()} complete")
            
        except Exception as e:
            logger.error(f"Failed to process {product}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    logger.info("\n" + "="*70)
    logger.info("  ✅ ANOMALY DETECTION COMPLETE")
    logger.info("="*70)
    logger.info(f"\nAnomalies saved to: gs://{gcs_manager.bucket_name}/{config['output']['anomalies_path']}/")
    logger.info(f"\nAnomaly data includes:")
    logger.info(f"  - Z-scores and anomaly classifications")
    logger.info(f"  - Persistence metrics (7d, 14d, 21d, 30d)")
    logger.info(f"  - Rolling averages and trends")
    logger.info(f"  - Growth stage information")
    logger.info(f"\nNext steps:")
    logger.info(f"  - Container 3: Stress Detection")
    logger.info(f"  - Container 4: Yield Forecasting models")


if __name__ == "__main__":
    main()
