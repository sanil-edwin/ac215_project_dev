# AgriGuard Data Service

Complete data pipeline for corn stress monitoring: **Ingestion → Processing → Validation**.

## Overview

The `data/` folder contains all components for managing agricultural data used by AgriGuard:

- **Raw data ingestion** from NASA, USDA, and gridMET
- **Processing pipeline** for cleaning and aggregation
- **Validation framework** for data quality assurance

Current data coverage: **99 Iowa counties, 2016-2025, 770K+ records**

## Folder Structure

```
data/
├── Dockerfile                    # Container config
├── requirements.txt              # Python dependencies
├── pipeline_complete.py          # Complete 3-stage pipeline
├── validation/                   # MS5 data quality modules
│   ├── __init__.py
│   ├── schema_validator.py      # Schema validation
│   ├── quality_checker.py       # Range & completeness checks
│   └── drift_detector.py        # Distribution change detection
├── processing/                   # Data cleaning & aggregation
│   ├── Dockerfile               # (Optional) Processing-specific container
│   ├── requirements.txt          # Processing dependencies
│   ├── cleaner/
│   │   └── clean_data.py        # DataCleaner class
│   ├── features/                # Feature engineering
│   └── models/                  # ML models
└── ingestion/                    # Raw data download (reference)
    ├── downloaders/
    ├── utils/
    └── main.py
```

## Quick Start

### Run Complete Pipeline Locally

```bash
cd data
python pipeline_complete.py
```

**Result:** ~25 minutes, produces 182K daily + 27K weekly clean records ✅

### Run in Docker

**First time (build the image - one time only):**
```bash
cd data
docker build -t agriguard-data-pipeline:latest .
```

**Every subsequent run (reuse cached image):**
```bash
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/agriguard-service-account.json \
  -v /mnt/c/Users/artyb/.gcp:/secrets:ro \
  agriguard-data-pipeline:latest
```

**Save image as file for portability (optional):**
```bash
# Save to tar file
docker save agriguard-data-pipeline:latest -o agriguard-data-pipeline.tar

# Load it later on a different machine
docker load -i agriguard-data-pipeline.tar

# Then run as normal
docker run --rm ...
```

**Note:** Docker automatically caches the built image locally. You only need to rebuild if you modify `Dockerfile` or `requirements.txt`. Just run the same `docker run` command every week—no rebuild needed.

## Execution Options

### Option 1: Local Execution (Recommended for MS5)

**One-time run:**
```bash
cd data
python pipeline_complete.py
```

**Weekly schedule (Linux/Mac):**
Add to crontab:
```bash
# Run every Monday at 6am EST
0 6 * * 1 cd /path/to/agriguard/data && python pipeline_complete.py >> /var/log/agriguard-pipeline.log 2>&1
```

**Status:** ✅ **Verified working.** Container tested and passes all 3 pipeline stages.

### Option 2: Docker (Cached)

**Create convenience script:**
```bash
#!/bin/bash
# run_pipeline.sh

docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/agriguard-service-account.json \
  -v /mnt/c/Users/artyb/.gcp:/secrets:ro \
  agriguard-data-pipeline:latest
```

Then just: `./run_pipeline.sh` each week (no rebuilds).

### Option 3: Cloud Run (Optional, requires IAM setup)

```bash
# Build locally
docker build -t us-central1-docker.pkg.dev/agriguard-ac215/agriguard/agriguard-data-pipeline:latest .

# Push to Artifact Registry (requires artifactregistry.writer role)
docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard/agriguard-data-pipeline:latest

# Create Cloud Run Job
gcloud run jobs create agriguard-data-pipeline \
  --image us-central1-docker.pkg.dev/agriguard-ac215/agriguard/agriguard-data-pipeline:latest \
  --region us-central1 \
  --memory 2Gi \
  --task-timeout 3600s \
  --service-account=agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com

# Schedule weekly (Cloud Scheduler)
gcloud scheduler jobs create app-engine agriguard-data-pipeline-weekly \
  --schedule="0 6 * * 1" \
  --timezone="America/New_York" \
  --http-method=POST \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/agriguard-ac215/jobs/agriguard-data-pipeline:run" \
  --oidc-service-account-email=agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com \
  --oidc-token-audience="https://us-central1-run.googleapis.com"
```

