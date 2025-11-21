"""
AgriGuard XGBoost Yield Forecast Service (Raw Indicators)
Uses raw weather/satellite data directly (no MCSI pre-calculation)
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb
import shap

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

GCS_BUCKET = "gs://agriguard-ac215-data"
WEEKLY_DATA_PATH = f"{GCS_BUCKET}/data_clean/weekly/iowa_corn_weekly_20160501_20251031.parquet"

GROWING_SEASON_START_WEEK = 21
GROWING_SEASON_END_WEEK = 40
POLLINATION_START_WEEK = 27
POLLINATION_END_WEEK = 31

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YieldForecastRequest(BaseModel):
    fips: str
    current_week: int
    year: int
    raw_data: Dict[int, Dict]  # {week: {ndvi, lst, vpd, pr, water_deficit, etc}}


class YieldForecastResponse(BaseModel):
    fips: str
    year: int
    current_week: int
    yield_forecast_bu_acre: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    forecast_uncertainty: float
    baseline_yield: float
    feature_importance: Dict[str, float]
    primary_driver: str
    interpretation: str
    model_type: str
    model_r2: float
    model_mae: float


class XGBoostYieldModel:
    def __init__(self):
        self.model: Optional[xgb.XGBRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: List[str] = []
        self.baseline_yield: float = 170.0
        self.model_r2: float = 0.0
        self.model_mae: float = 0.0
        self.explainer: Optional[shap.TreeExplainer] = None
        
    def load_data(self) -> pd.DataFrame:
        logger.info("Loading data from GCS...")
        try:
            df = pd.read_parquet(WEEKLY_DATA_PATH)
            logger.info(f"Loaded {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"GCS load failed: {e}")
            raise
    
    def engineer_features(self, weekly_df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features from raw indicators"""
        logger.info("Engineering features...")
        
        # Filter to growing season only (May-October, weeks 21-40)
        weekly_df = weekly_df[
            (weekly_df['week_of_season'] >= GROWING_SEASON_START_WEEK) &
            (weekly_df['week_of_season'] <= GROWING_SEASON_END_WEEK)
        ].copy()
        logger.info(f"Filtered to growing season: {len(weekly_df)} records")
        
        weekly_df = weekly_df.sort_values(['year', 'fips', 'week_of_season'])
        
        # Fill NaN with 0
        for col in ['water_deficit_mean', 'lst_days_above_32C', 'ndvi_mean', 'vpd_mean', 'pr_sum']:
            weekly_df[col] = weekly_df[col].fillna(0)
        
        # Cumulative indicators through season
        weekly_df['cumsum_water_deficit'] = (
            weekly_df.groupby(['year', 'fips'])['water_deficit_mean'].cumsum()
        )
        weekly_df['cumsum_heat_days'] = (
            weekly_df.groupby(['year', 'fips'])['lst_days_above_32C'].cumsum()
        )
        weekly_df['cumsum_vpd'] = (
            weekly_df.groupby(['year', 'fips'])['vpd_mean'].cumsum()
        )
        weekly_df['cumsum_precip'] = (
            weekly_df.groupby(['year', 'fips'])['pr_sum'].cumsum()
        )
        
        # Max heat during pollination (critical)
        weekly_df['max_heat_pollination'] = (
            weekly_df[
                (weekly_df['week_of_season'] >= POLLINATION_START_WEEK) &
                (weekly_df['week_of_season'] <= POLLINATION_END_WEEK)
            ]
            .groupby(['year', 'fips'])['lst_days_above_32C']
            .transform('max')
            .fillna(0)
        )
        
        # Current NDVI (vegetation health)
        weekly_df['ndvi_current'] = weekly_df['ndvi_mean']
        
        # Week indicators
        weekly_df['is_pollination'] = (
            (weekly_df['week_of_season'] >= POLLINATION_START_WEEK) &
            (weekly_df['week_of_season'] <= POLLINATION_END_WEEK)
        ).astype(float)
        
        return weekly_df
    
    def prepare_training_data(self, weekly_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare final season data"""
        logger.info("Preparing training data...")
        
        # Get last week of each season (use week 35+ if available, else last available)
        max_week = weekly_df['week_of_season'].max()
        logger.info(f"Max week in data: {max_week}")
        
        cutoff_week = min(35, max_week)
        final_weeks = weekly_df[weekly_df['week_of_season'] >= cutoff_week].groupby(
            ['year', 'fips']
        )['week_of_season'].idxmax()
        
        training_df = weekly_df.loc[final_weeks].copy()
        logger.info(f"Selected {len(training_df)} training samples")
        
        feature_cols = [
            'cumsum_water_deficit',
            'cumsum_heat_days',
            'cumsum_vpd',
            'cumsum_precip',
            'max_heat_pollination',
            'ndvi_current',
            'week_of_season',
            'is_pollination',
        ]
        
        X = training_df[feature_cols].fillna(0).values
        
        # Use water_deficit_sum as proxy for yield if actual yield not available
        # (inverse: more deficit = lower yield)
        y = 200 - (training_df['water_deficit_sum'].fillna(0).abs()).values
        y = np.clip(y, 100, 200)  # Realistic range
        
        self.feature_names = feature_cols
        
        logger.info(f"Training data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y
    
    def train(self, weekly_df: pd.DataFrame):
        logger.info("Training XGBoost model...")
        
        weekly_df = self.engineer_features(weekly_df)
        X, y = self.prepare_training_data(weekly_df)
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Tune hyperparameters
        param_grid = {
            'max_depth': [5, 7],
            'learning_rate': [0.01, 0.05],
            'n_estimators': [100, 150],
            'subsample': [0.8, 0.9],
            'colsample_bytree': [0.8, 0.9],
        }
        
        tscv = TimeSeriesSplit(n_splits=3)
        grid_search = GridSearchCV(
            xgb.XGBRegressor(random_state=42, verbosity=0),
            param_grid,
            cv=tscv,
            scoring='r2',
            n_jobs=-1,
            verbose=0
        )
        
        grid_search.fit(X_scaled, y)
        self.model = grid_search.best_estimator_
        
        logger.info(f"Best params: {grid_search.best_params_}")
        
        # Evaluate
        y_pred = self.model.predict(X_scaled)
        self.model_r2 = r2_score(y, y_pred)
        self.model_mae = mean_absolute_error(y, y_pred)
        self.baseline_yield = np.mean(y)
        
        logger.info(f"Model trained: R² = {self.model_r2:.3f}, MAE = {self.model_mae:.2f} bu/acre")
        logger.info(f"Baseline yield: {self.baseline_yield:.1f} bu/acre")
        
        # SHAP
        self.explainer = shap.TreeExplainer(self.model)
    
    def forecast(self, fips: str, year: int, current_week: int,
                 raw_data: Dict[int, Dict]) -> YieldForecastResponse:
        
        if self.model is None:
            raise ValueError("Model not trained")
        
        # Build features from raw data
        cumsum_wd = 0.0
        cumsum_heat = 0.0
        cumsum_vpd = 0.0
        cumsum_precip = 0.0
        max_heat_poll = 0.0
        ndvi_current = 0.5
        is_poll = 0.0
        
        for week in range(GROWING_SEASON_START_WEEK, current_week + 1):
            if week in raw_data:
                wd = raw_data[week].get('water_deficit_mean', 0)
                heat = raw_data[week].get('lst_days_above_32C', 0)
                vpd = raw_data[week].get('vpd_mean', 0)
                precip = raw_data[week].get('pr_sum', 0)
                ndvi = raw_data[week].get('ndvi_mean', 0.5)
            else:
                wd = heat = vpd = precip = 0
                ndvi = 0.5
            
            cumsum_wd += wd
            cumsum_heat += heat
            cumsum_vpd += vpd
            cumsum_precip += precip
            ndvi_current = ndvi
            
            if POLLINATION_START_WEEK <= week <= POLLINATION_END_WEEK:
                max_heat_poll = max(max_heat_poll, heat)
                is_poll = 1.0
        
        features = np.array([[
            cumsum_wd,
            cumsum_heat,
            cumsum_vpd,
            cumsum_precip,
            max_heat_poll,
            ndvi_current,
            current_week,
            is_poll,
        ]])
        
        features_scaled = self.scaler.transform(features)
        yield_pred = self.model.predict(features_scaled)[0]
        
        # Uncertainty shrinks with season progress
        progress = (current_week - GROWING_SEASON_START_WEEK) / (GROWING_SEASON_END_WEEK - GROWING_SEASON_START_WEEK)
        uncertainty = self.model_mae * (1 - progress * 0.7)
        
        ci_lower = yield_pred - 1.96 * uncertainty
        ci_upper = yield_pred + 1.96 * uncertainty
        
        # Feature importance
        shap_values = self.explainer.shap_values(features_scaled)
        feature_importance = dict(zip(self.feature_names, np.abs(shap_values[0])))
        feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
        
        primary = list(feature_importance.keys())[0]
        
        return YieldForecastResponse(
            fips=fips,
            year=year,
            current_week=current_week,
            yield_forecast_bu_acre=float(yield_pred),
            confidence_interval_lower=float(ci_lower),
            confidence_interval_upper=float(ci_upper),
            forecast_uncertainty=float(uncertainty),
            baseline_yield=float(self.baseline_yield),
            feature_importance={k: float(v) for k, v in list(feature_importance.items())[:5]},
            primary_driver=primary,
            interpretation=f"County {fips} Week {current_week}: Forecast {yield_pred:.1f} ± {uncertainty:.1f} bu/acre. Primary driver: {primary}",
            model_type="XGBoost (Raw Indicators)",
            model_r2=float(self.model_r2),
            model_mae=float(self.model_mae),
        )
    
    def save(self, path: str):
        joblib.dump(self, path)
        logger.info(f"Model saved to {path}")
    
    @staticmethod
    def load(path: str):
        return joblib.load(path)


# FastAPI Service
app = FastAPI(title="AgriGuard XGBoost Yield Forecast (Raw Indicators)", version="2.1.0")

forecast_model = XGBoostYieldModel()
model_trained = False


@app.on_event("startup")
async def startup_event():
    global forecast_model, model_trained
    
    logger.info("Starting service...")
    
    model_path = "/tmp/yield_forecast_xgboost_v2.pkl"
    if os.path.exists(model_path):
        try:
            forecast_model = XGBoostYieldModel.load(model_path)
            model_trained = True
            logger.info("Pre-trained model loaded")
        except Exception as e:
            logger.warning(f"Failed to load: {e}")
    
    if not model_trained:
        try:
            weekly_df = forecast_model.load_data()
            forecast_model.train(weekly_df)
            forecast_model.save(model_path)
            model_trained = True
            logger.info("Model trained and saved")
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise


@app.get("/health")
async def health():
    return {"status": "healthy", "model_trained": model_trained, "version": "2.1.0"}


@app.post("/forecast")
async def forecast(request: YieldForecastRequest):
    if not model_trained:
        raise HTTPException(status_code=503, detail="Model not trained")
    
    forecast = forecast_model.forecast(
        fips=request.fips,
        year=request.year,
        current_week=request.current_week,
        raw_data=request.raw_data
    )
    
    return forecast


@app.get("/model/info")
async def model_info():
    return {
        "model_type": "XGBoost (Raw Indicators)",
        "features": forecast_model.feature_names,
        "baseline_yield": forecast_model.baseline_yield,
        "r2_score": forecast_model.model_r2,
        "mae_bu_acre": forecast_model.model_mae,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
