"""
Lightweight yield forecast service
Loads pre-trained model from GCS, serves predictions
"""
from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import joblib
import gcsfs
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
model = None

class ForecastRequest(BaseModel):
    fips: str
    week: int
    year: int
    heat_days: float
    water_deficit: float
    precip: float
    ndvi_avg: float
    ndvi_min: float

@app.on_event("startup")
async def load_model():
    """Load pre-trained model from GCS"""
    global model
    try:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/secrets/agriguard-service-account.json'
        fs = gcsfs.GCSFileSystem()
        
        logger.info("Loading model from GCS...")
        with fs.open('gs://agriguard-ac215-data/models/yield_forecast.pkl', 'rb') as f:
            model = joblib.load(f)
        logger.info("✓ Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "r2": 0.554,
        "mae": 8.32,
        "data_source": "Pre-trained model from GCS"
    }

@app.post("/forecast")
async def forecast(request: ForecastRequest):
    """Forecast yield from stress indicators"""
    if model is None:
        return {"error": "Model not loaded"}
    
    # Prepare features (must match training order)
    features = np.array([[
        request.heat_days,
        request.water_deficit,
        request.precip,
        request.ndvi_avg,
        request.ndvi_min,
        0.0,  # ndvi_std (placeholder)
        1.0   # weeks_completed (placeholder)
    ]])
    
    # Predict
    predicted_yield = model.predict(features)[0]
    uncertainty = 8.32  # MAE from training
    
    return {
        "fips": request.fips,
        "week": request.week,
        "predicted_yield": float(predicted_yield),
        "uncertainty": float(uncertainty),
        "confidence": "medium" if request.week < 30 else "high"
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
