# AgriGuard MCSI + ML System - FULLY OPERATIONAL! 🎉✅

**Deployed:** November 17, 2025  
**Project:** agriguard-ac215  
**Region:** us-central1  
**Status:** ✅ **FULLY OPERATIONAL** - All Systems Live!

---

## 🎯 DEPLOYMENT COMPLETE

All systems are deployed, tested, and operational:
- ✅ MCSI Calculation Job - Scheduled & Running
- ✅ Model Training Pipeline - Tested & Working  
- ✅ Yield Prediction API - **LIVE & HEALTHY**

**API Status:** https://yield-prediction-api-uxtsuzru6a-uc.a.run.app/health
```json
{"status":"healthy","models_loaded":true}
```

---

## 📊 What's Deployed

### 1. MCSI Calculation System
**Purpose:** Calculate Multi-Factor Corn Stress Index for 99 Iowa counties

- **Type:** Cloud Run Job
- **Name:** `mcsi-weekly-job`
- **Schedule:** Every Monday at 8:00 AM Central Time
- **Resources:** 2 CPU, 2GB RAM
- **Timeout:** 30 minutes
- **Container:** `us-central1-docker.pkg.dev/agriguard-ac215/agriguard/mcsi-processor:latest`
- **Status:** ✅ Deployed & Scheduled

**What it does:**
- Loads water deficit, LST, and NDVI data from GCS
- Calculates stress scores for all 99 Iowa counties
- Combines water stress (45%), heat stress (35%), vegetation stress (20%)
- Saves results to `gs://agriguard-ac215-data/processed/mcsi/`

**Manual execution:**
```bash
gcloud run jobs execute mcsi-weekly-job --region us-central1
```

---

### 2. Yield Prediction API ⭐ **LIVE**
**Purpose:** Serve real-time corn yield predictions using Random Forest ML model

- **Type:** Cloud Run Service
- **Name:** `yield-prediction-api`
- **URL:** https://yield-prediction-api-uxtsuzru6a-uc.a.run.app
- **Resources:** 2 CPU, 4GB RAM
- **Access:** Public (unauthenticated)
- **Container:** `us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-serving:latest`
- **Status:** ✅ **HEALTHY & SERVING**
- **Model:** Random Forest (MAE: 14.58 bu/acre)

**Endpoints:**

#### Health Check ✅
```bash
curl https://yield-prediction-api-uxtsuzru6a-uc.a.run.app/health
```

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": true
}
```

#### Get Model Info
```bash
curl https://yield-prediction-api-uxtsuzru6a-uc.a.run.app/model/info
```

**Response:**
```json
{
  "model": "Random Forest",
  "mae": "14.58 bu/acre"
}
```

---

### 3. Model Training Pipeline
**Purpose:** Train ML models on historical data

- **Type:** Cloud Run Job
- **Name:** `model-training-job`
- **Schedule:** On-demand (manual execution)
- **Resources:** 4 CPU, 8GB RAM
- **Timeout:** 60 minutes
- **Container:** `us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-training:latest`
- **Status:** ✅ Tested Successfully

**What it does:**
- Loads features from `gs://agriguard-ac215-data/processed/features/corn_yield_features_2016_2024.parquet`
- Trains Random Forest + LightGBM ensemble models
- Performs 5-fold time-series cross-validation
- Saves models to `gs://agriguard-ac215-data/models/corn_yield_model/`

**Last Training Results:**
- **Date:** November 17, 2025
- **Records:** 824 county-years (2016-2024)
- **Features:** 141 features
- **Cross-validation MAE:** 14.44 ± 2.00 bu/acre
- **Random Forest MAE:** 14.58 bu/acre
- **Test Set (2024) MAE:** 14.87 bu/acre

**Manual execution:**
```bash
gcloud run jobs execute model-training-job --region us-central1
```

**Monitor training:**
```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=model-training-job" \
    --limit 50 \
    --format "table(timestamp, textPayload)"
```

---

## 🗂️ Data Architecture

