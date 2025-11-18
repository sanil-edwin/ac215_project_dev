# AgriGuard MS4 API - Real Data Service

**Version:** 2.1.0-real-data  
**Status:** ✅ Production-Ready  
**Deployed:** November 17, 2025  
**Service URL:** https://agriguard-api-ms4-723493210689.us-central1.run.app

---

## 🎯 Overview

FastAPI-based backend service that provides real-time corn stress monitoring (MCSI) and yield predictions for all 99 Iowa counties. Loads **real MCSI data from Google Cloud Storage** with intelligent fallback to temporal estimates.

### Key Features

- ✅ **Real MCSI Data Loading** - Reads processed MCSI parquet files from GCS
- ✅ **Intelligent Fallback** - Uses temporal estimates when real data unavailable
- ✅ **99 Iowa Counties** - Complete coverage with FIPS-based lookups
- ✅ **ML-Powered Predictions** - Random Forest model for yield forecasting
- ✅ **RESTful API** - 5 endpoints with auto-generated docs
- ✅ **Health Monitoring** - Reports data loading status

---

## 🚀 Quick Start

### Check Health
```bash
curl https://agriguard-api-ms4-723493210689.us-central1.run.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-17T20:39:04.026997",
  "models_loaded": true,
  "data_loaded": true,
  "version": "2.1.0-real-data"
}
```

### Get MCSI for County
```bash
curl "https://agriguard-api-ms4-723493210689.us-central1.run.app/api/mcsi/19153?start_date=2025-11-10&end_date=2025-11-17" | jq
```

**Response with Real Data:**
```json
{
  "county_fips": "19153",
  "county_name": "Polk",
  "start_date": "2025-11-10",
  "end_date": "2025-11-17",
  "mcsi_score": 0.68,
  "stress_level": "Low",
  "color": "#4CAF50",
  "components": {
    "water_stress": 1.51,
    "heat_stress": 0.0,
    "vegetation_stress": 0.0
  },
  "growth_stage": "maturity",
  "data_source": "Real MCSI from GCS"
}
```

---

## 📡 API Endpoints

### 1. Health Check
**GET** `/health`

Returns service health and data loading status.

**Response:**
- `status`: "healthy" or "unhealthy"
- `models_loaded`: Boolean - ML models loaded
- `data_loaded`: Boolean - MCSI data from GCS loaded
- `version`: API version string

### 2. List Counties
**GET** `/api/counties`

Returns all 99 Iowa counties with FIPS codes.

**Response:**
```json
{
  "counties": [
    {"fips": "19001", "name": "Adair"},
    {"fips": "19003", "name": "Adams"},
    ...
  ],
  "total": 99
}
```

### 3. Get MCSI (Multi-Factor Corn Stress Index)
**GET** `/api/mcsi/{fips}`

Calculate MCSI for a specific county and date range.

**Parameters:**
- `fips` (path): 5-digit county FIPS code (e.g., "19153")
- `start_date` (query, optional): Start date YYYY-MM-DD (default: 14 days ago)
- `end_date` (query, optional): End date YYYY-MM-DD (default: today)

**Response:**
- `mcsi_score`: Float (0-100) - Overall stress index
- `stress_level`: "Low", "Moderate", "High", or "Severe"
- `color`: Hex color code for visualization
- `components`: Water, heat, and vegetation stress percentages
- `growth_stage`: Corn phenology stage
- `data_source`: "Real MCSI from GCS" or "Temporal Estimate"

**Stress Level Thresholds:**
- **Low:** 0-30 (Green)
- **Moderate:** 30-50 (Yellow)
- **High:** 50-70 (Orange)
- **Severe:** 70+ (Red)

### 4. Predict Yield
**GET** `/api/predict/{fips}`

Predict corn yield using ML model.

**Parameters:**
- `fips` (path): 5-digit county FIPS code
- `year` (query, optional): Year to predict (default: 2025)

**Response:**
```json
{
  "county_fips": "19153",
  "county_name": "Polk",
  "year": 2025,
  "predicted_yield": 177.6,
  "confidence": "Medium",
  "trend": "average",
  "model": "Random Forest (MAE: 14.58)"
}
```

### 5. Historical Data
**GET** `/api/historical/{fips}`