**Note:** Requires GCP `artifactregistry.writer` IAM role. Local execution is simpler for MS5.

## Pipeline Stages

### Stage 1: Data Ingestion
**Loads raw data from authoritative sources**

- Downloads 6 environmental indicators (NDVI, LST, VPD, ETo, Precipitation, Water Deficit)
- Loads yield data from USDA NASS
- Applies USDA corn field masks (CDL)
- Stores in `gs://agriguard-ac215-data/data_raw_new/`

For detailed ingestion info: See `README.md` in appropriate subfolder

### Stage 2: Data Processing
**Cleans, merges, and aggregates data**

- Merges 6 indicators by date × county
- Creates daily aggregation (mean, std, min, max)
- Computes weekly summaries
- Generates climatology (long-term normals)
- Outputs to `gs://agriguard-ac215-data/data_clean/`

For detailed processing info: See `processing/README.md`

### Stage 3: Data Validation (MS5)
**Comprehensive quality assurance**

- **Schema validation:** Checks required columns and types
- **Quality checks:** Validates value ranges and completeness
- **Drift detection:** Monitors for unexpected data distribution changes
- **Completeness:** Ensures >95% data coverage

For detailed validation info: See `validation/README.md`

## Data Sources

| Indicator | Source | Frequency | Format | Records |
|-----------|--------|-----------|--------|---------|
| **NDVI** | NASA MODIS MOD13A1 | 16 days | Parquet | 11,187 |
| **LST** | NASA MODIS MOD11A2 | 8 days | Parquet | 22,770 |
| **VPD** | gridMET | Daily | Parquet | 181,170 |
| **ETo** | gridMET | Daily | Parquet | 182,457 |
| **Precipitation** | gridMET | Daily | Parquet | 182,358 |
| **Water Deficit** | Derived (ETo - Precip) | Daily | Parquet | 182,358 |
| **Yields** | USDA NASS | Annual | CSV | 1,416 |
| **Masks** | USDA CDL | Annual | GeoTIFF | 15 files |

**Total raw records:** 762,300+  
**Processing output:** 182K daily + 27K weekly records

## Output Data

Clean data stored in GCS as parquet files:

```
gs://agriguard-ac215-data/data_clean/
├── daily/
│   └── daily_clean_data.parquet          # 182,160 records
├── weekly/
│   └── weekly_clean_data.parquet         # 26,730 records
├── climatology/
│   └── climatology.parquet               # 2,673 records (baselines)
└── metadata/
    └── pipeline_metadata.parquet         # Processing logs
```

### Data Schema

All indicators follow consistent schema:

```
date              string    (YYYY-MM-DD)
fips              string    (5-digit county FIPS code)
county_name       string    (County name)
year              int       (Calendar year)
month             int       (Month: 1-12)
doy               int       (Day of year: 1-365)
week_of_season    int       (Week within growing season)

# For each indicator (ndvi, lst, vpd, eto, pr, water_deficit):
{indicator}_mean  float     (Mean value across county)
{indicator}_std   float     (Standard deviation)
{indicator}_min   float     (Minimum value)
{indicator}_max   float     (Maximum value)
```

## Using Data in Backend/Frontend

### Load Daily Data

```python
import pandas as pd

# Read from GCS
df = pd.read_parquet('gs://agriguard-ac215-data/data_clean/daily/daily_clean_data.parquet')

# Query specific county
adair_county = df[df['fips'] == '19001']

# Get latest data
latest = df[df['date'] == df['date'].max()]

# Get specific date range
mask = (df['date'] >= '2025-08-01') & (df['date'] <= '2025-09-30')
august_september = df[mask]
```

### Load Weekly Aggregation

```python
weekly_df = pd.read_parquet('gs://agriguard-ac215-data/data_clean/weekly/weekly_clean_data.parquet')

# Get historical baseline for comparison
climatology = pd.read_parquet('gs://agriguard-ac215-data/data_clean/climatology/climatology.parquet')
```

## Key Features

