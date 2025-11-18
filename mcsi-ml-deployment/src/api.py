"""
AgriGuard Serving API

Provides REST API endpoints for:
- MCSI (Multi-Factor Corn Stress Index) queries
- Corn yield predictions
- Batch predictions

Author: AgriGuard Team
Date: November 2025
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

from google.cloud import storage
import os

def download_models_from_gcs():
    """Download models from GCS to local directory"""
    bucket_name = "agriguard-ac215-data"
    model_path = os.getenv("MODEL_PATH", "models/corn_yield_model/")
    local_dir = Path('./models')
    local_dir.mkdir(exist_ok=True)
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        for blob in bucket.list_blobs(prefix=model_path):
            if blob.name.endswith(('.txt', '.pkl', '.json')):
                filename = blob.name.split('/')[-1]
                local_path = local_dir / filename
                blob.download_to_filename(local_path)
                logger.info(f"Downloaded {filename}")
    except Exception as e:
        logger.error(f"Error downloading models: {e}")
        raise

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AgriGuard API",
    description="Corn stress monitoring and yield prediction for Iowa counties",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model variables
lgbm_model = None
rf_model = None
feature_names = None
model_config = None

# MCSI Calculator (simplified version for API)
from mcsi_calculator import MCSICalculator


# =============================================================================
# Data Models (Request/Response Schemas)
# =============================================================================

class PredictionRequest(BaseModel):
    """Request model for yield prediction"""
    county_fips: str = Field(..., description="5-digit county FIPS code", example="19001")
    year: int = Field(..., description="Year for prediction", example=2025)
    features: Optional[Dict[str, float]] = Field(None, description="Pre-computed features (optional)")


class PredictionResponse(BaseModel):
    """Response model for yield prediction"""
    county_fips: str
    county_name: str
    year: int
    predicted_yield: float
    prediction_interval_95: Dict[str, float]
    confidence: str
    yield_drivers: Dict[str, List[str]]
    scenarios: Dict[str, float]


class MCSIRequest(BaseModel):
    """Request model for MCSI calculation"""
    county_fips: str = Field(..., description="5-digit county FIPS code")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


class MCSIResponse(BaseModel):
    """Response model for MCSI"""
    county_fips: str
    county_name: str
    start_date: str
    end_date: str
    mcsi_score: float
    stress_level: str
    color: str
    components: Dict[str, float]
    growth_stage: str
    calculation_date: str


class BatchPredictionRequest(BaseModel):
    """Request model for batch prediction"""
    county_fips_list: List[str] = Field(..., description="List of county FIPS codes")
    year: int = Field(..., description="Year for prediction")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    models_loaded: bool
    version: str


# =============================================================================
# Startup: Load Models
# =============================================================================

@app.on_event("startup")
async def load_models():
    """Load models at startup"""
    global lgbm_model, rf_model, feature_names, model_config
    
    logger.info("Loading models...")
    download_models_from_gcs()
    
    try:
        # Model directory
        model_dir = Path('./models')
        
        # Load LightGBM
        lgbm_path = model_dir / 'lgbm_model.txt'
        if lgbm_path.exists():
            lgbm_model = lgb.Booster(model_file=str(lgbm_path))
            logger.info("✓ LightGBM model loaded")
        else:
            logger.warning("⚠ LightGBM model not found")
        
        # Load Random Forest
        rf_path = model_dir / 'rf_model.pkl'
        if rf_path.exists():
            rf_model = joblib.load(rf_path)
            logger.info("✓ Random Forest model loaded")
        else:
            logger.warning("⚠ Random Forest model not found")
        
        # Load feature names
        features_path = model_dir / 'feature_names.json'
        if features_path.exists():
            with open(features_path, 'r') as f:
                feature_names = json.load(f)
            logger.info(f"✓ Loaded {len(feature_names)} feature names")
        else:
            logger.warning("⚠ Feature names not found")
        
        # Load model config
        config_path = model_dir / 'model_config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                model_config = json.load(f)
            logger.info("✓ Model config loaded")
        else:
            logger.warning("⚠ Model config not found")
        
        logger.info("Models loaded successfully!")
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        raise


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "AgriGuard API - Corn Stress Monitoring & Yield Prediction",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "mcsi": "/mcsi/{county_fips}",
            "predict": "/predict",
            "batch_predict": "/batch_predict"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if (lgbm_model and rf_model) else "degraded",
        timestamp=datetime.now().isoformat(),
        models_loaded=(lgbm_model is not None and rf_model is not None),
        version="1.0.0"
    )


@app.get("/mcsi/{county_fips}", response_model=MCSIResponse, tags=["MCSI"])
async def get_mcsi(
    county_fips: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get Multi-Factor Corn Stress Index for a county
    
    If dates not provided, uses last 7 days.
    """
    try:
        # Default to last 7 days if dates not provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start = datetime.now() - timedelta(days=7)
            start_date = start.strftime('%Y-%m-%d')
        
        # Calculate MCSI
        calculator = MCSICalculator()
        result = calculator.calculate_mcsi(
            county_fips=county_fips,
            start_date=start_date,
            end_date=end_date
        )
        
        return MCSIResponse(**result)
    
    except Exception as e:
        logger.error(f"Error calculating MCSI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_yield(request: PredictionRequest):
    """
    Predict corn yield for a county-year
    
    If features not provided, will compute them from raw data.
    """
    try:
        if not (lgbm_model and rf_model):
            raise HTTPException(status_code=503, detail="Models not loaded")
        
        # Get or compute features
        if request.features:
            feature_vector = [request.features.get(f, 0) for f in feature_names]
        else:
            # Would call feature_builder here to compute features
            # For now, return error
            raise HTTPException(
                status_code=400,
                detail="Features must be provided. Feature computation not yet implemented in API."
            )
        
        # Make predictions
        lgbm_pred = lgbm_model.predict([feature_vector])[0]
        rf_pred = rf_model.predict([feature_vector])[0]
        
        # Ensemble prediction
        lgbm_weight = model_config.get('lgbm_weight', 0.7)
        rf_weight = model_config.get('rf_weight', 0.3)
        ensemble_pred = lgbm_weight * lgbm_pred + rf_weight * rf_pred
        
        # Uncertainty estimate (simplified)
        # In production, this would be calibrated from validation set
        prediction_std = 12.0  # bu/acre
        
        # Confidence level based on feature quality
        feature_completeness = 1 - (np.array(feature_vector) == 0).mean()
        if feature_completeness > 0.95:
            confidence = "High"
        elif feature_completeness > 0.85:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        # Get county name from data (simplified)
        county_name = f"County {request.county_fips}"
        
        # Identify yield drivers (simplified)
        # In production, use SHAP values
        yield_drivers = {
            "positive": ["Adequate precipitation", "Normal temperatures"],
            "negative": ["Water deficit in August", "Heat stress during pollination"]
        }
        
        # Generate scenarios
        scenarios = {
            "current_conditions": round(ensemble_pred, 1),
            "if_normal_august": round(ensemble_pred + 5, 1),
            "if_dry_august": round(ensemble_pred - 8, 1)
        }
        
        return PredictionResponse(
            county_fips=request.county_fips,
            county_name=county_name,
            year=request.year,
            predicted_yield=round(ensemble_pred, 1),
            prediction_interval_95={
                'lower': round(ensemble_pred - 1.96 * prediction_std, 1),
                'upper': round(ensemble_pred + 1.96 * prediction_std, 1)
            },
            confidence=confidence,
            yield_drivers=yield_drivers,
            scenarios=scenarios
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch_predict", tags=["Prediction"])
async def batch_predict(request: BatchPredictionRequest):
    """
    Batch prediction for multiple counties
    
    Returns predictions for all requested counties.
    """
    try:
        if not (lgbm_model and rf_model):
            raise HTTPException(status_code=503, detail="Models not loaded")
        
        # This would load features for all counties and make predictions
        # For now, return error
        raise HTTPException(
            status_code=501,
            detail="Batch prediction not yet implemented. Use /predict for individual counties."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/counties", tags=["Metadata"])
async def list_counties():
    """List all available Iowa counties"""
    # This would read from GCS
    # For now, return example
    return {
        "counties": [
            {"fips": "19001", "name": "Adair"},
            {"fips": "19003", "name": "Adams"},
            # ... more counties
        ],
        "total": 99
    }


@app.get("/model/info", tags=["Metadata"])
async def model_info():
    """Get model information"""
    if not model_config:
        raise HTTPException(status_code=503, detail="Model config not loaded")
    
    return {
        "model_type": "Ensemble (LightGBM + Random Forest)",
        "lgbm_weight": model_config.get('lgbm_weight'),
        "rf_weight": model_config.get('rf_weight'),
        "n_features": model_config.get('n_features'),
        "training_date": model_config.get('training_date'),
        "expected_performance": {
            "mae": "12-16 bu/acre",
            "rmse": "15-20 bu/acre",
            "r2": "0.70-0.75"
        }
    }


@app.get("/model/features", tags=["Metadata"])
async def list_features():
    """List all features used by the model"""
    if not feature_names:
        raise HTTPException(status_code=503, detail="Feature names not loaded")
    
    # Group features by type
    period_features = [f for f in feature_names if any(p in f for p in ['emergence', 'vegetative', 'pollination', 'grain_fill', 'maturity'])]
    historical_features = [f for f in feature_names if '5yr' in f or 'prev' in f]
    interaction_features = [f for f in feature_names if 'interaction' in f or 'combined' in f]
    
    return {
        "total_features": len(feature_names),
        "feature_groups": {
            "period_features": len(period_features),
            "historical_features": len(historical_features),
            "interaction_features": len(interaction_features),
            "temporal_features": len([f for f in feature_names if 'year' in f])
        },
        "sample_features": feature_names[:20]
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": "The requested endpoint does not exist",
        "path": str(request.url)
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "detail": str(exc)
    }


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # For local development
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