Get historical MCSI data for charting.

**Parameters:**
- `fips` (path): County FIPS code
- `year` (query, optional): Year (default: 2024)

**Response:**
```json
{
  "county_fips": "19153",
  "county_name": "Polk",
  "data": [
    {
      "date": "2024-05-07",
      "mcsi_score": 15.48,
      "stress_level": "Low"
    },
    ...
  ]
}
```

### 6. Stress Map
**GET** `/api/stress/map`

Get current stress levels for all counties (map visualization).

**Parameters:**
- `date` (query, optional): Date YYYY-MM-DD (default: today)

**Response:**
```json
{
  "date": "2025-11-17",
  "counties": [
    {
      "fips": "19001",
      "name": "Adair",
      "mcsi_score": 0.63,
      "stress_level": "Low",
      "color": "green"
    },
    ...
  ]
}
```

---

## 🗄️ Data Sources

### Primary: Real MCSI from GCS

**Location:** `gs://agriguard-ac215-data/processed/mcsi/`

**Format:** Parquet files with schema:
```python
{
  'county_fips': str,       # "19153"
  'county_name': str,       # "Polk"
  'start_date': datetime,   # 2025-11-10
  'end_date': datetime,     # 2025-11-17
  'mcsi_score': float,      # 0.68
  'stress_level': str,      # "Low"
  'color': str,             # "green"
  'components': dict,       # {heat_stress, water_stress, vegetation_stress}
  'growth_stage': str,      # "off_season"
  'calculation_date': datetime
}
```

**Generated By:** `mcsi-weekly-job` Cloud Run Job  
**Update Frequency:** Weekly (Monday 8 AM Central)

### Fallback: Temporal Estimates

When real data is unavailable for a date range, the API generates realistic estimates based on:
- **Month** - Seasonal stress patterns (May low, July-Aug high)
- **Year** - Historical variations (2022 drought, 2023 wetter)
- **County** - Consistent per-county characteristics

**Temporal Pattern:**
- **May-June:** Low stress (15-40)
- **July-August:** High stress (35-70) - Critical period
- **September-October:** Declining stress (20-45)
- **November-April:** Off-season (minimal stress)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   Cloud Run Service (FastAPI)       │
│   - 2 CPU, 4GB RAM                  │
│   - Auto-scaling 0-10 instances     │
│   - Public access (unauthenticated) │
└────────┬────────────────────────────┘
         │
         ↓ Load at startup
