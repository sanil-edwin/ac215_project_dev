"""
Corn Yield Prediction Model Training

Trains an ensemble model (LightGBM + Random Forest) to predict
county-level corn yields using engineered features.

Author: AgriGuard Team
Date: November 2025
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib
import logging
import json
from pathlib import Path
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CornYieldModel:
    """
    Ensemble model for corn yield prediction
    
    Combines LightGBM (70%) and Random Forest (30%) for robust predictions.
    """
    
    def __init__(
        self,
        bucket_name='agriguard-ac215-data',
        lgbm_weight=0.7,
        rf_weight=0.3
    ):
        """
        Initialize model trainer
        
        Args:
            bucket_name: GCS bucket for data
            lgbm_weight: Weight for LightGBM predictions
            rf_weight: Weight for Random Forest predictions
        """
        self.bucket_name = bucket_name
        self.lgbm_weight = lgbm_weight
        self.rf_weight = rf_weight
        
        # Models
        self.lgbm_model = None
        self.rf_model = None
        self.scaler = StandardScaler()
        
        # Feature names (will be set during training)
        self.feature_names = None
        
        # Model hyperparameters
        self.lgbm_params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'max_depth': -1,
            'min_child_samples': 20,
            'verbosity': -1,
            'seed': 42
        }
        
        self.rf_params = {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 10,
            'min_samples_leaf': 5,
            'max_features': 'sqrt',
            'n_jobs': -1,
            'random_state': 42
        }
    
    def load_features(
        self,
        year_start: int = 2016,
        year_end: int = 2024
    ) -> pd.DataFrame:
        """
        Load engineered features from GCS
        
        Args:
            year_start: Start year
            year_end: End year
            
        Returns:
            DataFrame with features and target
        """
        logger.info(f"Loading features for {year_start}-{year_end}")
        
        feature_path = (
            f'gs://{self.bucket_name}/processed/features/'
            f'corn_yield_features_{year_start}_{year_end}.parquet'
        )
        
        df = pd.read_parquet(feature_path)
        logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
        
        return df
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        test_year: int = 2024
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split data into train and test sets
        
        Args:
            df: DataFrame with features and target
            test_year: Year to use as test set
            
        Returns:
            X_train, X_test, y_train, y_test
        """
        logger.info(f"Preparing data with test year = {test_year}")
        
        # Identify feature columns (exclude metadata and target)
        exclude_cols = ['fips', 'year', 'yield_bu_per_acre', 'county_name']
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        
        # Split by year
        train_df = df[df['year'] < test_year].copy()
        test_df = df[df['year'] == test_year].copy()
        
        logger.info(f"Train: {len(train_df)} records ({train_df['year'].min()}-{train_df['year'].max()})")
        logger.info(f"Test: {len(test_df)} records ({test_year})")
        
        # Extract features and target
        X_train = train_df[feature_cols]
        X_test = test_df[feature_cols]
        y_train = train_df['yield_bu_per_acre']
        y_test = test_df['yield_bu_per_acre']
        
        # Store feature names
        self.feature_names = feature_cols
        
        # Handle missing values (forward fill then zero)
        X_train = X_train.fillna(method='ffill').fillna(0)
        X_test = X_test.fillna(method='ffill').fillna(0)
        
        logger.info(f"Feature completeness after imputation: 100%")
        
        return X_train, X_test, y_train, y_test
    
    def train_with_cv(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        n_splits: int = 5
    ) -> Dict:
        """
        Train models with time-series cross-validation
        
        Args:
            X_train: Training features
            y_train: Training target
            n_splits: Number of CV folds
            
        Returns:
            Dictionary with CV results
        """
        logger.info("="*60)
        logger.info("TRAINING WITH TIME-SERIES CROSS-VALIDATION")
        logger.info("="*60)
        
        # Time-series cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        cv_results = {
            'lgbm_scores': [],
            'rf_scores': [],
            'ensemble_scores': []
        }
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train), 1):
            logger.info(f"\nFold {fold}/{n_splits}")
            
            # Split fold
            X_fold_train = X_train.iloc[train_idx]
            X_fold_val = X_train.iloc[val_idx]
            y_fold_train = y_train.iloc[train_idx]
            y_fold_val = y_train.iloc[val_idx]
            
            # Train LightGBM
            lgb_train = lgb.Dataset(X_fold_train, y_fold_train)
            lgb_val = lgb.Dataset(X_fold_val, y_fold_val, reference=lgb_train)
            
            lgbm_fold = lgb.train(
                self.lgbm_params,
                lgb_train,
                num_boost_round=500,
                valid_sets=[lgb_val],
                callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
            )
            
            lgbm_pred = lgbm_fold.predict(X_fold_val)
            lgbm_mae = mean_absolute_error(y_fold_val, lgbm_pred)
            cv_results['lgbm_scores'].append(lgbm_mae)
            
            # Train Random Forest
            rf_fold = RandomForestRegressor(**self.rf_params)
            rf_fold.fit(X_fold_train, y_fold_train)
            rf_pred = rf_fold.predict(X_fold_val)
            rf_mae = mean_absolute_error(y_fold_val, rf_pred)
            cv_results['rf_scores'].append(rf_mae)
            
            # Ensemble prediction
            ensemble_pred = (
                self.lgbm_weight * lgbm_pred +
                self.rf_weight * rf_pred
            )
            ensemble_mae = mean_absolute_error(y_fold_val, ensemble_pred)
            cv_results['ensemble_scores'].append(ensemble_mae)
            
            logger.info(f"  LightGBM MAE: {lgbm_mae:.2f} bu/acre")
            logger.info(f"  Random Forest MAE: {rf_mae:.2f} bu/acre")
            logger.info(f"  Ensemble MAE: {ensemble_mae:.2f} bu/acre")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("CROSS-VALIDATION RESULTS")
        logger.info("="*60)
        logger.info(f"LightGBM:")
        logger.info(f"  Mean MAE: {np.mean(cv_results['lgbm_scores']):.2f} ± {np.std(cv_results['lgbm_scores']):.2f}")
        logger.info(f"Random Forest:")
        logger.info(f"  Mean MAE: {np.mean(cv_results['rf_scores']):.2f} ± {np.std(cv_results['rf_scores']):.2f}")
        logger.info(f"Ensemble:")
        logger.info(f"  Mean MAE: {np.mean(cv_results['ensemble_scores']):.2f} ± {np.std(cv_results['ensemble_scores']):.2f}")
        logger.info("="*60 + "\n")
        
        return cv_results
    
    def train_final_models(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ):
        """
        Train final models on all training data
        
        Args:
            X_train: Training features
            y_train: Training target
        """
        logger.info("Training final models on all training data...")
        
        # Train LightGBM
        logger.info("Training LightGBM...")
        lgb_train = lgb.Dataset(X_train, y_train)
        self.lgbm_model = lgb.train(
            self.lgbm_params,
            lgb_train,
            num_boost_round=500
        )
        logger.info("  ✓ LightGBM trained")
        
        # Train Random Forest
        logger.info("Training Random Forest...")
        self.rf_model = RandomForestRegressor(**self.rf_params)
        self.rf_model.fit(X_train, y_train)
        logger.info("  ✓ Random Forest trained")
    
    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict:
        """
        Evaluate models on test set
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info("="*60)
        logger.info("EVALUATING ON TEST SET")
        logger.info("="*60)
        
        # Predictions
        lgbm_pred = self.lgbm_model.predict(X_test)
        rf_pred = self.rf_model.predict(X_test)
        ensemble_pred = (
            self.lgbm_weight * lgbm_pred +
            self.rf_weight * rf_pred
        )
        
        # Metrics for each model
        metrics = {}
        
        for name, pred in [
            ('LightGBM', lgbm_pred),
            ('Random Forest', rf_pred),
            ('Ensemble', ensemble_pred)
        ]:
            mae = mean_absolute_error(y_test, pred)
            rmse = np.sqrt(mean_squared_error(y_test, pred))
            r2 = r2_score(y_test, pred)
            
            metrics[name] = {
                'MAE': mae,
                'RMSE': rmse,
                'R2': r2
            }
            
            logger.info(f"\n{name}:")
            logger.info(f"  MAE:  {mae:.2f} bu/acre")
            logger.info(f"  RMSE: {rmse:.2f} bu/acre")
            logger.info(f"  R²:   {r2:.4f}")
        
        # Residual analysis
        residuals = y_test - ensemble_pred
        logger.info(f"\nResidual Analysis (Ensemble):")
        logger.info(f"  Mean error: {residuals.mean():.2f} bu/acre")
        logger.info(f"  Std error:  {residuals.std():.2f} bu/acre")
        logger.info(f"  Max overpredict: {residuals.min():.2f} bu/acre")
        logger.info(f"  Max underpredict: {residuals.max():.2f} bu/acre")
        
        logger.info("="*60 + "\n")
        
        return metrics
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Get feature importance from models
        
        Args:
            top_n: Number of top features to return
            
        Returns:
            DataFrame with feature importance
        """
        # LightGBM feature importance
        lgbm_importance = pd.DataFrame({
            'feature': self.feature_names,
            'lgbm_importance': self.lgbm_model.feature_importance(importance_type='gain')
        })
        
        # Random Forest feature importance
        rf_importance = pd.DataFrame({
            'feature': self.feature_names,
            'rf_importance': self.rf_model.feature_importances_
        })
        
        # Merge and average
        importance = lgbm_importance.merge(rf_importance, on='feature')
        importance['avg_importance'] = (
            importance['lgbm_importance'] * self.lgbm_weight +
            importance['rf_importance'] * self.rf_weight
        )
        
        # Sort and return top N
        importance = importance.sort_values('avg_importance', ascending=False)
        
        logger.info(f"\nTop {top_n} Most Important Features:")
        logger.info("="*60)
        for idx, row in importance.head(top_n).iterrows():
            logger.info(f"{row['feature']:<50} {row['avg_importance']:.1f}")
        logger.info("="*60 + "\n")
        
        return importance.head(top_n)
    
    def save_models(self, output_dir: str = './models'):
        """
        Save trained models and metadata
        
        Args:
            output_dir: Directory to save models
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving models to {output_dir}...")
        
        # Save LightGBM
        lgbm_path = output_path / 'lgbm_model.txt'
        self.lgbm_model.save_model(str(lgbm_path))
        logger.info(f"  ✓ Saved LightGBM to {lgbm_path}")
        
        # Save Random Forest
        rf_path = output_path / 'rf_model.pkl'
        joblib.dump(self.rf_model, rf_path)
        logger.info(f"  ✓ Saved Random Forest to {rf_path}")
        
        # Save feature names
        features_path = output_path / 'feature_names.json'
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f, indent=2)
        logger.info(f"  ✓ Saved feature names to {features_path}")
        
        # Save model config
        config = {
            'lgbm_weight': self.lgbm_weight,
            'rf_weight': self.rf_weight,
            'lgbm_params': self.lgbm_params,
            'rf_params': self.rf_params,
            'n_features': len(self.feature_names),
            'training_date': str(pd.Timestamp.now())
        }
        config_path = output_path / 'model_config.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"  ✓ Saved config to {config_path}")
        
        logger.info("All models saved successfully!\n")
    
    def upload_to_gcs(self, local_dir: str = './models'):
        """
        Upload models to GCS
        
        Args:
            local_dir: Local directory with models
        """
        from google.cloud import storage
        
        logger.info("Uploading models to GCS...")
        
        client = storage.Client()
        bucket = client.bucket(self.bucket_name)
        
        local_path = Path(local_dir)
        for file_path in local_path.glob('*'):
            if file_path.is_file():
                blob_name = f'models/corn_yield_model/{file_path.name}'
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                logger.info(f"  ✓ Uploaded {file_path.name}")
        
        logger.info("All models uploaded to GCS!\n")


def main():
    """Main training pipeline"""
    
    logger.info("\n" + "="*60)
    logger.info("CORN YIELD PREDICTION MODEL TRAINING")
    logger.info("="*60 + "\n")
    
    # Initialize model
    model = CornYieldModel()
    
    # Load features
    df = model.load_features(year_start=2016, year_end=2024)
    
    # Prepare data (2024 as test set)
    X_train, X_test, y_train, y_test = model.prepare_data(df, test_year=2024)
    
    # Cross-validation
    cv_results = model.train_with_cv(X_train, y_train, n_splits=5)
    
    # Train final models
    model.train_final_models(X_train, y_train)
    
    # Evaluate
    metrics = model.evaluate(X_test, y_test)
    
    # Feature importance
    importance = model.get_feature_importance(top_n=20)
    
    # Save models
    model.save_models(output_dir='./models')
    
    # Upload to GCS
    model.upload_to_gcs(local_dir='./models')
    
    logger.info("="*60)
    logger.info("TRAINING COMPLETE!")
    logger.info("="*60)
    logger.info(f"\nFinal Model Performance (Test Set 2024):")
    logger.info(f"  MAE:  {metrics['Ensemble']['MAE']:.2f} bu/acre")
    logger.info(f"  RMSE: {metrics['Ensemble']['RMSE']:.2f} bu/acre")
    logger.info(f"  R²:   {metrics['Ensemble']['R2']:.4f}")
    logger.info("\nModels saved to: ./models/")
    logger.info(f"Models uploaded to: gs://{model.bucket_name}/models/corn_yield_model/")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    main()
