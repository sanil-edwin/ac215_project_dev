# Step-by-Step Implementation Instructions
## AgriGuard MCSI & ML Model Deployment

**Last Updated:** November 16, 2025  
**Estimated Time:** 4-6 hours for complete implementation  
**Difficulty:** Intermediate

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Google Cloud Platform account
- [ ] Project `agriguard-ac215` created
- [ ] Billing enabled on GCP project
- [ ] `gcloud` CLI installed and configured
- [ ] Docker installed
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] Access to `gs://agriguard-ac215-data` bucket

---

## 🚀 Quick Start (10 minutes)

If you just want to get something running quickly:

```bash
# 1. Clone/create project directory
mkdir -p agriguard && cd agriguard

# 2. Copy all provided files to proper locations
# (see directory structure below)

# 3. Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Authenticate with GCP
gcloud auth login
gcloud config set project agriguard-ac215

# 5. Test MCSI locally
python mcsi_calculator.py

# 6. Test feature engineering locally
python feature_builder.py

# 7. Deploy everything
chmod +x deploy.sh
./deploy.sh all
```

---

## 📁 Directory Structure Setup

Create this exact directory structure:

```
agriguard/
├── README.md
├── requirements.txt
├── requirements-test.txt
├── deploy.sh
│
├── src/
│   ├── mcsi_calculator.py
│   ├── feature_builder.py
│   ├── train_model.py
│   └── api.py
│
├── containers/
│   ├── mcsi_processing/
│   │   ├── Dockerfile.mcsi
│   │   ├── requirements.txt
│   │   └── src/
│   │       └── mcsi_calculator.py (copy from src/)
│   │
│   ├── model_training/
│   │   ├── Dockerfile.training
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── feature_builder.py (copy from src/)
│   │       └── train_model.py (copy from src/)
│   │
│   └── model_serving/
│       ├── Dockerfile.serving
│       ├── requirements.txt
│       ├── models/  (will be populated after training)
│       └── src/
│           ├── api.py (copy from src/)
│           └── mcsi_calculator.py (copy from src/)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_mcsi_calculator.py
│   ├── test_feature_builder.py
│   ├── test_model.py
│   └── test_api.py
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── tests.yml
│       └── docker-build.yml
│
└── models/  (created during training)
    ├── lgbm_model.txt
    ├── rf_model.pkl
    ├── feature_names.json
    └── model_config.json
```

---

## 📝 Step 1: Environment Setup (15 minutes)

### 1.1 Create Project Structure

```bash
# Create main directory
mkdir -p agriguard && cd agriguard

# Create subdirectories
mkdir -p src containers/{mcsi_processing,model_training,model_serving}/src
mkdir -p tests .github/workflows models

# Create __init__.py files
touch src/__init__.py tests/__init__.py
```

### 1.2 Copy Implementation Files

Copy all the provided Python files to their appropriate locations:

```bash
# Copy main source files
cp mcsi_calculator.py src/
cp feature_builder.py src/
cp train_model.py src/
cp api.py src/

# Copy to container directories (they need their own copies)
cp src/mcsi_calculator.py containers/mcsi_processing/src/
cp src/feature_builder.py containers/model_training/src/
cp src/train_model.py containers/model_training/src/
cp src/api.py containers/model_serving/src/
cp src/mcsi_calculator.py containers/model_serving/src/

# Copy Dockerfiles
cp Dockerfile.mcsi containers/mcsi_processing/
cp Dockerfile.training containers/model_training/
cp Dockerfile.serving containers/model_serving/

# Copy requirements
cp requirements.txt .
cp requirements.txt containers/mcsi_processing/
cp requirements.txt containers/model_training/
cp requirements.txt containers/model_serving/
cp requirements-test.txt .

# Copy tests
cp test_mcsi_calculator.py tests/
cp test_feature_builder.py tests/

# Copy deployment script
cp deploy.sh .
chmod +x deploy.sh
```

### 1.3 Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
# venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 1.4 Configure GCP

```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project agriguard-ac215

# Set region
gcloud config set run/region us-central1

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    storage.googleapis.com \
    aiplatform.googleapis.com

# Create service account (if not exists)
gcloud iam service-accounts create agriguard-service-account \
    --display-name="AgriGuard Service Account" || true

# Grant permissions
PROJECT_ID=$(gcloud config get-value project)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agriguard-service-account@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agriguard-service-account@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

---

## 🧪 Step 2: Local Testing (30 minutes)

### 2.1 Test MCSI Calculator

```bash
# Test MCSI calculation
cd src
python mcsi_calculator.py

# Expected output:
# - Loading data messages
# - MCSI scores for all counties
# - Summary statistics
# - Top 5 most stressed counties
```

### 2.2 Test Feature Builder

```bash
# Test feature engineering
python feature_builder.py

