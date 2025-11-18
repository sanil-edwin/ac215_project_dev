# AgriGuard Complete Implementation Guide
## MCSI + ML Model for Corn Yield Prediction

**Project:** AgriGuard - AC215_E115  
**Created:** November 16, 2025  
**Components:** MCSI Calculator + ML Yield Prediction Model  
**Timeline:** 4 weeks to full deployment

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Implementation Phases](#implementation-phases)
4. [MCSI Implementation](#mcsi-implementation)
5. [ML Model Implementation](#ml-model-implementation)
6. [Testing & CI/CD](#testing--cicd)
7. [Deployment Instructions](#deployment-instructions)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

```bash
# Required tools
- Python 3.10+
- Docker
- gcloud CLI
- Git
- GCP Project: agriguard-ac215

# Required GCP APIs
- Cloud Storage
- Cloud Run
- Cloud Build
- Vertex AI
- Artifact Registry
```

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/agriguard.git
cd agriguard

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Authenticate with GCP
gcloud auth login
gcloud config set project agriguard-ac215

# Set environment variables
export GCS_BUCKET_NAME=agriguard-ac215-data
export PROJECT_ID=agriguard-ac215
export REGION=us-central1
```

---

## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    DATA LAYER (GCS)                        │
│  • Satellite: NDVI, LST (11-23k records)                   │
│  • Weather: Water Deficit, ETo, Precip (181k records)      │
│  • Yields: Historical data (1.4k records, 2016-2024)       │
└──────────────┬─────────────────────────────────────────────┘
               │
     ┌─────────┴──────────┐
     │                    │
     ▼                    ▼
┌─────────────┐    ┌──────────────────┐
│    MCSI     │    │   ML PIPELINE    │
│ Processing  │    │  • Feature Eng   │
│  • Weekly   │    │  • Training      │
│  • Stress   │    │  • Prediction    │
│  • Alerts   │    │  • Serving       │
└──────┬──────┘    └────────┬─────────┘
       │                    │
       └────────┬───────────┘
                │
                ▼
      ┌──────────────────┐
      │  SERVING LAYER   │
      │  • FastAPI       │
      │  • Cloud Run     │
      │  • Vertex AI     │
      └──────────────────┘
```

---

## Implementation Phases

### Phase 1: MCSI Implementation (Week 1) ✅
**Goal:** Real-time corn stress monitoring

**Deliverables:**
- MCSI calculator with 3 stress components
- Cloud Run deployment
- Weekly automated jobs
- FastAPI endpoints
- Alert system

**Time:** 5-7 days

### Phase 2: Feature Engineering (Week 2) ✅
**Goal:** Prepare ML-ready features

**Deliverables:**
- Feature builder (150+ features)
- Temporal aggregations
- Historical baselines
- Feature matrix saved to GCS

**Time:** 5-7 days

### Phase 3: Model Training (Week 3) ✅
**Goal:** Build and validate yield prediction model

**Deliverables:**
- LightGBM + Random Forest ensemble
- Cross-validation pipeline
- Model evaluation (R² > 0.65)
- Model artifacts in GCS

**Time:** 5-7 days

### Phase 4: Deployment (Week 4) ✅
**Goal:** Production deployment

**Deliverables:**
- Vertex AI model deployment
- Serving API (FastAPI)
- Batch prediction pipeline
- Monitoring & logging

**Time:** 5-7 days

---

## MCSI Implementation

### What is MCSI?

**Multi-Factor Corn Stress Index** combines:
- **Water Stress** (45% weight) - from Water Deficit
- **Heat Stress** (35% weight) - from LST
- **Vegetation Stress** (20% weight) - from NDVI

**Output:** 0-100 stress score per county
- 0-30: Low stress (green)
- 30-60: Moderate stress (yellow)
- 60-100: High stress (red)

### MCSI Formula

```
MCSI = (0.45 × Water_Stress + 0.35 × Heat_Stress + 0.20 × Veg_Stress) × Growth_Stage_Multiplier

Where:
- Water_Stress = normalize(cumulative_water_deficit, 0-100)
- Heat_Stress = normalize(days_above_32C, 0-100)
- Veg_Stress = normalize(NDVI_anomaly, 0-100)
- Growth_Stage_Multiplier = 1.5 during pollination, 1.0 otherwise
```

### Directory Structure

```
containers/mcsi_processing/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── mcsi_calculator.py      # Core MCSI logic
│   ├── data_loader.py          # Load from GCS
│   ├── cloud_run_job.py        # Weekly processing
│   └── api.py                  # FastAPI endpoints
├── tests/
│   ├── test_mcsi_calculator.py
│   └── test_api.py
└── README.md
```

### Implementation Files

All MCSI code is provided in:
- `mcsi_calculator.py` - Core calculations
- `data_loader.py` - GCS data loading
- `cloud_run_job.py` - Batch processing
- `api.py` - REST API
- `Dockerfile` - Container config
- `tests/test_mcsi_calculator.py` - Unit tests

**See separate files for complete code.**

---

## ML Model Implementation

### Model Architecture

**Ensemble Approach:**
- **Primary:** LightGBM (70% weight)
  - Fast training (<5 min)
  - Handles missing values
  - Built-in feature importance
  
- **Secondary:** Random Forest (30% weight)
  - Diversifies predictions
  - Robust to outliers
  - Complements gradient boosting

**Target:** County-level corn yield (bushels/acre)

### Feature Engineering

**~150 features per county-year:**

1. **Temporal Aggregations** (per growth period)
   - Mean, max, min, std
   - For: Water Deficit, LST, NDVI, VPD, ETo, Precip
   - Periods: Emergence, Vegetative, Pollination, Grain Fill, Maturity

2. **Stress Indicators**
   - Days with high water deficit (>4mm, >6mm)
   - Days with heat stress (>32°C, >35°C)
   - NDVI anomaly severity
   - Consecutive dry days

3. **Critical Period Metrics**
   - Pollination period (Jul 15 - Aug 15) stress
   - Grain fill period (Aug 16 - Sep 15) stress
   - Early season establishment

4. **Historical Baselines**
   - Deviation from 5-year average
   - Anomaly flags
   - Trend indicators

5. **Interaction Features**
   - Water × Heat stress
   - Critical period combinations
   - Stage-weighted metrics

### Directory Structure

```
containers/model_training/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── feature_builder.py      # Feature engineering
│   ├── train.py                # Model training
│   ├── evaluate.py             # Model evaluation
│   └── utils.py                # Helper functions
├── tests/
│   ├── test_feature_builder.py
│   ├── test_model.py
│   └── test_integration.py
└── README.md

containers/model_serving/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── api.py                  # FastAPI serving
│   ├── predictor.py            # Inference logic
│   └── utils.py
├── tests/
│   └── test_api.py
└── README.md
```

### Training Pipeline

```python
# Simplified workflow
1. Load data from GCS (2016-2024)
2. Build features (~150 per county-year)
3. Split: Train (2016-2023), Test (2024)
4. Train ensemble:
   - LightGBM with 5-fold time-series CV
   - Random Forest with same CV
5. Evaluate on 2024 holdout
6. Save models to GCS
7. Deploy to Vertex AI
```

### Expected Performance

| Metric | Target | Actual (Expected) |
|--------|--------|-------------------|
| R² Score | > 0.65 | 0.70-0.75 |
| MAE | < 18 bu/acre | 12-16 bu/acre |
| RMSE | < 22 bu/acre | 15-20 bu/acre |
| Training Time | < 10 min | 3-5 min (CPU) |
| Inference | < 100ms | 50-80ms |

---

## Testing & CI/CD

### Testing Strategy

**Unit Tests (50%+ coverage):**
- MCSI calculations
- Feature engineering
- Model predictions
- API endpoints

**Integration Tests:**
- End-to-end data pipeline
- API workflows
- Model serving

**Test Structure:**
```
tests/
├── unit/
│   ├── test_mcsi_calculator.py      # 10+ test cases
│   ├── test_feature_builder.py      # 8+ test cases
│   ├── test_model_training.py       # 5+ test cases
│   └── test_api.py                  # 10+ test cases
├── integration/
│   ├── test_mcsi_pipeline.py
│   └── test_ml_pipeline.py
└── conftest.py                      # Shared fixtures
```

### GitHub Actions CI/CD

**Workflows:**
```yaml
.github/workflows/
├── ci.yml              # Main CI pipeline
├── tests.yml           # Test execution
├── docker-build.yml    # Container builds
└── deploy.yml          # Deployment
```

**CI Pipeline:**
1. Code quality (flake8, black)
2. Unit tests (pytest)
3. Integration tests
4. Coverage report (>50%)
5. Docker builds
6. Deploy to Cloud Run (on merge to main)

### Running Tests Locally

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_mcsi_calculator.py -v

# Run with markers
pytest tests/unit/ -m "not slow" -v

# View coverage report
open htmlcov/index.html
```

---

## Deployment Instructions

### MCSI Deployment

```bash
# 1. Build container
cd containers/mcsi_processing
docker build -t gcr.io/${PROJECT_ID}/mcsi-processor:latest .

# 2. Push to Artifact Registry
docker push gcr.io/${PROJECT_ID}/mcsi-processor:latest

# 3. Deploy as Cloud Run Job
gcloud run jobs create mcsi-weekly-job \
  --image gcr.io/${PROJECT_ID}/mcsi-processor:latest \
  --region ${REGION} \
  --set-env-vars GCS_BUCKET_NAME=${GCS_BUCKET_NAME} \
  --memory 4Gi \
  --cpu 2 \
  --max-retries 2 \
  --task-timeout 3600

# 4. Schedule weekly execution
gcloud scheduler jobs create http mcsi-scheduler \
  --location ${REGION} \
  --schedule "0 8 * * 1" \
  --http-method POST \
  --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/mcsi-weekly-job:run" \
  --oauth-service-account-email ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com

# 5. Deploy API
gcloud run deploy mcsi-api \
  --image gcr.io/${PROJECT_ID}/mcsi-processor:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --command uvicorn \
  --args api:app,--host,0.0.0.0,--port,8080
```

### ML Model Deployment

```bash
# 1. Train model locally
cd containers/model_training
python src/train.py --year_start 2016 --year_end 2024

# 2. Deploy to Vertex AI
cd ../../vertex_ai
python deploy_model.py \
  --model-path gs://${GCS_BUCKET_NAME}/models/corn_yield_model \
  --endpoint-name corn-yield-predictor

# 3. Deploy serving API
cd ../containers/model_serving
docker build -t gcr.io/${PROJECT_ID}/model-serving:latest .
docker push gcr.io/${PROJECT_ID}/model-serving:latest

gcloud run deploy yield-prediction-api \
  --image gcr.io/${PROJECT_ID}/model-serving:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2
```

### Verification

```bash
# Test MCSI API
curl https://mcsi-api-HASH-uc.a.run.app/mcsi/19001/2024

# Test ML Prediction API
curl -X POST https://yield-prediction-api-HASH-uc.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
    "county_fips": "19001",
    "year": 2025,
    "features": {...}
  }'

# Check health endpoints
curl https://mcsi-api-HASH-uc.a.run.app/health
curl https://yield-prediction-api-HASH-uc.a.run.app/health
```

---

## Troubleshooting

### Common Issues

#### 1. GCS Authentication Errors
```bash
# Solution: Set up service account
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com

export GOOGLE_APPLICATION_CREDENTIALS=sa-key.json
```

#### 2. Memory Errors in Cloud Run
```bash
# Solution: Increase memory allocation
gcloud run services update SERVICE_NAME \
  --memory 4Gi \
  --cpu 2
```

#### 3. Data Not Found Errors
```bash
# Verify data exists
gsutil ls gs://${GCS_BUCKET_NAME}/data_raw_new/weather/water_deficit/

# Check file permissions
gsutil iam get gs://${GCS_BUCKET_NAME}
```

#### 4. Model Training Failures
```python
# Debug: Check data quality
import pandas as pd
df = pd.read_parquet('gs://agriguard-ac215-data/data_raw_new/weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet')
print(f"Records: {len(df)}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Missing values: {df.isnull().sum().sum()}")
```

#### 5. CI/CD Pipeline Failures
```bash
# Check GitHub Actions logs
# Common fixes:
- Add GCP_SA_KEY to GitHub Secrets
- Enable required GCP APIs
- Update workflow permissions
- Check Docker build context
```

---

## Performance Optimization

### MCSI Processing
- Uses vectorized pandas operations
- Caches historical baselines
- Parallel county processing (if needed)
- **Expected runtime:** 3-5 minutes for 99 counties

### ML Training
- Feature caching to avoid recomputation
- Incremental data loading
- GPU support (optional, not required)
- **Expected runtime:** 3-5 minutes on CPU

### Serving
- Model loaded once at startup
- Feature caching for batch predictions
- Async API endpoints
- **Expected latency:** <100ms per prediction

---

## Monitoring & Alerts

### Cloud Logging

```python
# Set up logging in your code
import logging
from google.cloud import logging as cloud_logging

client = cloud_logging.Client()
client.setup_logging()

logger = logging.getLogger(__name__)
logger.info("MCSI calculation started")
```

### Metrics to Track

**MCSI:**
- Processing time per county
- Number of high-stress counties
- Alert generation rate

**ML Model:**
- Prediction latency
- Feature computation time
- Model accuracy drift
- API request volume

### Setting Up Alerts

```bash
# Create alert policy for high API latency
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High API Latency" \
  --condition-display-name="Latency > 500ms" \
  --condition-threshold-value=0.5 \
  --condition-threshold-duration=60s
```

---

## Next Steps

### After Implementation

1. **Integration Testing**
   - End-to-end workflow validation
   - User acceptance testing
   - Performance benchmarking

2. **Documentation**
   - API documentation (Swagger/OpenAPI)
   - User guides
   - Deployment runbooks

3. **Monitoring Setup**
   - Cloud Monitoring dashboards
   - Alert policies
   - Log-based metrics

4. **MS5 Preparation** (Due Dec 11)
   - Kubernetes migration
   - Ansible playbooks
   - Increase test coverage to 70%
   - Record 6-minute video
   - Write Medium blog post

---

## Support Resources

### Documentation
- [Google Cloud Run](https://cloud.google.com/run/docs)
- [Vertex AI](https://cloud.google.com/vertex-ai/docs)
- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Project Resources
- GCP Project: `agriguard-ac215`
- Data Bucket: `gs://agriguard-ac215-data`
- Region: `us-central1`

### Getting Help
- Review implementation guides in this package
- Check GitHub Issues
- Review Cloud Logging for errors
- Test locally before deploying

---

**Implementation Package Contents:**
1. ✅ MCSI Calculator (`mcsi_calculator.py`)
2. ✅ Feature Builder (`feature_builder.py`)
3. ✅ Model Training (`train.py`)
4. ✅ Model Serving API (`api.py`)
5. ✅ Test Suite (complete `tests/` directory)
6. ✅ CI/CD Workflows (`.github/workflows/`)
7. ✅ Docker Configurations (all `Dockerfile`s)
8. ✅ Deployment Scripts (`deploy.sh`)

**Ready to implement!** Follow the phases sequentially for best results.

---

*Created: November 16, 2025*  
*Version: 1.0*  
*For: AgriGuard AC215_E115 Project*
