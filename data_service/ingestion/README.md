# AgriGuard Data Ingestion Pipeline

Production-ready container for downloading and processing agricultural data for Iowa corn stress monitoring.

## Overview

Pulls corn-masked satellite indicators, weather data, and yield records from authoritative sources (NASA, USDA, gridMET). Processes incrementally—only downloads new data since last run. All data processed through county-level aggregation and stored in GCS as parquet files. For detailed data description please see README_data_description.md.

## Data Sources

| Indicator | Source | Frequency | Coverage |
|-----------|--------|-----------|----------|
| **NDVI** | NASA MODIS MOD13A1 | 16 days | 2016-2025 |
| **LST** | NASA MODIS MOD11A2 | 8 days | 2016-2025 |
| **VPD** | gridMET | Daily | 2016-2025 |
| **ETo** | gridMET | Daily | 2016-2025 |
| **Precip** | gridMET | Daily | 2016-2025 |
| **Water Deficit** | Derived (ETo - Precip) | Daily | 2016-2025 |
| **Yield** | USDA NASS | Annual | 2010-2025 |
| **Masks** | USDA CDL | Annual | 2010-2025 |

## Quick Start

### Local Testing

```bash
# Build
docker build -t agriguard-ingestion:latest .

# Test with GCP credentials
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/key.json \
  -v ~/.gcp:/secrets \
  agriguard-ingestion:latest \
  python main.py --download ndvi

# Test yield with API key
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/key.json \
  -e NASS_API_KEY='your_api_key' \
  -v ~/.gcp:/secrets \
  agriguard-ingestion:latest \
  python main.py --download yield
```

### All Downloads

```bash
# Download all indicators
python main.py --download all

# Or individually
python main.py --download mask
python main.py --download yield
python main.py --download ndvi
python main.py --download lst
python main.py --download vpd
python main.py --download eto
python main.py --download precip
```

## Deployment

### 1. Build & Push to GCP

```bash
docker build -t gcr.io/agriguard-ac215/agriguard-ingestion:latest .
docker push gcr.io/agriguard-ac215/agriguard-ingestion:latest
```

### 2. Create Cloud Run Jobs

**Daily jobs (May-Oct during growing season):**
```bash
# NDVI
gcloud run jobs create agriguard-ndvi-corn-job \
  --image=gcr.io/agriguard-ac215/agriguard-ingestion:latest \
  --args="python,main.py,--download,ndvi" \
  --timeout=28800 \
  --memory=4Gi \
  --cpu=2 \
  --region=us-central1 \
  --project=agriguard-ac215

# LST
gcloud run jobs create agriguard-lst-corn-job \
  --image=gcr.io/agriguard-ac215/agriguard-ingestion:latest \
  --args="python,main.py,--download,lst" \
  --timeout=28800 \
  --memory=4Gi \
  --cpu=2 \
  --region=us-central1 \
  --project=agriguard-ac215

# VPD
gcloud run jobs create agriguard-vpd-corn-job \
  --image=gcr.io/agriguard-ac215/agriguard-ingestion:latest \
  --args="python,main.py,--download,vpd" \
  --timeout=28800 \
  --memory=4Gi \
  --cpu=2 \
  --region=us-central1 \
  --project=agriguard-ac215

# ETo
gcloud run jobs create agriguard-eto-corn-job \
  --image=gcr.io/agriguard-ac215/agriguard-ingestion:latest \
  --args="python,main.py,--download,eto" \
  --timeout=28800 \
  --memory=4Gi \
  --cpu=2 \
  --region=us-central1 \
  --project=agriguard-ac215

# Precip + Water Deficit
gcloud run jobs create agriguard-precip-corn-job \
  --image=gcr.io/agriguard-ac215/agriguard-ingestion:latest \
  --args="python,main.py,--download,precip" \
  --timeout=28800 \
  --memory=4Gi \
  --cpu=2 \
  --region=us-central1 \
  --project=agriguard-ac215
```

**Reference data jobs (occasional):**
```bash
# Masks (monthly or as-needed)
gcloud run jobs create agriguard-mask-job \
  --image=gcr.io/agriguard-ac215/agriguard-ingestion:latest \
  --args="python,main.py,--download,mask" \
  --timeout=3600 \
  --memory=2Gi \
  --region=us-central1 \
  --project=agriguard-ac215

# Yields (annual, after harvest)
gcloud run jobs create agriguard-yield-job \
  --image=gcr.io/agriguard-ac215/agriguard-ingestion:latest \
  --args="python,main.py,--download,yield" \
  --timeout=1800 \
  --memory=1Gi \
  --set-env-vars=NASS_API_KEY='your_api_key' \
  --region=us-central1 \
  --project=agriguard-ac215
```

### 3. Schedule Jobs (Cloud Scheduler)

