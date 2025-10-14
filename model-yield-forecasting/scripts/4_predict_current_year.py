"""Generate predictions for the current year (2025) - With NDVI + EVI."""

import sys
sys.path.append('/app')

from utils.data_loader import DataLoader
from utils.feature_engineering import RollingWindowFeatureEngineer
import pandas as pd
import numpy as np
import joblib
import json
from io import BytesIO
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnyDatePredictor:
    """Generate forecasts for any date during the season."""
    
    def __init__(self):
        self.loader = DataLoader()
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.load_model()
    
    def load_model(self):
        """Load trained model from GCS."""
        logger.info("Loading model with NDVI + EVI...")
        
        # Load model
        blob = self.loader.bucket.blob("model_yield_forecasting/models/rolling_window_model_ndvi_evi.joblib")
        model_bytes = blob.download_as_bytes()
        self.model = joblib.load(BytesIO(model_bytes))
        
        # Load scaler
        blob = self.loader.bucket.blob("model_yield_forecasting/models/rolling_window_scaler_ndvi_evi.joblib")
        scaler_bytes = blob.download_as_bytes()
        self.scaler = joblib.load(BytesIO(scaler_bytes))
        
        # Load feature names
        blob = self.loader.bucket.blob("model_yield_forecasting/models/rolling_window_features_ndvi_evi.json")
        features_dict = json.loads(blob.download_as_string())
        self.feature_names = features_dict['features']
        
        # Load metrics for uncertainty
        blob = self.loader.bucket.blob("model_yield_forecasting/models/training_metrics_ndvi_evi.json")
        self.metrics = json.loads(blob.download_as_string())
        
        logger.info(f"  Model loaded successfully")
        logger.info(f"  Expected features: {len(self.feature_names)}")
        logger.info(f"  Training RMSE: {self.metrics['rmse']:.2f} bu/acre")
    
    def predict_for_dates(self, year: int, forecast_dates: list):
        """Generate predictions for multiple dates."""
        logger.info("\n" + "="*60)
        logger.info(f"GENERATING {year} PREDICTIONS (WITH NDVI + EVI)")
        logger.info("="*60)
        
        # Load data
        logger.info("\nLoading satellite data...")
        et_df = self.loader.load_et_data()
        lst_df = self.loader.load_lst_data()
        ndvi_evi_df = self.loader.load_ndvi_data()
        
        # Initialize feature engineer
        engineer = RollingWindowFeatureEngineer(et_df, lst_df, ndvi_evi_df)
        
        all_predictions = []
        
        for forecast_date in forecast_dates:
            logger.info(f"\n{'='*50}")
            logger.info(f"Generating predictions for {forecast_date.strftime('%B %d, %Y')}")
            logger.info(f"{'='*50}")
            
            # Create features
            features_df = engineer.create_features_for_date(year, forecast_date)
            
            if len(features_df) == 0:
                logger.warning(f"No features created for {forecast_date.date()}")
                continue
            
            # Align features with training
            for col in self.feature_names:
                if col not in features_df.columns:
                    features_df[col] = 0  # Future data not available
            
            X = features_df[self.feature_names].fillna(0)
            
            # Scale and predict
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            
            # Calculate uncertainty based on data completeness
            data_completeness = features_df['data_completeness'].values if 'data_completeness' in features_df.columns else np.ones(len(features_df)) * 0.5
            
            # Uncertainty decreases as season progresses
            base_rmse = self.metrics['rmse']
            uncertainty = base_rmse * (1.5 - 0.5 * data_completeness)
            
            # Create results DataFrame
            results = pd.DataFrame({
                'fips': features_df['fips'],
                'forecast_date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_yield': predictions,
                'year': year,
                'data_completeness': data_completeness,
                'uncertainty_bu_per_acre': uncertainty,
                'lower_bound': predictions - uncertainty,
                'upper_bound': predictions + uncertainty,
                'days_since_may1': features_df['days_since_may1'].values if 'days_since_may1' in features_df.columns else 0
            })
            
            all_predictions.append(results)
            
            logger.info(f"  Predicted for {len(results)} counties")
            logger.info(f"  Mean prediction: {predictions.mean():.1f} bu/acre")
            logger.info(f"  Range: {predictions.min():.1f} - {predictions.max():.1f} bu/acre")
            logger.info(f"  Avg uncertainty: ±{uncertainty.mean():.1f} bu/acre")
        
        # Combine all forecasts
        predictions_df = pd.concat(all_predictions, ignore_index=True)
        
        return predictions_df
    
    def save_predictions(self, predictions_df, year):
        """Save predictions to GCS."""
        logger.info(f"\nSaving predictions...")
        
        # Save as parquet
        output_path = f"model_yield_forecasting/predictions/predictions_{year}_ndvi_evi.parquet"
        self.loader.save_to_gcs(predictions_df, output_path)
        
        # Save as CSV
        csv_buffer = BytesIO()
        predictions_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        blob = self.loader.bucket.blob(f"model_yield_forecasting/predictions/predictions_{year}_ndvi_evi.csv")
        blob.upload_from_file(csv_buffer, content_type='text/csv')
        
        logger.info(f"  Saved predictions")
    
    def create_prediction_summary(self, predictions_df, year):
        """Create summary of predictions."""
        logger.info("\nCreating prediction summary...")
        
        summary = []
        summary.append("="*70)
        summary.append(f"{year} IOWA CORN YIELD PREDICTIONS - WITH NDVI + EVI")
        summary.append("="*70)
        summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("")
        summary.append("Model uses: ET + LST + NDVI + EVI satellite data")
        summary.append("")
        
        # Group by forecast date
        for forecast_date in sorted(predictions_df['forecast_date'].unique()):
            forecast_data = predictions_df[predictions_df['forecast_date'] == forecast_date]
            
            date_obj = datetime.strptime(forecast_date, '%Y-%m-%d')
            summary.append(f"\n{date_obj.strftime('%B %d, %Y')} Forecast")
            summary.append("-" * 50)
            summary.append(f"  Counties: {len(forecast_data)}")
            summary.append(f"  State Average: {forecast_data['predicted_yield'].mean():.1f} bu/acre")
            summary.append(f"  Avg Uncertainty: ±{forecast_data['uncertainty_bu_per_acre'].mean():.1f} bu/acre")
            summary.append(f"  Range: {forecast_data['predicted_yield'].min():.1f} - {forecast_data['predicted_yield'].max():.1f} bu/acre")
            summary.append(f"  Data Completeness: {forecast_data['data_completeness'].mean()*100:.1f}%")
            
            # Top 5 counties
            top_5 = forecast_data.nlargest(5, 'predicted_yield')
            summary.append(f"\n  Top 5 Counties:")
            for idx, row in top_5.iterrows():
                summary.append(f"    {row['fips']}: {row['predicted_yield']:.1f} ± {row['uncertainty_bu_per_acre']:.1f} bu/acre")
        
        summary.append("\n" + "="*70)
        summary.append("MODEL CAPABILITIES")
        summary.append("="*70)
        summary.append("✓ Can predict yield for ANY date from May 1 to September 30")
        summary.append("✓ Uses multi-sensor fusion: ET + LST + NDVI + EVI")
        summary.append("✓ NDVI: Best for sparse vegetation (early season)")
        summary.append("✓ EVI: Best for dense canopy (reproductive/grain fill)")
        summary.append("✓ Uncertainty decreases as the season progresses")
        summary.append("")
        
        summary_text = "\n".join(summary)
        
        # Save
        blob = self.loader.bucket.blob(f"model_yield_forecasting/predictions/predictions_{year}_summary_ndvi_evi.txt")
        blob.upload_from_string(summary_text, content_type='text/plain')
        
        print(summary_text)


def main():
    """Main prediction pipeline."""
    logger.info("="*60)
    logger.info("ROLLING WINDOW FORECASTING - 2025 PREDICTIONS (WITH NDVI + EVI)")
    logger.info("="*60)
    
    predictor = AnyDatePredictor()
    
    # Define forecast dates
    forecast_dates = [
        datetime(2025, 6, 15),
        datetime(2025, 6, 30),
        datetime(2025, 7, 15),
        datetime(2025, 7, 31),
        datetime(2025, 8, 15),
        datetime(2025, 8, 31),
        datetime(2025, 9, 15),
        datetime(2025, 9, 30),
    ]
    
    logger.info(f"\nGenerating predictions for {len(forecast_dates)} dates in 2025")
    
    predictions = predictor.predict_for_dates(2025, forecast_dates)
    predictor.save_predictions(predictions, 2025)
    predictor.create_prediction_summary(predictions, 2025)
    
    logger.info("\n" + "="*60)
    logger.info("PREDICTION GENERATION COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    main()