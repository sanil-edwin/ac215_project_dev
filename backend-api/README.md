# Backend API Service

**Complete FastAPI server with 5 endpoints for MS4**

## Files

- `api_extended.py` - Main FastAPI application
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container definition
- `models/` - **YOU NEED TO ADD THIS FOLDER**

## Setup

### 1. Copy Your Models
```bash
# Copy models from your existing model_serving
cp -r ../mcsi-ml-deployment/containers/model_serving/models ./models

# You need these files:
# models/rf_model.pkl
# models/feature_names.json
# models/model_config.json
```

### 2. Test Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run API
python api_extended.py

# Visit http://localhost:8080
# API docs at http://localhost:8080/docs
```

### 3. Deploy
```bash
# Use deployment scripts in ../deployment/
cd ../deployment
./deploy.sh
```

## API Endpoints

- `GET /health` - Health check
- `GET /api/counties` - List all 99 Iowa counties
- `GET /api/mcsi/{fips}` - Calculate MCSI for county
- `GET /api/predict/{fips}?year=YYYY` - Predict yield
- `GET /api/stress/map` - Stress map data
- `GET /api/historical/{fips}?year=YYYY` - Historical trends

## Environment

- Python 3.11
- FastAPI
- Runs on port 8080