```bash
# NDVI: every 3 days during growing season
gcloud scheduler jobs create app-engine agriguard-ndvi-schedule \
  --schedule="0 2 */3 5-10 *" \
  --timezone=America/Chicago \
  --http-method=POST \
  --uri=https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/agriguard-ac215/jobs/agriguard-ndvi-corn-job:run \
  --location=us-central1 \
  --project=agriguard-ac215 \
  --oidc-service-account-email=agriguard-ac215@iam.gserviceaccount.com
```

## Data Flow

```
Cloud Scheduler Trigger
    ↓
Cloud Run Job
    ↓
Container: main.py --download [indicator]
    ↓
Load downloader module
    ↓
Check existing data in GCS
    ↓
Find last update date
    ↓
Download only NEW data (incremental)
    ↓
Apply corn masks (year-specific CDL)
    ↓
Aggregate to county level
    ↓
Merge with existing data
    ↓
Upload to gs://agriguard-ac215-data/data_raw_new/
    ↓
✓ Complete
```

## Key Features

✅ **Incremental Updates** - Only downloads missing data, no duplicates  
✅ **Corn-Masked** - All indicators filtered to corn fields using USDA CDL  
✅ **County Aggregation** - Mean, std, min, max statistics per county  
✅ **Season-Filtered** - May-October only (corn growing season)  
✅ **Idempotent** - Safe to re-run without side effects  
✅ **Error Handling** - Graceful failures, detailed logging  
✅ **Production-Ready** - No hardcoded credentials, proper IAM setup  

## Output Format

**Parquet files** in `gs://agriguard-ac215-data/data_raw_new/`:

```
├── modis/
│   ├── ndvi/iowa_corn_ndvi_20160501_20251031.parquet
│   └── lst/iowa_corn_lst_20160501_20251031.parquet
└── weather/
    ├── vpd/iowa_corn_vpd_20160501_20251031.parquet
    ├── eto/iowa_corn_eto_20160501_20251031.parquet
    ├── pr/iowa_corn_pr_20160501_20251031.parquet
    └── water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet
```

**Schema (all indicators):**
```
date          string    (YYYY-MM-DD)
fips          string    (5-digit county code)
county_name   string
mean          float     (indicator value)
std           float     (standard deviation)
min           float     (minimum)
max           float     (maximum)
mask_year     int       (CDL mask version used)
```

## Environment Variables

Required for Cloud Run:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/var/secrets/google/key.json  # Auto-set by Cloud Run
NASS_API_KEY='your_api_key'  # For yield downloader (optional, required for 2025+ data)
```

Get NASS API key: https://quickstats.nass.usda.gov/api

## Development

### Add New Data Source

1. Create `downloaders/new_source.py` with `main()` function
2. Import in `main.py`
3. Add case in `main()` switch statement
4. Test locally: `docker run ... python main.py --download new_source`

### File Structure

```
ingestion/
├── Dockerfile
├── requirements.txt
├── main.py              # Entry point
├── downloaders/         # Individual data source modules
│   ├── ndvi.py
│   ├── lst.py
│   ├── vpd.py
│   ├── eto.py
│   ├── precip.py
│   ├── mask.py
│   └── yield_.py
└── utils/               # Helper functions
```

## Performance

| Indicator | Typical Runtime | Data Points | Update Lag |
|-----------|-----------------|-------------|-----------|
| NDVI | 15-20 min | 11K records | 3-5 days |
| LST | 15-20 min | 23K records | 3-5 days |
| VPD | 10-15 min | 181K records | 1-2 days |
| ETo | 10-15 min | 181K records | 1-2 days |
| Precip | 10-15 min | 181K records | 1-2 days |
| Masks | 5-10 min | Reference | Varies |
| Yield | 2-3 min | 1.4K records | Annual |

## Troubleshooting

**Empty date range error:**
- Check that last date < today
- Fixed in eto.py, precip.py (uses dynamic end_date)

**401 Unauthorized (NASS):**
- Yield downloader needs API key
- Get key: https://quickstats.nass.usda.gov/api
- Set: `NASS_API_KEY=your_key`

**Permission denied (masks):**
- Service account needs `earthengine.exports.create` permission
- Not critical—all existing masks available

**No new data:**
- Check GCS path exists
- Verify last update date is reasonable
- Job will exit gracefully with `✓ Already up to date!`

## Monitoring

Check job status:
```bash
gcloud run jobs logs agriguard-ndvi-corn-job \
  --limit=100 \
  --project=agriguard-ac215
```

Execute job manually:
```bash
gcloud run jobs execute agriguard-ndvi-corn-job \
  --wait \
  --project=agriguard-ac215
```

## Credits

Data sources:
- NASA MODIS: https://modis.gsfc.nasa.gov/
- USDA NASS: https://quickstats.nass.usda.gov/
- gridMET: https://www.climatologylab.org/gridmet.html
- USDA CDL: https://nassgeodata.gmu.edu/CropScape/

Pipeline maintained by AgriGuard team.
