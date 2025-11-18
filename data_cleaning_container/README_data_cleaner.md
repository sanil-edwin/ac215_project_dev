# AgriGuard Data Cleaning Container

**Transform raw satellite and weather data into clean, ML-ready datasets.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Input Data](#input-data)
- [Output Data](#output-data)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Data Validation](#data-validation)
- [Pipeline Architecture](#pipeline-architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Performance](#performance)
- [Support](#support)

---

## Overview

This containerized pipeline consolidates raw AgriGuard satellite and weather data into unified, temporally-aligned datasets optimized for Crop Stress Index (CSI) computation and machine learning model training.

### What it Does

✅ **Temporal Alignment** - Merges NDVI (16-day), LST (8-day), and daily weather data into unified daily/weekly tables  
✅ **Gap Filling** - Forward-fills NDVI up to 16 days with age tracking  
✅ **Quality Control** - Removes outliers and adds quality flags per indicator  
✅ **Derived Metrics** - Computes days since rain, seasonal cumulative precipitation  
✅ **Water Stress Integration** - Incorporates pre-computed water deficit (ETo - Precipitation)  
✅ **Climatology** - Generates historical normals for stress index calculations  
✅ **Growth Phases** - Auto-labels corn growth stages (emergence, pollination, grain fill)

### Key Stats

| Metric | Value |
|--------|-------|
| **Runtime** | 30-60 minutes |
| **Schedule** | Weekly (Mondays, 3:00 AM CT) |
| **Input Size** | ~15 MB (raw parquet files) |
| **Output Size** | ~461 MB (clean datasets) |
| **Coverage** | 99 Iowa counties, 2016-2025 |
| **Records** | 1.78M daily, 25.7K weekly |

---

## Input Data

**Source:** `gs://agriguard-ac215-data/data_raw_new/`

```
data_raw_new/
├── modis/
│   ├── ndvi/
│   │   └── iowa_corn_ndvi_20160501_20251031.parquet     (11,187 records)
│   └── lst/
│       └── iowa_corn_lst_20160501_20251031.parquet      (22,770 records)
└── weather/
    ├── vpd/
    │   └── iowa_corn_vpd_20160501_20251031.parquet      (181,170 records)
    ├── eto/
    │   └── iowa_corn_eto_20160501_20251031.parquet      (182,457 records)
    ├── pr/
    │   └── iowa_corn_pr_20160501_20251031.parquet       (182,358 records)
    └── water_deficit/
        └── iowa_corn_water_deficit_20160501_20251031.parquet  (182,358 records)
```

**Coverage:**
- **Spatial:** All 99 Iowa counties
- **Temporal:** 2016-05-01 to 2025-11-12 (growing seasons + early November 2025)
- **Corn-Masked:** USDA CDL corn classification (year-specific masks 2016-2024)
- **Total Input Records:** 762,300 across 6 indicator files
- **Note:** November 2025 data (12 days) included for most recent conditions

---

## Output Data

**Destination:** `gs://agriguard-ac215-data/data_clean/`

### File Structure

```
data_clean/
├── daily/
│   └── iowa_corn_daily_20160501_20251031.parquet         (~450 MB, 1.78M rows)
│
├── weekly/
│   └── iowa_corn_weekly_20160501_20251031.parquet        (~8 MB, 25.7K rows)
│
├── climatology/
│   └── daily_normals_2016_2024.parquet                   (~3 MB, 18K rows)
│
└── metadata/
    └── data_quality_report.json                          (~2 KB)
```

### Daily Clean Data Schema

**File:** `daily/iowa_corn_daily_20160501_20251031.parquet`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `date` | datetime | Observation date | `2024-08-10` |
| `fips` | str | County FIPS code | `19001` |
| `county_name` | str | County name | `Adair` |
| `year` | int | Year | `2024` |
| `doy` | int | Day of year | `223` |
| `week_of_season` | int | Week number (1 = May 1-7) | `15` |
| `growth_phase` | str | Corn growth stage | `grain_fill` |
| **NDVI (Vegetation Health)** | | | |
| `ndvi_mean` | float | Mean NDVI (0-1) | `0.72` |
| `ndvi_std` | float | Standard deviation | `0.08` |
| `ndvi_source_date` | datetime | MODIS composite date | `2024-08-01` |
| `ndvi_age_days` | int | Days since last update | `9` |
| `ndvi_quality` | str | Quality flag | `good` |
| **LST (Land Surface Temperature)** | | | |
| `lst_mean` | float | Mean LST (°C) | `31.5` |
| `lst_std` | float | Standard deviation | `2.1` |
| `lst_quality` | str | Quality flag | `good` |
| **VPD (Vapor Pressure Deficit)** | | | |
| `vpd_mean` | float | Mean VPD (kPa) | `0.0023` |
| `vpd_std` | float | Standard deviation | `0.0005` |
| `vpd_quality` | str | Quality flag | `good` |
| **ETo (Evapotranspiration)** | | | |
| `eto_mean` | float | Mean ETo (mm/day) | `5.8` |
| `eto_std` | float | Standard deviation | `0.3` |
| `eto_quality` | str | Quality flag | `good` |
| **Precipitation** | | | |
| `pr_mean` | float | Mean precip (mm/day) | `2.1` |
| `pr_std` | float | Standard deviation | `0.4` |
| `pr_quality` | str | Quality flag | `good` |
| **Water Deficit (Pre-computed)** | | | |
| `water_deficit` | float | ETo - Precip (mm/day) | `3.7` |
| `water_deficit_quality` | str | Quality flag | `good` |
| **Derived Metrics** | | | |
| `days_since_rain` | int | Consecutive dry days | `3` |
| `cumulative_precip_season` | float | Total mm since May 1 | `245.3` |

**Quality Flags:**
- `good` - Fresh data, high confidence
- `fair` - Moderate age (NDVI 10-20 days old)
- `poor` - Stale data (NDVI >20 days old)
- `missing` - No data available

---

### Weekly Clean Data Schema

**File:** `weekly/iowa_corn_weekly_20160501_20251031.parquet`

| Column | Type | Description |
|--------|------|-------------|
| `week_start` | datetime | Monday of week |
| `fips` | str | County FIPS code |
| `county_name` | str | County name |
| `year` | int | Year |
| `week_of_season` | int | Week number |
| `growth_phase` | str | Dominant phase in week |
| `ndvi_mean` | float | Weekly mean NDVI |
| `ndvi_freshness` | str | `fresh` or `stale` |
| `lst_mean` | float | Weekly mean LST (°C) |
| `lst_max` | float | Hottest day in week (°C) |
| `lst_days_above_32C` | int | Heat stress days |
| `vpd_mean` | float | Weekly mean VPD (kPa) |
| `vpd_max` | float | Peak VPD in week |
| `eto_mean` | float | Weekly mean ETo (mm/day) |
| `eto_sum` | float | Total weekly ETo (mm) |
| `pr_sum` | float | Total weekly rainfall (mm) |
| `pr_days` | int | Days with >1mm rain |
| `water_deficit_mean` | float | Mean daily deficit |
| `water_deficit_sum` | float | Total weekly deficit (mm) |
| `completeness` | float | Fraction of valid days (0-1) |
| `quality_score` | str | Overall quality |

---

### Climatology Schema

**File:** `climatology/daily_normals_2016_2024.parquet`

Historical statistics by county × day-of-year for z-score calculations:

| Column | Description |
|--------|-------------|
| `fips` | County FIPS code |
| `doy` | Day of year (122-304) |
| `ndvi_climatology_median` | Historical median NDVI |
| `ndvi_climatology_std` | Standard deviation |
| `ndvi_climatology_p10` | 10th percentile (bad year) |
| `ndvi_climatology_p90` | 90th percentile (good year) |
| `lst_climatology_median` | Historical median LST |
| `lst_climatology_p90` | Heat stress threshold |
| `vpd_climatology_median` | Historical median VPD |
| `eto_climatology_median` | Historical median ETo |
| `pr_climatology_median` | Historical median precipitation |
| `water_deficit_climatology_median` | Historical median water deficit |
| `water_deficit_climatology_p90` | High stress threshold |

---

### Metadata Schema

**File:** `metadata/data_quality_report.json`

```json
{
  "last_updated": "2025-11-15T14:32:18.123456",
  "date_range": {
    "start": "2016-05-01",
    "end": "2025-10-31"
  },
  "daily_records": 1782000,
  "weekly_records": 25740,
  "counties": 99,
  "data_quality": {
    "ndvi": {
      "completeness": 87.3,
      "avg_age_days": 8.2
    },
    "lst": {"completeness": 94.1},
    "vpd": {"completeness": 99.8},
    "eto": {"completeness": 99.7},
    "pr": {"completeness": 99.9},
    "water_deficit": {"completeness": 99.9}
  },
  "processing_stats": {
    "runtime_seconds": 2847,
    "memory_peak_mb": 6234
  }
}
```

---

## Quick Start

### Prerequisites

- Google Cloud SDK installed and configured
- Docker installed
- Access to `agriguard-ac215` GCP project
- Service account with Storage permissions

### One-Time Setup

```bash
# 1. Authenticate with GCP
gcloud auth login
gcloud config set project agriguard-ac215

# 2. Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# 3. Verify service account exists
gcloud iam service-accounts describe \
  agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com
```

---

## Deployment

### Build Image

```bash
cd data_cleaning_container/

# Build Docker image
docker build -t data-cleaner:latest .

# Tag for Artifact Registry
docker tag data-cleaner:latest \
  us-central1-docker.pkg.dev/agriguard-ac215/agriguard-containers/data-cleaner:latest

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard-containers/data-cleaner:latest
```

### Create Cloud Run Job

```bash
gcloud run jobs create agriguard-data-cleaner \
  --image=us-central1-docker.pkg.dev/agriguard-ac215/agriguard-containers/data-cleaner:latest \
  --region=us-central1 \
  --memory=8Gi \
  --cpu=4 \
  --max-retries=2 \
  --task-timeout=2h \
  --service-account=agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com
```

### Update Existing Job

```bash
gcloud run jobs update agriguard-data-cleaner \
  --image=us-central1-docker.pkg.dev/agriguard-ac215/agriguard-containers/data-cleaner:latest \
  --region=us-central1
```

### Execute Job

**Manual execution:**
```bash
gcloud run jobs execute agriguard-data-cleaner --region=us-central1
```

**Schedule weekly runs:**
```bash
gcloud scheduler jobs create http agriguard-clean-data-weekly \
  --location=us-central1 \
  --schedule="0 3 * * 1" \
  --time-zone="America/Chicago" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/agriguard-ac215/jobs/agriguard-data-cleaner:run" \
  --http-method=POST \
  --oauth-service-account-email=agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com
```

---

## Monitoring

### List Executions

```bash
# List recent executions
gcloud run jobs executions list \
  --job=agriguard-data-cleaner \
  --region=us-central1 \
  --limit=10

# Get execution details
gcloud run jobs executions describe <EXECUTION_NAME> \
  --region=us-central1
```

### View Logs

**Stream logs in real-time:**
```bash
gcloud logging tail \
  "resource.type=cloud_run_job AND resource.labels.job_name=agriguard-data-cleaner"
```

**Query specific errors:**
```bash
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=agriguard-data-cleaner AND severity>=ERROR" \
  --limit=50 \
  --format=json
```

**Cloud Console:**
```
https://console.cloud.google.com/run/jobs/details/us-central1/agriguard-data-cleaner?project=agriguard-ac215
```

---

## Data Validation

### Verify Output Files

```bash
# Check all output files exist
gsutil ls -lh gs://agriguard-ac215-data/data_clean/daily/
gsutil ls -lh gs://agriguard-ac215-data/data_clean/weekly/
gsutil ls -lh gs://agriguard-ac215-data/data_clean/climatology/
gsutil ls -lh gs://agriguard-ac215-data/data_clean/metadata/
```

### Inspect Daily Data

```bash
# Download daily data
gsutil cp gs://agriguard-ac215-data/data_clean/daily/iowa_corn_daily_20160501_20251031.parquet .

# Inspect with Python
python3 << 'EOF'
import pandas as pd

df = pd.read_parquet('iowa_corn_daily_20160501_20251031.parquet')

print("=" * 60)
print("DAILY CLEAN DATA SUMMARY")
print("=" * 60)
print(f"\nShape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Counties: {df['fips'].nunique()}")
print(f"Years: {sorted(df['year'].unique())}")

print("\n" + "=" * 60)
print("DATA QUALITY")
print("=" * 60)
print(f"\nNDVI Quality:")
print(df['ndvi_quality'].value_counts())
print(f"\nNDVI Age (days):")
print(df[df['ndvi_age_days'] >= 0]['ndvi_age_days'].describe())

print("\n" + "=" * 60)
print("SAMPLE ROWS")
print("=" * 60)
print(df[['date', 'fips', 'county_name', 'ndvi_mean', 'lst_mean', 
          'water_deficit', 'growth_phase']].head(5))

print("\n" + "=" * 60)
print("MISSING DATA")
print("=" * 60)
print(df.isnull().sum()[df.isnull().sum() > 0])
EOF
```

### Check Metadata

```bash
gsutil cat gs://agriguard-ac215-data/data_clean/metadata/data_quality_report.json | jq .
```

Expected output:
```json
{
  "last_updated": "2024-11-15T...",
  "daily_records": 1782000,
  "weekly_records": 25740,
  "counties": 99,
  "data_quality": {
    "ndvi": {"completeness": 87.3},
    "lst": {"completeness": 94.1},
    "vpd": {"completeness": 99.8}
  }
}
```

---

## Pipeline Architecture

```
┌────────────────────────────────────────────────────────────┐
│  INPUT: Raw Data (data_raw_new/)                          │
│  ├─ NDVI: 16-day composites (11K records)                 │
│  ├─ LST: 8-day composites (22K records)                   │
│  ├─ Weather: Daily VPD, ETo, Precip (181K records each)   │
│  └─ Water Deficit: Daily ETo-Precip (181K records)        │
└──────────────────┬─────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────┐
│  PROCESSING: Data Cleaner (Cloud Run Job)                 │
│                                                            │
│  Step 1: Temporal Alignment                               │
│    → Create complete date × county grid                   │
│    → Merge all indicators to same dates                   │
│                                                            │
│  Step 2: Gap Filling                                      │
│    → Forward-fill NDVI up to 16 days                      │
│    → Track source date and age                            │
│                                                            │
│  Step 3: Outlier Removal                                  │
│    → Clip to 0.1th-99.9th percentiles                     │
│                                                            │
│  Step 4: Derived Metrics                                  │
│    → days_since_rain (consecutive dry days)               │
│    → cumulative_precip_season (total mm since May 1)      │
│                                                            │
│  Step 5: Quality Flags                                    │
│    → Assess data freshness and completeness               │
│                                                            │
│  Step 6: Growth Phase Labeling                            │
│    → Auto-assign based on date                            │
│                                                            │
│  Step 7: Weekly Aggregation                               │
│    → Compute weekly means, sums, maxes                    │
│    → Heat stress days, rainfall events                    │
│                                                            │
│  Step 8: Climatology                                      │
│    → Compute historical normals (2016-2024)               │
│    → By county × day-of-year                              │
│                                                            │
└──────────────────┬─────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────┐
│  OUTPUT: Clean Data (data_clean/)                         │
│  ├─ Daily: 1.78M rows, all indicators aligned             │
│  ├─ Weekly: 25.7K rows, phase aggregates                  │
│  ├─ Climatology: 18K rows, historical normals             │
│  └─ Metadata: Quality report (JSON)                       │
└────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

None required. Uses Application Default Credentials from service account.

### Service Account Permissions

`agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com` requires:

| Permission | Scope | Reason |
|------------|-------|--------|
| `storage.objects.get` | `data_raw_new/` | Read raw data |
| `storage.objects.list` | `data_raw_new/` | List input files |
| `storage.objects.create` | `data_clean/` | Write clean data |
| `storage.objects.delete` | `data_clean/` | Overwrite existing files |

### Resource Limits

| Resource | Default | Adjustable | Max |
|----------|---------|------------|-----|
| Memory | 8 GB | Yes | 32 GB |
| CPU | 4 cores | Yes | 8 cores |
| Timeout | 2 hours | Yes | 24 hours |
| Max Retries | 2 | Yes | 10 |

**Adjust resources:**
```bash
gcloud run jobs update agriguard-data-cleaner \
  --memory=16Gi \
  --cpu=8 \
  --task-timeout=3h \
  --region=us-central1
```

---

### Data Quality Insights

**Water Deficit Distribution (Actual 2016-2025):**

Based on validation of actual data (November 2025):
- **Surplus (< 0 mm/day):** 19.9% of records - Precipitation exceeds evapotranspiration
- **Normal (0-2 mm/day):** 9.5% - Adequate soil moisture
- **Moderate Stress (2-4 mm/day):** 23.4% - Beginning water stress
- **High Stress (4-6 mm/day):** 35.7% - Significant water deficit ⚠️
- **Severe Stress (>6 mm/day):** 11.6% - Critical water shortage

**Key Observation:** The high percentage of "High Stress" records (35.7%) indicates that **2025 has experienced significant drought conditions** compared to historical averages. This distribution reflects actual water stress patterns across Iowa corn fields from 2016-2025.

**Data Completeness:**
- Water Deficit: 100.0% complete
- All 99 counties: Full coverage
- Date continuity: No gaps in daily records

---

## Troubleshooting

### Job Fails with "Out of Memory"

**Symptom:** Job crashes during processing

**Solution:**
```bash
gcloud run jobs update agriguard-data-cleaner \
  --memory=16Gi \
  --region=us-central1
```

---

### Job Times Out

**Symptom:** Job killed after 2 hours

**Solution:**
```bash
gcloud run jobs update agriguard-data-cleaner \
  --task-timeout=3h \
  --region=us-central1
```

---

### Missing Input Data

**Symptom:** Error loading raw parquet files

**Check input files exist:**
```bash
gsutil ls gs://agriguard-ac215-data/data_raw_new/modis/ndvi/
gsutil ls gs://agriguard-ac215-data/data_raw_new/modis/lst/
gsutil ls gs://agriguard-ac215-data/data_raw_new/weather/vpd/
gsutil ls gs://agriguard-ac215-data/data_raw_new/weather/eto/
gsutil ls gs://agriguard-ac215-data/data_raw_new/weather/pr/
gsutil ls gs://agriguard-ac215-data/data_raw_new/weather/water_deficit/
```

**Solution:** Run data ingestion jobs first

---

### Permission Denied Errors

**Symptom:** `403 Forbidden` when accessing GCS

**Check service account permissions:**
```bash
gcloud projects get-iam-policy agriguard-ac215 \
  --flatten="bindings[].members" \
  --filter="bindings.members:agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com"
```

**Solution:** Grant Storage Object Admin role:
```bash
gcloud projects add-iam-policy-binding agriguard-ac215 \
  --member="serviceAccount:agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

### Output Data Quality Issues

**Check logs for warnings:**
```bash
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=agriguard-data-cleaner AND severity>=WARNING" \
  --limit=100
```

**Inspect metadata:**
```bash
gsutil cat gs://agriguard-ac215-data/data_clean/metadata/data_quality_report.json | jq .data_quality
```

---

## Development

### Local Testing

```bash
# Set up authentication
gcloud auth application-default login

# Run container locally
docker run --rm \
  -v ~/.config/gcloud:/root/.config/gcloud \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  data-cleaner:latest
```

### Code Structure

```
data_cleaning_container/
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── src/
    └── clean_data.py          # Main cleaning pipeline
        ├── DataCleaner        # Main class
        │   ├── run()          # Entry point
        │   ├── create_daily_clean_data()
        │   ├── create_weekly_clean_data()
        │   ├── create_climatology()
        │   ├── create_metadata()
        │   ├── _load_water_deficit()
        │   ├── _fill_ndvi_gaps()
        │   ├── _remove_outliers()
        │   ├── _add_quality_flags()
        │   └── _add_growth_phase()
        └── main()             # Script entry point
```

### Adding New Indicators

1. **Load raw data** in `create_daily_clean_data()`:
   ```python
   # Example: Loading water_deficit (already implemented)
   water_deficit = pd.read_parquet(
       f'{self.raw_path}/weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet'
   )
   ```

2. **Merge with main dataframe**:
   ```python
   df = df.merge(
       water_deficit[['date', 'fips', 'water_deficit']], 
       on=['date', 'fips'], 
       how='left'
   )
   ```

3. **Add quality flags** in `_add_quality_flags()`:
   ```python
   df['water_deficit_quality'] = 'good'
   df.loc[df['water_deficit'].isna(), 'water_deficit_quality'] = 'missing'
   ```

4. **Update climatology** in `create_climatology()`:
   ```python
   climatology = clim_df.groupby(['fips', 'doy']).agg({
       'water_deficit': ['median', 'std', lambda x: x.quantile(0.1), lambda x: x.quantile(0.9)]
   })
   ```

5. **Update weekly aggregation** in `create_weekly_clean_data()`:
   ```python
   agg_dict['water_deficit_mean'] = ('water_deficit', 'mean')
   agg_dict['water_deficit_sum'] = ('water_deficit', 'sum')
   ```

### Running Tests

```bash
# Unit tests (TODO: add test suite)
pytest tests/

# Integration test (requires GCP access)
python src/clean_data.py
```

---

## Performance

### Benchmark

| Metric | Value | Notes |
|--------|-------|-------|
| **Runtime** | 30-60 min | Varies by data volume |
| **Memory Peak** | ~6 GB | Out of 8 GB allocated |
| **CPU Utilization** | 60-80% | 4 cores |
| **Input Size** | ~15 MB | Compressed parquet |
| **Output Size** | ~461 MB | Uncompressed parquet |
| **GCS Read** | ~50 MB | Including retries |
| **GCS Write** | ~461 MB | Clean data |
| **Cost per Run** | ~$0.12 | Cloud Run charges |

### Optimization Tips

1. **Reduce memory usage:**
   - Process data in chunks
   - Drop unnecessary columns early
   - Use categorical dtypes for strings

2. **Speed up processing:**
   - Increase CPU to 8 cores
   - Use vectorized pandas operations
   - Parallelize county-level operations

3. **Lower costs:**
   - Use spot instances (preemptible)
   - Compress output files
   - Schedule during off-peak hours

---

## Support

### Resources

- **Documentation:** [AgriGuard Data Ingestion README](../README_data_ingestion.md)
- **Project Repository:** https://github.com/your-org/agriguard
- **Issues:** https://github.com/your-org/agriguard/issues
- **GCP Console:** https://console.cloud.google.com/run/jobs?project=agriguard-ac215

### Contact

**Project Lead:** Artem Biriukov  
**Email:** arb433@g.harvard.edu  
**Course:** AC215_E115 - Harvard University  
**Project:** AgriGuard - Automated Corn Stress Monitoring

### Changelog

#### v1.1.1 (2025-11-16)
- Updated record counts to match actual data (November 2025 included)
- ETo: 182,457 records (was 181,170)
- Precipitation: 182,358 records (was 181,071)
- Water Deficit: 182,358 records (was 181,071)
- Total: 762,300 records (was 758,269)
- Note: Includes 12 days of November 2025 data (1,188 records) for current season monitoring

#### v1.1 (2025-11-15)
- Added water_deficit as input indicator (pre-computed from data ingestion)
- Updated pipeline to load water_deficit from raw data instead of computing
- Added water_deficit to climatology calculations
- Enhanced quality control with water_deficit quality flags
- Updated documentation to reflect 6 input indicators

#### v1.0 (2024-11-15)
- Initial release
- Daily and weekly clean data generation
- Climatology computation
- Quality flags and metadata
- Automated gap filling for NDVI

---

## License

MIT License - See LICENSE file for details

---

**Last Updated:** November 16, 2025  
**Version:** 1.1.1  
**Container Image:** `us-central1-docker.pkg.dev/agriguard-ac215/agriguard-containers/data-cleaner:latest`  
**Maintained by:** AgriGuard Team
