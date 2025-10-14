"""Prepare features for rolling window yield forecasting - With NDVI + EVI."""

import sys
sys.path.append('/app')

from utils.data_loader import DataLoader
from utils.feature_engineering import RollingWindowFeatureEngineer
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main feature preparation pipeline."""
    
    logger.info("="*60)
    logger.info("ROLLING WINDOW YIELD FORECASTING - FEATURE PREPARATION (WITH NDVI + EVI)")
    logger.info("="*60)
    
    # Initialize data loader
    loader = DataLoader()
    
    # Load data
    logger.info("\n1. Loading data...")
    yields_df = loader.load_yields()
    et_df = loader.load_et_data()
    lst_df = loader.load_lst_data()
    ndvi_evi_df = loader.load_ndvi_data()  # Contains both NDVI and EVI
    
    logger.info(f"\nData loaded:")
    logger.info(f"  Yields: {len(yields_df)} records")
    logger.info(f"  ET: {len(et_df)} records")
    logger.info(f"  LST: {len(lst_df)} records")
    logger.info(f"  NDVI/EVI: {len(ndvi_evi_df)} records")
    
    # Training years (2017-2024)
    training_years = list(range(2017, 2025))
    
    logger.info(f"\n2. Creating features for training years: {training_years}")
    
    # Initialize feature engineer with NDVI/EVI
    engineer = RollingWindowFeatureEngineer(et_df, lst_df, ndvi_evi_df)
    
    # Define forecast dates
    forecast_dates = [
        (6, 15), (6, 30),
        (7, 15), (7, 31),
        (8, 15), (8, 31),
        (9, 15), (9, 30),
    ]
    
    # Create training dataset
    training_df = engineer.create_training_dataset(training_years, forecast_dates)
    
    if len(training_df) == 0:
        logger.error("No training features created! Exiting.")
        return
    
    # Merge with yields
    logger.info("\n3. Merging with yield data...")
    
    merged = training_df.merge(
        yields_df[['year', 'fips', 'yield', 'county']],
        on=['year', 'fips'],
        how='left'
    )
    
    # Remove rows without yield data
    before_drop = len(merged)
    merged = merged.dropna(subset=['yield'])
    after_drop = len(merged)
    
    logger.info(f"  Samples before yield merge: {before_drop}")
    logger.info(f"  Samples after yield merge: {after_drop}")
    logger.info(f"  Dropped {before_drop - after_drop} samples without yield data")
    
    # Summary statistics
    logger.info(f"\nFinal training dataset:")
    logger.info(f"  Total samples: {len(merged)}")
    logger.info(f"  Counties: {merged['fips'].nunique()}")
    logger.info(f"  Years: {sorted(merged['year'].unique())}")
    logger.info(f"  Forecast dates per year: {merged.groupby('year')['cutoff_date'].nunique().mean():.1f}")
    
    feature_cols = [c for c in merged.columns 
                   if c not in ['year', 'fips', 'yield', 'county', 'cutoff_date']]
    logger.info(f"  Features: {len(feature_cols)}")
    
    # Show feature breakdown
    logger.info(f"\nFeature breakdown:")
    temporal_features = [c for c in feature_cols if any(x in c for x in ['days', 'week', 'month', 'completeness'])]
    et_features = [c for c in feature_cols if c.startswith('et_')]
    lst_features = [c for c in feature_cols if c.startswith('lst_')]
    ndvi_features = [c for c in feature_cols if c.startswith('ndvi_')]
    evi_features = [c for c in feature_cols if c.startswith('evi_')]
    logger.info(f"  Temporal: {len(temporal_features)}")
    logger.info(f"  ET-based: {len(et_features)}")
    logger.info(f"  LST-based: {len(lst_features)}")
    logger.info(f"  NDVI-based: {len(ndvi_features)}")
    logger.info(f"  EVI-based: {len(evi_features)}")
    
    # Save to GCS
    logger.info(f"\n4. Saving to GCS...")
    output_path = "model_yield_forecasting/features/rolling_window_training_features_ndvi_evi.parquet"
    loader.save_to_gcs(merged, output_path)
    
    # Also save feature names
    import json
    feature_info = {
        'total_features': int(len(feature_cols)),
        'feature_names': feature_cols,
        'temporal_features': temporal_features,
        'et_features': et_features,
        'lst_features': lst_features,
        'ndvi_features': ndvi_features,
        'evi_features': evi_features,
        'training_samples': int(len(merged)),
        'counties': int(merged['fips'].nunique()),
        'years': [int(y) for y in sorted(merged['year'].unique())]
    }
    
    feature_json = json.dumps(feature_info, indent=2)
    blob = loader.bucket.blob("model_yield_forecasting/features/feature_info_ndvi_evi.json")
    blob.upload_from_string(feature_json, content_type='application/json')
    
    logger.info("\n" + "="*60)
    logger.info("FEATURE PREPARATION COMPLETE (WITH NDVI + EVI)")
    logger.info("="*60)


if __name__ == "__main__":
    main()