### GCS Bucket Structure
```
gs://agriguard-ac215-data/
│
├── data_raw/                          # Original data
│   ├── yields/                        # USDA NASS yield data (2010-2024)
│   │   └── iowa_corn_yields_2010_2025.csv
│   └── masks/                         # Corn field masks (CDL 2010-2024)
│       └── corn/
│
├── data_raw_new/                      # Corn-masked indicators
│   ├── modis/
│   │   ├── ndvi/                      # Vegetation index (11,187 records)
│   │   ├── lst/                       # Land surface temperature (22,770 records)
│   │   └── et/                        # Evapotranspiration (10,593 records)
│   └── weather/
│       ├── vpd/                       # Vapor pressure deficit (181,170 records)
│       ├── eto/                       # Reference evapotranspiration (181,170 records)
│       ├── pr/                        # Precipitation (181,071 records)
│       └── water_deficit/             # ETo - Precipitation (181,071 records)
│
├── processed/                         # Processed outputs
│   ├── features/                      # ML features
│   │   └── corn_yield_features_2016_2024.parquet  ✅ (824 records, 145 features)
│   └── mcsi/                          # MCSI calculation results
│       └── mcsi_YYYY-MM-DD_YYYY-MM-DD.parquet
│
└── models/                            # Trained ML models ✅
    └── corn_yield_model/
        ├── lgbm_model.txt             # LightGBM model (945 KB)
        ├── rf_model.pkl               # Random Forest model (1.8 MB) ✅ LOADED
        ├── feature_names.json         # Feature list (141 features)
        └── model_config.json          # Model metadata
```

### Data Coverage
- **Spatial:** All 99 Iowa counties
- **Temporal:** 2016-2025 growing seasons (May-October)
- **Total Records:** 770,547 indicator observations
- **Features Built:** 824 county-year combinations
- **Yields:** 2010-2024 (ground truth for training)

---

## 🔄 Automated Workflows

### Weekly MCSI Calculation
**Schedule:** Every Monday at 8:00 AM Central Time

**Workflow:**
1. Cloud Scheduler triggers `mcsi-weekly-schedule`
2. Executes `mcsi-weekly-job` on Cloud Run
3. Loads latest week of satellite & weather data
4. Calculates MCSI for all 99 counties
5. Saves results to GCS
6. Logs completion status

**View schedule:**
```bash
gcloud scheduler jobs describe mcsi-weekly-schedule --location us-central1
```

**Manually trigger:**
```bash
gcloud scheduler jobs run mcsi-weekly-schedule --location us-central1
```

---

## 🔧 Management Commands

### Check Service Status
```bash
# List all services
gcloud run services list --region us-central1

# Get serving API details
gcloud run services describe yield-prediction-api --region us-central1

# View API logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=yield-prediction-api" \
    --limit 50 \
    --format "table(timestamp, textPayload)"
```

### Manage Jobs
```bash
# List all jobs
gcloud run jobs list --region us-central1

# View job executions
gcloud run jobs executions list --job mcsi-weekly-job --region us-central1

# Check execution details
gcloud run jobs executions describe EXECUTION_NAME --region us-central1

# View job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=mcsi-weekly-job" \
    --limit 50
```

### Update Containers
```bash
# In Cloud Shell
cd ~/model_serving

# Rebuild container
docker build -t us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-serving:latest .
docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-serving:latest

# Update service with new image
gcloud run services update yield-prediction-api \
    --image us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-serving:latest \
    --region us-central1
```

### Retrain Models
```bash
# Execute training job
gcloud run jobs execute model-training-job --region us-central1

# Wait for completion (~5-10 minutes)
# Models automatically saved to GCS

# Restart API to load new models
gcloud run services update yield-prediction-api \
    --region us-central1 \
    --update-env-vars RELOAD=$(date +%s)
```

---

## 📈 Model Performance

### Actual Performance (Trained November 17, 2025)
- **Cross-Validation MAE:** 14.44 ± 2.00 bu/acre
- **Random Forest MAE:** 14.58 bu/acre  
- **Test Set (2024) MAE:** 14.87 bu/acre
- **Test Set RMSE:** 17.82 bu/acre
- **Features Used:** 141 features
- **Training Data:** 750 county-years (2016-2023)
- **Test Data:** 74 county-years (2024)

### Feature Categories
1. **Period Features** (~75 features)
   - 5 growth stages × 15 metrics
   - Emergence, Vegetative, Pollination, Grain Fill, Maturity

2. **Stress Indicators** (~30 features)
   - Days above temperature thresholds
   - Cumulative water deficits
   - Consecutive dry days
   - NDVI anomalies

3. **Historical Features** (~20 features)
   - 5-year yield averages
   - Previous year performance
   - Trend analysis

4. **Temporal Features** (~16 features)
   - Year trends
   - Drought year indicators
   - Seasonal patterns

### Most Important Features (Top 5)
1. **yield_5yr_mean** - 5-year historical yield average (630,885 importance)
2. **yield_prev_year** - Previous year yield (364,469 importance)
3. **year_since_2016** - Temporal trend (330,976 importance)
4. **yield_5yr_std** - Yield variability (260,579 importance)
5. **yield_5yr_trend** - Long-term trend (191,981 importance)

---

## 🎯 MCSI Calculation

### Stress Components

**Water Stress (45% weight)**
- Based on cumulative water deficit (ETo - Precipitation)
- Thresholds: 2mm, 4mm, 6mm per day
- Critical during pollination period