# Expected output:
# - Loading data for 2016-2024
# - Processing messages
# - Feature matrix saved
# - Summary: ~150 features per county-year
```

**Note:** This may take 5-10 minutes to run as it processes 9 years of data.

### 2.3 Run Unit Tests

```bash
# Run all tests
cd ..
pytest tests/ -v --cov=src --cov-report=html

# Expected:
# - All tests pass (or skip if GCS access needed)
# - Coverage report generated in htmlcov/

# View coverage
open htmlcov/index.html  # Mac
# or
xdg-open htmlcov/index.html  # Linux
```

### 2.4 Test API Locally

```bash
# Start API server
cd src
uvicorn api:app --reload --port 8080

# In another terminal, test endpoints:
curl http://localhost:8080/health
curl http://localhost:8080/model/info
curl "http://localhost:8080/mcsi/19001?start_date=2024-07-01&end_date=2024-07-31"

# Stop server: Ctrl+C
```

---

## 🏗️ Step 3: Build and Test Containers (45 minutes)

### 3.1 Test Docker Builds Locally

```bash
# Build MCSI container
cd containers/mcsi_processing
docker build -t mcsi-processor:test -f Dockerfile.mcsi .

# Test run
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/key.json \
  -v ~/.config/gcloud/application_default_credentials.json:/tmp/keys/key.json:ro \
  mcsi-processor:test

# Build training container
cd ../model_training
docker build -t model-training:test -f Dockerfile.training .

# Build serving container
cd ../model_serving
docker build -t model-serving:test -f Dockerfile.serving .

# Test serving container
docker run -p 8080:8080 --rm model-serving:test
# Visit http://localhost:8080/health
```

### 3.2 Configure Container Registry

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Or for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 🚀 Step 4: Deploy to GCP (60 minutes)

### 4.1 Full Deployment

```bash
# From project root
./deploy.sh all

# This will:
# 1. Build all containers
# 2. Push to GCR
# 3. Deploy MCSI job and API
# 4. Deploy training job
# 5. Deploy serving API
# 6. Run tests
```

**Expected Duration:** 15-20 minutes

### 4.2 Manual Step-by-Step Deployment (Alternative)

If you prefer to deploy components individually:

```bash
# Deploy MCSI only
./deploy.sh mcsi

# Deploy training only
./deploy.sh training

# Deploy serving only
./deploy.sh serving

# Test deployments
./deploy.sh test
```

### 4.3 Verify Deployments

```bash
# Check Cloud Run services
gcloud run services list --region us-central1

# Check Cloud Run jobs
gcloud run jobs list --region us-central1

# Check Cloud Scheduler
gcloud scheduler jobs list --location us-central1

# Get service URLs
gcloud run services describe mcsi-api --region us-central1 --format 'value(status.url)'
gcloud run services describe yield-prediction-api --region us-central1 --format 'value(status.url)'
```

---

## 🎯 Step 5: Train Initial Model (30 minutes)

### 5.1 Trigger Training Job

```bash
# Execute training job
gcloud run jobs execute model-training-job --region us-central1 --wait

# Monitor logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=model-training-job" \
  --limit 50 --format json
```

### 5.2 Verify Model Artifacts

```bash
# Check that models were saved to GCS
gsutil ls gs://agriguard-ac215-data/models/corn_yield_model/

# Expected files:
# - lgbm_model.txt
# - rf_model.pkl
# - feature_names.json
# - model_config.json
```

### 5.3 Update Serving Container with Trained Model

```bash
# Download models
mkdir -p models
gsutil cp -r gs://agriguard-ac215-data/models/corn_yield_model/* models/

# Rebuild and redeploy serving container
cd containers/model_serving
cp -r ../../models ./
docker build -t gcr.io/agriguard-ac215/model-serving:latest -f Dockerfile.serving .
docker push gcr.io/agriguard-ac215/model-serving:latest

# Update Cloud Run service
gcloud run deploy yield-prediction-api \
  --image gcr.io/agriguard-ac215/model-serving:latest \
  --region us-central1
```

---

## ✅ Step 6: Validation & Testing (30 minutes)

### 6.1 Test MCSI API

```bash
# Get MCSI API URL
MCSI_URL=$(gcloud run services describe mcsi-api --region us-central1 --format 'value(status.url)')

# Test health
curl ${MCSI_URL}/health

# Test MCSI for Adair County (19001)
curl "${MCSI_URL}/mcsi/19001?start_date=2024-07-01&end_date=2024-07-31" | jq

# Expected response:
{
  "county_fips": "19001",
  "county_name": "Adair",
  "mcsi_score": 45.2,
  "stress_level": "Moderate",
  "color": "yellow",
  "components": {
    "water_stress": 38.5,
    "heat_stress": 42.1,
    "vegetation_stress": 25.3
  },
  "growth_stage": "pollination",
  "calculation_date": "2024-11-16T..."
}
```

### 6.2 Test Serving API

```bash
# Get Serving API URL
SERVING_URL=$(gcloud run services describe yield-prediction-api --region us-central1 --format 'value(status.url)')