✅ **Complete Pipeline** - Ingestion → Processing → Validation in single container  
✅ **Real Data** - Uses actual MODIS, gridMET, and USDA data  
✅ **Corn-Masked** - All indicators filtered to corn fields only (USDA CDL)  
✅ **Incremental Updates** - Only processes new data since last run  
✅ **County-Level** - Aggregated to 99 Iowa counties  
✅ **Production-Ready** - Docker container verified working  
✅ **Scheduled Execution** - Local cron or Cloud Run automation  
✅ **Validated Data** - Schema, quality, and drift checks  
✅ **Complete Logging** - Detailed logs for monitoring  
✅ **No Rebuilds** - Docker image cached after first build  

## Performance

| Stage | Time | Output |
|-------|------|--------|
| Ingestion | ~10 sec | 762K records loaded |
| Processing | ~15 min | 182K daily + 27K weekly |
| Validation | <1 sec | All checks passed |
| **Total** | **~25 min** | **Ready for use** |

## Documentation

For more detailed information:

- **Dataset structure & values:** See `README_data_description.md`
- **Ingestion process:** See `ingestion/README.md` (or `ingestion/` subfolder if exists)
- **Processing pipeline:** See `processing/README.md` (or `processing/` subfolder)
- **Validation framework:** See `validation/README.md` (or `validation/` subfolder)

## Monitoring

Check pipeline status:

```bash
# View recent logs (if running on Cloud Run)
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=agriguard-data-pipeline" \
  --limit 50 \
  --format json

# Check data freshness
gsutil stat gs://agriguard-ac215-data/data_clean/daily/daily_clean_data.parquet
```

## Troubleshooting

**Pipeline fails to start:**
- Ensure GCP credentials are configured: `export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/agriguard-service-account.json`
- Check service account has GCS access
- Verify `gs://agriguard-ac215-data/` bucket exists

**Missing data in output:**
- Check raw data exists in `data_raw_new/`: `gsutil ls gs://agriguard-ac215-data/data_raw_new/`
- Verify GCS paths in `pipeline_complete.py`
- Review logs for specific errors

**Validation checks failing:**
- Check for outliers in raw data
- Verify all 99 counties have data
- See `validation/` folder for detailed checks

**Docker credential issues (WSL):**
- Use WSL paths, not Windows paths: `/mnt/c/Users/...` not `C:\Users\...`
- Mount GCP credentials: `-v /mnt/c/Users/artyb/.gcp:/secrets:ro`

**Docker slow or not caching:**
- Check if image is loaded: `docker images | grep agriguard-data-pipeline`
- If missing, rebuild: `docker build -t agriguard-data-pipeline:latest .`

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│        STAGE 1: INGESTION               │
│  Load 6 indicators from GCS (raw_new/)  │
│  • NDVI, LST, VPD, ETo, Precip, WD      │
│  ✓ 762K records loaded                  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│       STAGE 2: PROCESSING               │
│  Merge → Aggregate → Climatology        │
│  • Daily (182K) + Weekly (27K) + Clim   │
│  ✓ Clean data to GCS (clean/)           │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      STAGE 3: VALIDATION (MS5)          │
│  Schema ✓ Quality ✓ Drift ✓             │
│  ✓ ALL VALIDATIONS PASSED               │
└──────────────────┬──────────────────────┘
                   │
                   ▼
         Ready for Backend/Frontend
```

## Environment Setup

Required for execution:

```bash
# Local or Cloud Run
export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/agriguard-service-account.json
export GCS_BUCKET=agriguard-ac215-data
```

## Support

- **Data questions:** See `README_data_description.md`
- **Processing issues:** See `processing/README.md`
- **Validation errors:** See `validation/README.md`
- **Pipeline bugs:** Check logs or contact development team

---

**Status:** ✅ Production-ready (local execution verified)  
**Last Updated:** November 19, 2025  
**Coverage:** 99 Iowa counties, 2016-2025  
**Update Frequency:** Weekly (Monday 6am EST, local or Cloud Run)  
**Test Results:** All 3 pipeline stages PASS ✅  
**Docker:** Image caches locally after first build—no rebuilds needed