┌─────────────────────────────────────┐
│   GCS Bucket                         │
│   gs://agriguard-ac215-data/        │
│   └── processed/mcsi/*.parquet      │
└────────┬────────────────────────────┘
         │
         ↓ Generated weekly
┌─────────────────────────────────────┐
│   MCSI Processor Job                │
│   - Processes 99 counties           │
│   - Takes ~2 minutes                │
│   - Scheduled: Mon 8 AM CT          │
└─────────────────────────────────────┘
```

---

## 🛠️ Deployment

### Prerequisites
- Docker installed
- Google Cloud SDK (`gcloud`)
- Service account: `agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com`

### Build and Deploy

```bash
cd backend-api

# Build container
docker build -t us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-ms4:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-ms4:latest

# Deploy to Cloud Run
gcloud run deploy agriguard-api-ms4 \
  --image=us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-ms4:latest \
  --region=us-central1 \
  --service-account=agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --cpu=2 \
  --memory=4Gi \
  --timeout=300 \
  --max-instances=10
```

### Environment Variables
None required - all configuration is in code.

### IAM Permissions Required
Service account needs:
- `storage.objects.get` - Read MCSI data from GCS
- `storage.objects.list` - List available MCSI files

---

## 📦 Dependencies

**Key Libraries:**
- `fastapi==0.104.1` - Web framework
- `uvicorn==0.24.0` - ASGI server
- `pandas==2.1.3` - Data processing
- `pyarrow==14.0.1` - **CRITICAL** - Parquet file reading
- `google-cloud-storage==2.10.0` - GCS access
- `scikit-learn==1.3.2` - ML models
- `joblib==1.3.2` - Model serialization

**Full requirements.txt:**
```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pandas==2.1.3
numpy==1.26.2
scikit-learn==1.3.2
joblib==1.3.2
google-cloud-storage==2.10.0
pyarrow==14.0.1
```

---

## 🔧 Configuration

### MCSI Calculation Formula

```python
MCSI = (water_stress × 0.45) + (heat_stress × 0.35) + (vegetation_stress × 0.20)
```

**Growth Stage Multipliers:**
- Emergence (May): 1.0
- Vegetative (June): 1.2
- Pollination (July 15-Aug 15): 1.5 (CRITICAL)
- Grain Fill (Aug-Sept): 1.3
- Maturity (Sept-Oct): 1.0
- Off-season: 1.0

### Iowa Counties

All 99 Iowa counties supported with FIPS codes 19001-19197:
- Adair (19001) through Wright (19197)
- Complete FIPS mapping in code

---

## 🐛 Troubleshooting

### Issue: `data_loaded: false`

**Symptom:** Health check shows models loaded but no data  
**Cause:** MCSI files not in GCS or loading error  
**Solution:**
```bash
# Check if files exist
gsutil ls gs://agriguard-ac215-data/processed/mcsi/

# Generate new data
gcloud run jobs execute mcsi-weekly-job --region us-central1

# Check logs for errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=agriguard-api-ms4" --limit 50
```

### Issue: "Temporal Estimate" instead of real data

**Symptom:** `data_source: "Temporal Estimate"` in response  
**Cause:** No data available for requested date range  
**Solution:**
1. Check what dates exist: `gsutil cat gs://agriguard-ac215-data/processed/mcsi/mcsi_*.parquet | head`
2. Request dates that have data
3. Or run MCSI job to generate data for desired dates

### Issue: Startup takes >10 seconds

**Cause:** Loading large parquet files  
**Solution:** Normal behavior. First cold start loads data. Subsequent requests are fast.

### Issue: Import errors for pyarrow

**Cause:** Missing pyarrow in requirements.txt  
**Solution:** 
```bash
echo "pyarrow==14.0.1" >> requirements.txt
# Rebuild and redeploy
```

---

## 📊 Performance

### Response Times
- Health check: ~50ms
- MCSI calculation: ~200-500ms (with real data)
- MCSI calculation: ~100ms (temporal estimate)
- Yield prediction: ~150ms
- Historical data: ~300-600ms

### Startup Time
- Cold start: 8-12 seconds (loads parquet files)
- Warm start: <1 second

### Data Loading
- Parquet file size: ~12 KB per week (99 counties)
- Loading time: ~2-3 seconds at startup
- Memory usage: ~100 MB for data + models

---

## 🧪 Testing

### Manual Testing

```bash
# Test all endpoints
./test_api.sh

# Or individually:
curl https://agriguard-api-ms4-723493210689.us-central1.run.app/health
curl https://agriguard-api-ms4-723493210689.us-central1.run.app/api/counties
curl https://agriguard-api-ms4-723493210689.us-central1.run.app/api/mcsi/19153
curl https://agriguard-api-ms4-723493210689.us-central1.run.app/api/predict/19153?year=2025
curl https://agriguard-api-ms4-723493210689.us-central1.run.app/api/historical/19153?year=2024
```

### Check Logs

```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=agriguard-api-ms4" --limit 100 --format json

# Search for errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=agriguard-api-ms4 AND severity>=ERROR" --limit 20
```

---

## 📝 Code Structure

```
backend-api/
├── api_extended.py           # Main API file (600+ lines)
│   ├── Data Models (Pydantic)
│   ├── GCS Loading Functions
│   ├── MCSI Calculation
│   ├── Startup (loads data)
│   └── API Endpoints
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container definition
└── models/                  # ML models
    ├── rf_model.pkl         # Random Forest model
    ├── feature_names.json   # 150 feature names
    └── model_config.json    # Model metadata
```

### Key Functions

**`load_mcsi_from_gcs()`**
- Called at startup
- Lists all parquet files in GCS
- Loads the most recent file
- Returns pandas DataFrame or None

**`get_mcsi_for_period(df, fips, start_date, end_date)`**
- Filters data by county and date range
- Extracts stress components from dict
- Returns aggregated MCSI values

**`calculate_mcsi_simple(county_fips, start_date, end_date)`**
- First tries to get real data
- Falls back to temporal estimates
- Returns formatted MCSI response
- Includes `data_source` field

---

## 🔄 Data Pipeline

### Weekly MCSI Generation

```mermaid
graph LR
    A[Cloud Scheduler] -->|Mon 8 AM| B[MCSI Job]
    B -->|Load| C[Raw Data GCS]
    C -->|Process| D[Calculate MCSI]
    D -->|Save| E[Parquet to GCS]
    E -->|Auto-reload| F[API Service]
```

**Manual Trigger:**
```bash
gcloud run jobs execute mcsi-weekly-job --region us-central1
```

**Monitor:**
```bash
gcloud run jobs executions list --region us-central1 --job mcsi-weekly-job
```

---

## 🔐 Security

### Authentication
- **Current:** Unauthenticated (public API)
- **Production:** Should add API key or OAuth

### Data Access
- Service account has minimal permissions
- Read-only access to GCS bucket
- No write permissions to production data

### CORS
- Enabled for all origins (frontend needs this)
- Configure specific origins in production

---

## 📈 Monitoring

### Key Metrics to Watch

1. **Data Loading Status**
   - Check `/health` endpoint
   - `data_loaded` should be `true`

2. **Response Times**
   - Monitor Cloud Run metrics
   - Alert if >1 second average

3. **Error Rates**
   - Check logs for exceptions
   - Alert on ERROR severity

4. **Cold Starts**
   - Monitor startup latency
   - Consider min-instances=1 for production

### Dashboards

**Cloud Run Console:**
https://console.cloud.google.com/run/detail/us-central1/agriguard-api-ms4

**Logs Explorer:**
https://console.cloud.google.com/logs/query?project=agriguard-ac215

---

## 🎓 Development Notes

### Recent Changes (Nov 17, 2025)

1. ✅ Added pyarrow dependency for parquet reading
2. ✅ Fixed column name mismatch (county_fips vs fips)
3. ✅ Added load_mcsi_from_gcs() call in startup
4. ✅ Fixed component extraction from dict structure
5. ✅ Removed duplicate function definitions
6. ✅ Added data_source field to responses

### Known Limitations

1. **Date Range Dependency**
   - Only has data for dates that MCSI job processed
   - November data is off-season (low stress)
   - Need May-October data for meaningful charts

2. **Historical Data**
   - Currently generates estimates for historical queries
   - Real historical data requires processing past dates

3. **Real-time Updates**
   - Data refreshed weekly, not real-time
   - Cold starts reload data (8-12 seconds)

---

## 🔗 Related Services

**Frontend:**
- URL: https://agriguard-frontend-ms4-723493210689.us-central1.run.app
- Repository: `frontend-app/`
- Framework: Next.js

**MCSI Processor:**
- Job: `mcsi-weekly-job`
- Schedule: Monday 8 AM CT
- Duration: ~2 minutes

**Existing Production API:**
- URL: https://yield-prediction-api-uxtsuzru6a-uc.a.run.app
- Purpose: Original ML serving API
- Status: Active, used for comparison

---

## 📞 Support

**Developer:** Arty (arb433@g.harvard.edu)  
**Course:** AC215 - Harvard Extension School  
**Project:** AgriGuard - MS4 Milestone  
**Due Date:** November 25, 2025

**Documentation:**
- API Docs (Swagger): https://agriguard-api-ms4-723493210689.us-central1.run.app/docs
- Frontend: Deployed and operational
- Handover Doc: `HANDOVER_MS4_REAL_DATA.md`

---

## ✅ Success Criteria

**Service is working correctly when:**

1. Health check returns:
   ```json
   {
     "models_loaded": true,
     "data_loaded": true,
     "version": "2.1.0-real-data"
   }
   ```

2. MCSI responses include:
   ```json
   {
     "data_source": "Real MCSI from GCS",
     "mcsi_score": 0.68  // Real value from parquet
   }
   ```

3. Startup logs show:
   ```
   INFO:api_extended:✓ Loaded 99 MCSI records from GCS
   ```

4. All 99 Iowa counties return data

5. Historical endpoint generates realistic temporal trends

---

**Last Updated:** November 17, 2025, 8:45 PM EST  
**Status:** ✅ Production-Ready with Real Data  
**Deployment:** Revision agriguard-api-ms4-00011-9n4