# Test health
curl ${SERVING_URL}/health

# Test model info
curl ${SERVING_URL}/model/info | jq

# Test counties list
curl ${SERVING_URL}/counties | jq
```

### 6.3 Trigger Manual MCSI Calculation

```bash
# Trigger MCSI job manually
gcloud run jobs execute mcsi-weekly-job --region us-central1 --wait

# Check results in GCS
gsutil ls gs://agriguard-ac215-data/processed/mcsi/

# Download and view results
gsutil cp gs://agriguard-ac215-data/processed/mcsi/mcsi_2024-11-10_2024-11-16.parquet .
python -c "import pandas as pd; print(pd.read_parquet('mcsi_2024-11-10_2024-11-16.parquet'))"
```

---

## 📊 Step 7: Monitoring & Maintenance (Ongoing)

### 7.1 Set Up Monitoring Dashboards

```bash
# View Cloud Run metrics
echo "MCSI API: https://console.cloud.google.com/run/detail/us-central1/mcsi-api"
echo "Serving API: https://console.cloud.google.com/run/detail/us-central1/yield-prediction-api"
```

### 7.2 View Logs

```bash
# MCSI API logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mcsi-api" --limit 50

# Serving API logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=yield-prediction-api" --limit 50

# Training job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=model-training-job" --limit 50
```

### 7.3 Schedule Regular Retraining

```bash
# Create scheduler for monthly retraining
gcloud scheduler jobs create http model-retraining-scheduler \
  --location us-central1 \
  --schedule "0 2 1 * *" \
  --http-method POST \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/agriguard-ac215/jobs/model-training-job:run" \
  --oauth-service-account-email agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com
```

---

## 🐛 Troubleshooting Guide

### Issue: "Permission denied" errors

**Solution:**
```bash
# Ensure service account has correct permissions
PROJECT_ID=$(gcloud config get-value project)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:agriguard-service-account@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### Issue: Container fails to start

**Solution:**
```bash
# Check logs
gcloud run services logs read SERVICE_NAME --region us-central1

# Common fixes:
# 1. Increase memory: --memory 4Gi
# 2. Check environment variables
# 3. Verify model files are present
```

### Issue: Models not found in serving API

**Solution:**
```bash
# Download models from GCS
mkdir -p models
gsutil cp -r gs://agriguard-ac215-data/models/corn_yield_model/* models/

# Rebuild serving container with models
cd containers/model_serving
cp -r ../../models ./
docker build -t gcr.io/agriguard-ac215/model-serving:latest .
docker push gcr.io/agriguard-ac215/model-serving:latest
```

### Issue: Data not found in GCS

**Solution:**
```bash
# Verify bucket access
gsutil ls gs://agriguard-ac215-data/data_raw_new/

# Check service account permissions
gcloud projects get-iam-policy agriguard-ac215 \
  --flatten="bindings[].members" \
  --filter="bindings.members:agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com"
```

---

## 📈 Performance Optimization

### For MCSI Processing:
- Use `--cpu 2 --memory 4Gi` for faster processing
- Process counties in parallel (modify code)
- Cache historical baselines

### For Model Training:
- Use `--cpu 4 --memory 8Gi` for training
- Enable GPU for faster training (optional)
- Cache feature matrices

### For Serving API:
- Use `--cpu 2 --memory 4Gi`
- Implement caching for repeated queries
- Use batch prediction for multiple counties

---

## 🎓 Next Steps

After successful deployment:

1. **Integration Testing:** Test end-to-end workflows
2. **User Testing:** Get farmer feedback
3. **Performance Tuning:** Optimize based on usage
4. **Documentation:** Update API docs
5. **MS5 Prep:** Add Kubernetes, Ansible, increase test coverage

---

## 📞 Support

**Documentation:**
- GCP Cloud Run: https://cloud.google.com/run/docs
- LightGBM: https://lightgbm.readthedocs.io/
- FastAPI: https://fastapi.tiangolo.com/

**Common Commands:**
```bash
# View all services
gcloud run services list

# View all jobs
gcloud run jobs list

# View logs
gcloud logging read "resource.type=cloud_run_revision"

# Redeploy a service
gcloud run services update SERVICE_NAME --image IMAGE_URL
```

---

**Implementation Complete!** 🎉

You now have:
- ✅ MCSI calculator deployed and running weekly
- ✅ ML model trained and serving predictions
- ✅ APIs deployed and accessible
- ✅ Automated scheduling configured
- ✅ Monitoring and logging set up

**Total Time:** ~4-6 hours for first-time setup

---

*Last Updated: November 16, 2025*  
*Version: 1.0*  
*Project: AgriGuard AC215_E115*