**Heat Stress (35% weight)**
- Based on LST (land surface temperature)
- Thresholds: 32°C, 35°C, 38°C
- Critical during tasseling/pollination

**Vegetation Stress (20% weight)**
- Based on NDVI anomaly from 5-year baseline
- Thresholds: -10%, -20%, -30%
- Indicates overall crop health

### Growth Stage Multipliers
- **Pollination (July 15 - Aug 15):** 2.0x (most critical)
- **Grain Fill (Aug 16 - Sep 15):** 1.5x
- **Other periods:** 1.0x

### Stress Levels
- **Low:** MCSI < 30 (minimal stress)
- **Moderate:** MCSI 30-50 (watch closely)
- **High:** MCSI 50-70 (yield impacts likely)
- **Severe:** MCSI > 70 (significant yield loss expected)

---

## 🔐 Security & Access

### Service Accounts
- **Compute Service Account:** `723493210689-compute@developer.gserviceaccount.com`
  - Used for Cloud Scheduler
  - Has permissions to execute Cloud Run jobs
  - Has read access to GCS bucket

### IAM Roles
```bash
# View service account roles
gcloud projects get-iam-policy agriguard-ac215 \
    --flatten="bindings[].members" \
    --filter="bindings.members:723493210689-compute@developer.gserviceaccount.com"
```

### API Access
- **Serving API:** Public (unauthenticated)
- **Cloud Run Jobs:** Internal only
- **GCS Bucket:** Project-level access

---

## 💰 Cost Estimates

### Monthly Costs (Approximate)

**Cloud Run Services:**
- Serving API: ~$10-20/month
  - Always-on, minimal traffic
  - 2 CPU, 4GB RAM

**Cloud Run Jobs:**
- MCSI Job: ~$2-5/month
  - Weekly execution (4-5 times/month)
  - 2 CPU, 2GB RAM, 5-10 min runtime
- Training Job: ~$1-2 per execution
  - On-demand
  - 4 CPU, 8GB RAM, 5-10 min runtime

**Cloud Scheduler:**
- ~$0.10/month (1 job)

**Cloud Storage:**
- ~$5-10/month
  - Data storage (~13 MB) + egress

**Artifact Registry:**
- ~$0.10/month (3 images, ~5 GB total)

**Total Estimated Cost:** ~$20-40/month

---

## 🐛 Troubleshooting

### API Not Responding
```bash
# Check service status
gcloud run services describe yield-prediction-api --region us-central1

# View recent logs
gcloud logging read "resource.type=cloud_run_revision" \
    --limit 20 \
    --format "table(timestamp, textPayload)"

# Test health endpoint
curl https://yield-prediction-api-uxtsuzru6a-uc.a.run.app/health
```

### Job Failing
```bash
# Check job status
gcloud run jobs describe mcsi-weekly-job --region us-central1

# View execution logs
gcloud run jobs executions describe EXECUTION_NAME --region us-central1

# Common issues:
# - Timeout: Increase --task-timeout
# - Memory: Increase --memory
# - Data access: Check service account permissions
```

### Models Not Loading
```bash
# Check if models exist in GCS
gsutil ls gs://agriguard-ac215-data/models/corn_yield_model/

# Verify serving API can access GCS
gcloud logging read "resource.labels.service_name=yield-prediction-api" \
    --limit 50 | grep -i "model"

# Retrain models
gcloud run jobs execute model-training-job --region us-central1
```

---

## 🔄 Update Procedures

### Update Code
```bash
# 1. Update code locally or in Cloud Shell
cd ~/model_serving

# 2. Edit files as needed
nano src/api_simple.py

# 3. Rebuild container
docker build -t us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-serving:latest .
docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-serving:latest

# 4. Deploy new version
gcloud run services update yield-prediction-api \
    --image us-central1-docker.pkg.dev/agriguard-ac215/agriguard/model-serving:latest \
    --region us-central1

# 5. Verify
curl https://yield-prediction-api-uxtsuzru6a-uc.a.run.app/health
```

### Update Schedule
```bash
# Update MCSI schedule (e.g., change to Tuesdays at 9 AM)
gcloud scheduler jobs update http mcsi-weekly-schedule \
    --location us-central1 \
    --schedule "0 9 * * 2"
```

### Roll Back
```bash
# List revisions
gcloud run revisions list --service yield-prediction-api --region us-central1

# Roll back to previous revision
gcloud run services update-traffic yield-prediction-api \
    --to-revisions REVISION_NAME=100 \
    --region us-central1
```

---

## 📚 Additional Resources

### Documentation
- **Data Ingestion:** `README_data_ingestion.md` - Comprehensive data documentation
- **MCSI Calculator:** `src/mcsi_calculator.py` - Stress index calculation
- **Feature Builder:** `src/feature_builder.py` - Feature engineering pipeline
- **Model Training:** `src/train_model.py` - ML model training
- **API:** `src/api_simple.py` - Simplified serving API

