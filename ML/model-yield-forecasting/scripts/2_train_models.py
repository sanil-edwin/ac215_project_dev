"""Train rolling window yield forecasting model - With NDVI + EVI."""

import sys
sys.path.append('/app')

from utils.data_loader import DataLoader
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import xgboost as xgb
import joblib
import logging
import json
from io import BytesIO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RollingWindowForecaster:
    """Train single model that works for any forecast date."""
    
    def __init__(self):
        self.loader = DataLoader()
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.metrics = {}
    
    def load_features(self) -> pd.DataFrame:
        """Load rolling window training features with NDVI + EVI."""
        path = "model_yield_forecasting/features/rolling_window_training_features_ndvi_evi.parquet"
        blob = self.loader.bucket.blob(path)
        content = blob.download_as_bytes()
        return pd.read_parquet(BytesIO(content))
    
    def prepare_data(self, df: pd.DataFrame):
        """Prepare features and target."""
        # Exclude non-feature columns
        exclude_cols = ['year', 'fips', 'yield', 'county', 'cutoff_date']
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        
        X = df[feature_cols].fillna(0)
        y = df['yield'].values
        groups = df['fips'].values  # For group-based CV
        
        logger.info(f"\nData prepared:")
        logger.info(f"  Samples: {len(X)}")
        logger.info(f"  Features: {len(feature_cols)}")
        logger.info(f"  Counties (groups): {len(np.unique(groups))}")
        
        # Check for any issues
        if X.shape[1] == 0:
            raise ValueError("No features found! Check feature engineering.")
        
        return X, y, groups, feature_cols
    
    def train_model(self):
        """Train the rolling window model."""
        logger.info(f"\n{'='*60}")
        logger.info(f"TRAINING ROLLING WINDOW MODEL (WITH NDVI + EVI)")
        logger.info(f"{'='*60}")
        
        # Load data
        df = self.load_features()
        X, y, groups, feature_cols = self.prepare_data(df)
        
        # Scale features
        logger.info("\nScaling features...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Cross-validation setup (group by county to avoid data leakage)
        logger.info("\nStarting 5-fold cross-validation...")
        cv = GroupKFold(n_splits=5)
        
        cv_scores = []
        fold_predictions = []
        fold_actuals = []
        feature_importance_list = []
        
        for fold, (train_idx, val_idx) in enumerate(cv.split(X_scaled, y, groups)):
            logger.info(f"\nFold {fold + 1}/5...")
            
            X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            # Train XGBoost
            model = xgb.XGBRegressor(
                n_estimators=300,
                learning_rate=0.03,
                max_depth=6,
                min_child_weight=3,
                subsample=0.8,
                colsample_bytree=0.8,
                gamma=0.1,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42 + fold,
                n_jobs=-1
            )
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=30,
                verbose=False
            )
            
            # Evaluate
            y_pred = model.predict(X_val)
            rmse = np.sqrt(mean_squared_error(y_val, y_pred))
            mae = mean_absolute_error(y_val, y_pred)
            r2 = r2_score(y_val, y_pred)
            
            cv_scores.append({'rmse': rmse, 'mae': mae, 'r2': r2})
            fold_predictions.extend(y_pred)
            fold_actuals.extend(y_val)
            
            # Store feature importance
            feature_importance_list.append(model.feature_importances_)
            
            logger.info(f"  RMSE: {rmse:.2f} bu/acre")
            logger.info(f"  MAE: {mae:.2f} bu/acre")
            logger.info(f"  R²: {r2:.3f}")
        
        # Train final model on all data
        logger.info(f"\nTraining final model on all data...")
        final_model = xgb.XGBRegressor(
            n_estimators=300,
            learning_rate=0.03,
            max_depth=6,
            min_child_weight=3,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1
        )
        final_model.fit(X_scaled, y, verbose=False)
        
        # Calculate overall metrics
        overall_rmse = np.sqrt(mean_squared_error(fold_actuals, fold_predictions))
        overall_mae = mean_absolute_error(fold_actuals, fold_predictions)
        overall_r2 = r2_score(fold_actuals, fold_predictions)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CROSS-VALIDATION RESULTS:")
        logger.info(f"{'='*60}")
        logger.info(f"  RMSE: {overall_rmse:.2f} ± {np.std([s['rmse'] for s in cv_scores]):.2f} bu/acre")
        logger.info(f"  MAE: {overall_mae:.2f} ± {np.std([s['mae'] for s in cv_scores]):.2f} bu/acre")
        logger.info(f"  R²: {overall_r2:.3f} ± {np.std([s['r2'] for s in cv_scores]):.3f}")
        logger.info(f"{'='*60}")
        
        # Feature importance analysis
        avg_importance = np.mean(feature_importance_list, axis=0)
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': avg_importance
        }).sort_values('importance', ascending=False)
        
        logger.info(f"\nTop 20 Most Important Features:")
        for idx, row in feature_importance.head(20).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")
        
        # Check NDVI/EVI importance
        ndvi_features = feature_importance[feature_importance['feature'].str.startswith('ndvi_')]
        evi_features = feature_importance[feature_importance['feature'].str.startswith('evi_')]
        
        logger.info(f"\nNDVI Features in Top 50: {len(ndvi_features.head(50))}")
        logger.info(f"EVI Features in Top 50: {len(evi_features.head(50))}")
        
        # Store
        self.model = final_model
        self.scaler = scaler
        self.feature_names = feature_cols
        self.feature_importance = feature_importance
        self.metrics = {
            'rmse': overall_rmse,
            'mae': overall_mae,
            'r2': overall_r2,
            'rmse_std': np.std([s['rmse'] for s in cv_scores]),
            'mae_std': np.std([s['mae'] for s in cv_scores]),
            'r2_std': np.std([s['r2'] for s in cv_scores]),
            'cv_scores': cv_scores
        }
        
        self.save_model()
        self.save_metrics()
    
    def save_model(self):
        """Save model and scaler to GCS."""
        logger.info(f"\nSaving model to GCS...")
        
        # Save model
        model_buffer = BytesIO()
        joblib.dump(self.model, model_buffer)
        model_buffer.seek(0)
        
        model_path = "model_yield_forecasting/models/rolling_window_model_ndvi_evi.joblib"
        blob = self.loader.bucket.blob(model_path)
        blob.upload_from_file(model_buffer, content_type='application/octet-stream')
        logger.info(f"  Saved model")
        
        # Save scaler
        scaler_buffer = BytesIO()
        joblib.dump(self.scaler, scaler_buffer)
        scaler_buffer.seek(0)
        
        scaler_path = "model_yield_forecasting/models/rolling_window_scaler_ndvi_evi.joblib"
        blob = self.loader.bucket.blob(scaler_path)
        blob.upload_from_file(scaler_buffer, content_type='application/octet-stream')
        logger.info(f"  Saved scaler")
        
        # Save feature names
        features_dict = {'features': self.feature_names}
        features_json = json.dumps(features_dict, indent=2)
        
        features_path = "model_yield_forecasting/models/rolling_window_features_ndvi_evi.json"
        blob = self.loader.bucket.blob(features_path)
        blob.upload_from_string(features_json, content_type='application/json')
        logger.info(f"  Saved feature names")
        
        # Save feature importance
        importance_csv = self.feature_importance.to_csv(index=False)
        importance_path = "model_yield_forecasting/models/feature_importance_ndvi_evi.csv"
        blob = self.loader.bucket.blob(importance_path)
        blob.upload_from_string(importance_csv, content_type='text/csv')
        logger.info(f"  Saved feature importance")
    
    def save_metrics(self):
        """Save training metrics."""
        logger.info(f"\nSaving metrics...")
        
        metrics_json = json.dumps(self.metrics, indent=2, default=str)
        blob = self.loader.bucket.blob("model_yield_forecasting/models/training_metrics_ndvi_evi.json")
        blob.upload_from_string(metrics_json, content_type='application/json')
        
        logger.info("Metrics saved")


def main():
    """Main training pipeline."""
    logger.info("="*60)
    logger.info("ROLLING WINDOW YIELD FORECASTING - MODEL TRAINING (WITH NDVI + EVI)")
    logger.info("="*60)
    
    forecaster = RollingWindowForecaster()
    forecaster.train_model()
    
    logger.info("\n" + "="*60)
    logger.info("MODEL TRAINING COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    main()