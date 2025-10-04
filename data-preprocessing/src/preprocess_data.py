#!/usr/bin/env python3
"""
Data Preprocessing & Feature Engineering for AgriGuard
Creates features for stress detection and yield forecasting models
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import click
from loguru import logger
import yaml
from typing import Tuple, Dict
from sklearn.preprocessing import StandardScaler
import joblib

sys.path.append(str(Path(__file__).parent.parent))
from src.utils.logging_utils import setup_logging


class DataPreprocessor:
    """Preprocess yield data and create ML features"""
    
    def __init__(self, config_path: str = "configs/preprocessing_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        np.random.seed(self.config['random_seed'])
        
        logger.info("DataPreprocessor initialized")
    
    def load_data(self) -> pd.DataFrame:
        """Load yield data from Container 1"""
        
        input_path = self.config['paths']['input']
        logger.info(f"Loading data from: {input_path}")
        
        df = pd.read_csv(input_path)
        
        logger.info(f"Loaded {len(df)} records")
        logger.info(f"Years: {sorted(df['year'].unique().tolist())}")
        logger.info(f"Counties: {df['county'].nunique()}")
        
        return df
    
    def create_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create historical yield lag features"""
        
        logger.info("Creating lag features...")
        
        df = df.sort_values(['county', 'year'])
        
        for lag in self.config['features']['yield_lags']:
            df[f'yield_lag_{lag}'] = df.groupby('county')['yield_bu_per_acre'].shift(lag)
        
        logger.info(f"Created {len(self.config['features']['yield_lags'])} lag features")
        
        return df
    
    def generate_synthetic_satellite_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate synthetic satellite features
        These simulate what real Sentinel-2, Sentinel-1, MODIS would measure
        Correlate with actual yields to create realistic patterns
        """
        
        logger.info("Generating synthetic satellite features...")
        
        features = []
        
        for idx, row in df.iterrows():
            county = row['county']
            year = row['year']
            actual_yield = row['yield_bu_per_acre']
            
            # Normalize yield to 0-1 scale for correlation
            yield_normalized = (actual_yield - 100) / 100  # Roughly 0-1.5 range
            yield_normalized = max(0, min(1.5, yield_normalized))
            
            # Early season NDVI (Apr-Jun) - moderate correlation with yield
            ndvi_early_base = np.random.uniform(*self.config['features']['ndvi']['early_season_mean'])
            ndvi_early_mean = ndvi_early_base + yield_normalized * 0.1
            ndvi_early_std = np.random.uniform(*self.config['features']['ndvi']['std_dev'])
            
            # Mid season NDVI (Jul-Aug) - high correlation with yield (critical period)
            ndvi_mid_base = np.random.uniform(*self.config['features']['ndvi']['mid_season_mean'])
            ndvi_mid_mean = ndvi_mid_base + yield_normalized * 0.15
            ndvi_mid_std = np.random.uniform(*self.config['features']['ndvi']['std_dev'])
            
            # Late season NDVI (Sep-Oct) - lower values as crop matures
            ndvi_late_base = np.random.uniform(*self.config['features']['ndvi']['late_season_mean'])
            ndvi_late_mean = ndvi_late_base + yield_normalized * 0.05
            ndvi_late_std = np.random.uniform(*self.config['features']['ndvi']['std_dev'])
            
            # SAR moisture (correlated with yield - dry years = low yield)
            sar_vv = np.random.uniform(*self.config['features']['sar']['vv_mean']) + yield_normalized * 2
            sar_vh = np.random.uniform(*self.config['features']['sar']['vh_mean']) + yield_normalized * 2
            sar_moisture = np.random.uniform(*self.config['features']['sar']['moisture_proxy']) + yield_normalized * 3
            
            # Evapotranspiration
            et_seasonal = np.random.uniform(*self.config['features']['et']['seasonal_total']) + yield_normalized * 100
            et_anomaly = np.random.uniform(*self.config['features']['et']['anomaly']) * (1 - yield_normalized)
            
            # Growing Degree Days (temperature accumulation)
            gdd = np.random.uniform(*self.config['features']['gdd']['cumulative']) + yield_normalized * 200
            
            # Stress indicators (inverse correlation - high stress = low yield)
            stress_days = int(np.random.uniform(*self.config['features']['stress']['days_threshold']) * (1.5 - yield_normalized))
            stress_severity = np.random.uniform(*self.config['features']['stress']['severity']) * (1.2 - yield_normalized)
            stress_severity = max(0, min(1, stress_severity))
            
            features.append({
                'county': county,
                'year': year,
                
                # NDVI features (from Sentinel-2)
                'ndvi_early_mean': round(ndvi_early_mean, 3),
                'ndvi_early_std': round(ndvi_early_std, 3),
                'ndvi_mid_mean': round(ndvi_mid_mean, 3),
                'ndvi_mid_std': round(ndvi_mid_std, 3),
                'ndvi_late_mean': round(ndvi_late_mean, 3),
                'ndvi_late_std': round(ndvi_late_std, 3),
                
                # SAR features (from Sentinel-1)
                'sar_vv_mean': round(sar_vv, 2),
                'sar_vh_mean': round(sar_vh, 2),
                'sar_moisture_proxy': round(sar_moisture, 2),
                
                # ET features (from MODIS)
                'et_seasonal_total': round(et_seasonal, 1),
                'et_anomaly': round(et_anomaly, 1),
                
                # Meteorological
                'gdd_cumulative': round(gdd, 0),
                
                # Stress indicators
                'stress_days_count': stress_days,
                'stress_severity_avg': round(stress_severity, 3)
            })
        
        features_df = pd.DataFrame(features)
        logger.success(f"Generated {len(features_df)} feature records with {len(features_df.columns)-2} features")
        
        return features_df
    
    def create_stress_features(self, df: pd.DataFrame, satellite_df: pd.DataFrame) -> pd.DataFrame:
        """Create features for unsupervised stress detection model"""
        
        logger.info("Creating stress detection features...")
        
        # Merge satellite features
        stress_features = satellite_df.copy()
        
        # Select relevant features for stress detection (no yield info!)
        feature_cols = [
            'county', 'year',
            'ndvi_early_mean', 'ndvi_early_std',
            'ndvi_mid_mean', 'ndvi_mid_std',
            'ndvi_late_mean', 'ndvi_late_std',
            'sar_moisture_proxy',
            'et_anomaly',
            'stress_days_count',
            'stress_severity_avg'
        ]
        
        stress_features = stress_features[feature_cols]
        
        logger.info(f"Stress features shape: {stress_features.shape}")
        logger.info(f"Features: {[c for c in stress_features.columns if c not in ['county', 'year']]}")
        
        return stress_features
    
    def create_yield_features(self, df: pd.DataFrame, satellite_df: pd.DataFrame) -> pd.DataFrame:
        """Create features for supervised yield forecasting model"""
        
        logger.info("Creating yield forecasting features...")
        
        # Merge yield lags with satellite features
        yield_features = df[['county', 'year', 'yield_bu_per_acre'] + 
                           [col for col in df.columns if 'yield_lag' in col]].copy()
        
        yield_features = yield_features.merge(satellite_df, on=['county', 'year'], how='inner')
        
        # Remove rows with missing lag features (first few years per county)
        before = len(yield_features)
        yield_features = yield_features.dropna()
        after = len(yield_features)
        
        logger.info(f"Removed {before - after} rows with missing lag features")
        logger.info(f"Final yield features shape: {yield_features.shape}")
        
        return yield_features
    
    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data into train/validation/test by year"""
        
        config = self.config['data_split']
        
        train = df[df['year'] <= config['train_end_year']]
        val = df[(df['year'] > config['train_end_year']) & (df['year'] <= config['val_end_year'])]
        test = df[df['year'] >= config['test_start_year']]
        
        logger.info(f"Train: {len(train)} records (years <= {config['train_end_year']})")
        logger.info(f"Val:   {len(val)} records (years {config['train_end_year']+1}-{config['val_end_year']})")
        logger.info(f"Test:  {len(test)} records (years >= {config['test_start_year']})")
        
        return train, val, test
    
    def save_features(self, stress_features: pd.DataFrame, yield_features: pd.DataFrame):
        """Save processed features"""
        
        # Save stress features
        stress_dir = self.config['paths']['output_stress']
        os.makedirs(stress_dir, exist_ok=True)
        
        stress_train, stress_val, stress_test = self.split_data(stress_features)
        
        stress_train.to_parquet(f"{stress_dir}/train.parquet", index=False)
        stress_val.to_parquet(f"{stress_dir}/val.parquet", index=False)
        stress_test.to_parquet(f"{stress_dir}/test.parquet", index=False)
        
        logger.success(f"Saved stress features to: {stress_dir}")
        
        # Save yield features
        yield_dir = self.config['paths']['output_yield']
        os.makedirs(yield_dir, exist_ok=True)
        
        yield_train, yield_val, yield_test = self.split_data(yield_features)
        
        yield_train.to_parquet(f"{yield_dir}/train.parquet", index=False)
        yield_val.to_parquet(f"{yield_dir}/val.parquet", index=False)
        yield_test.to_parquet(f"{yield_dir}/test.parquet", index=False)
        
        logger.success(f"Saved yield features to: {yield_dir}")
        
        # Save feature names
        feature_info = {
            'stress_features': [c for c in stress_features.columns if c not in ['county', 'year']],
            'yield_features': [c for c in yield_features.columns if c not in ['county', 'year', 'yield_bu_per_acre']],
            'target': 'yield_bu_per_acre'
        }
        
        import json
        with open(f"{yield_dir}/feature_info.json", 'w') as f:
            json.dump(feature_info, f, indent=2)


@click.command()
@click.option('--config', default='configs/preprocessing_config.yaml', help='Config file')
@click.option('--verbose', is_flag=True, help='Verbose logging')
def main(config, verbose):
    """Preprocess data and create ML features"""
    
    setup_logging(verbose=verbose)
    
    logger.info("="*70)
    logger.info("AgriGuard Data Preprocessing - Container 2")
    logger.info("="*70)
    
    preprocessor = DataPreprocessor(config_path=config)
    
    # Load yield data
    df = preprocessor.load_data()
    
    # Create lag features
    df = preprocessor.create_lag_features(df)
    
    # Generate synthetic satellite features
    satellite_features = preprocessor.generate_synthetic_satellite_features(df)
    
    # Create model-specific features
    stress_features = preprocessor.create_stress_features(df, satellite_features)
    yield_features = preprocessor.create_yield_features(df, satellite_features)
    
    # Save
    preprocessor.save_features(stress_features, yield_features)
    
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Stress features: {stress_features.shape}")
    logger.info(f"Yield features: {yield_features.shape}")
    logger.info("="*70)
    logger.success("Preprocessing complete!")


if __name__ == "__main__":
    main()