### Project Structure
```
mcsi-ml-deployment/
├── src/
│   ├── api_simple.py          # Serving API (LIVE)
│   ├── train_model.py         # Training pipeline
│   ├── feature_builder.py     # Feature engineering
│   └── mcsi_calculator.py     # MCSI computation
├── containers/
│   ├── mcsi_processing/       # MCSI job container
│   ├── model_training/        # Training job container
│   └── model_serving/         # API container (DEPLOYED)
├── models/                    # Local model copies
└── requirements.txt           # Python dependencies
```

### GCP Console Links
- **Cloud Run:** https://console.cloud.google.com/run?project=agriguard-ac215
- **Cloud Scheduler:** https://console.cloud.google.com/cloudscheduler?project=agriguard-ac215
- **Cloud Storage:** https://console.cloud.google.com/storage/browser/agriguard-ac215-data
- **Artifact Registry:** https://console.cloud.google.com/artifacts?project=agriguard-ac215
- **Logs:** https://console.cloud.google.com/logs?project=agriguard-ac215

### External Resources
- **USDA NASS Quick Stats:** https://quickstats.nass.usda.gov/api
- **USDA CDL:** https://nassgeodata.gmu.edu/CropScape/
- **Google Earth Engine:** https://earthengine.google.com/
- **MODIS Products:** https://lpdaac.usgs.gov/
- **OpenET:** https://openetdata.org/
- **gridMET:** https://www.climatologylab.org/gridmet.html

---

## ✅ Deployment Checklist

- [x] Data ingestion pipeline complete
- [x] Feature engineering pipeline complete
- [x] ML models trained successfully
- [x] MCSI job created and scheduled
- [x] Serving API deployed and healthy
- [x] Training job tested successfully
- [x] Cloud Scheduler configured
- [x] All containers in Artifact Registry
- [x] Service accounts configured
- [x] Health endpoint responding
- [x] Models loaded in serving API
- [x] End-to-end system tested

**🎉 ALL SYSTEMS OPERATIONAL!**

---

## 🚀 Quick Start Guide

### Test the System

```bash
# 1. Check API health
curl https://yield-prediction-api-uxtsuzru6a-uc.a.run.app/health
# Expected: {"status":"healthy","models_loaded":true}

# 2. Get model information
curl https://yield-prediction-api-uxtsuzru6a-uc.a.run.app/model/info
# Expected: {"model":"Random Forest","mae":"14.58 bu/acre"}

# 3. Run MCSI calculation
gcloud run jobs execute mcsi-weekly-job --region us-central1

# 4. Retrain models (if needed)
gcloud run jobs execute model-training-job --region us-central1
```

---

## 🎯 Key Achievements

✅ **Automated Data Pipeline:** Weekly MCSI calculations  
✅ **Production ML Model:** 14.58 MAE on 99 Iowa counties  
✅ **Scalable Architecture:** Cloud Run + GCS + Artifact Registry  
✅ **Real-time API:** Always-on yield prediction service  
✅ **Comprehensive Monitoring:** Cloud Logging + Scheduler  

---

## 📊 System Statistics

| Metric | Value |
|--------|-------|
| **Deployment Date** | November 17, 2025 |
| **Total Data Records** | 770,547 |
| **Counties Covered** | 99 (all Iowa) |
| **Years of Data** | 2016-2025 |
| **Features Engineered** | 141 |
| **Model MAE** | 14.58 bu/acre |
| **API Uptime** | ✅ Healthy |
| **Monthly Cost** | ~$20-40 |

---

## 🏆 Technical Highlights

### Data Engineering
- ✅ Corn-masked satellite indicators (CDL-based)
- ✅ Multi-source data fusion (MODIS + gridMET + OpenET)
- ✅ 770K+ records across 7 indicators
- ✅ Automated weekly updates

### Machine Learning
- ✅ Time-series cross-validation
- ✅ 141 engineered features
- ✅ Random Forest ensemble
- ✅ Production-grade serving

### DevOps & Infrastructure
- ✅ Containerized workflows (Docker)
- ✅ Cloud-native deployment (Cloud Run)
- ✅ Automated scheduling (Cloud Scheduler)
- ✅ Centralized logging (Cloud Logging)
- ✅ Version control (Artifact Registry)

---

**Deployed by:** Artem Biriukov (arb433@g.harvard.edu)  
**Date:** November 17, 2025  
**Course:** Harvard AC215_E115  
**Project:** AgriGuard - Corn Stress Monitoring & Yield Prediction  
**Version:** 1.0 - Production

---

🌽 **System Status: FULLY OPERATIONAL** 🚀

All components deployed, tested, and serving predictions!
