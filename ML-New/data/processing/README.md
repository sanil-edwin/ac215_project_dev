# Data Processing Pipeline

Transforms raw satellite and weather data (770K+ records) into clean, aggregated datasets for the AgriGuard corn stress monitoring system.

## What It Does

1. **Loads** 7 indicators (NDVI, LST, ET, VPD, ETo, Precipitation, Water Deficit)
2. **Merges** by date + county (FIPS code)
3. **Aggregates** daily (mean, std, min, max)
4. **Summarizes** weekly
5. **Computes** climatology (baselines)
6. **Saves** clean data to GCS

**Processing window:** May 1 - October 31 (corn growing season only)  
**Input:** 770K raw records  
**Output:** 182K daily + 27K weekly clean records

## Structure
```
processing/
├── Dockerfile                  # Cloud Run container
├── __init__.py                 # Package init
├── config.py                   # GCS paths & settings
├── requirements.txt            # Dependencies
└── cleaner/
    ├── __init__.py
    └── clean_data.py          # DataCleaner class
```

## Quick Start

### Local
```bash
source venv/bin/activate
pip install -r requirements.txt
python -m cleaner.clean_data
```

### Docker
```bash
docker build -t agriguard-data-processor:latest .
docker run --rm \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/agriguard-service-account.json \
  -v /path/to/.gcp:/secrets \
  agriguard-data-processor:latest
```

### Cloud Run
```bash
gcloud run deploy agriguard-data-processor \
  --source . \
  --memory 4Gi \
  --timeout 3600 \
  --service-account agriguard-service-account@agriguard-ac215.iam.gserviceaccount.com
```

## Configuration

Edit `config.py` to change:
- GCS bucket names
- Input/output paths
- Aggregation methods

## Input Data

Raw parquet files in `gs://agriguard-ac215-data/data_raw_new/`:
- MODIS: NDVI, LST, ET
- Weather: VPD, ETo, Precipitation, Water Deficit

## Output Data

Clean datasets in `gs://agriguard-ac215-data/data_clean/`:
- `daily/` - 182K daily aggregates
- `weekly/` - 27K weekly summaries
- `climatology/` - Historical baselines
- `metadata/` - Processing logs

## DataCleaner Class
```python
from cleaner import DataCleaner

cleaner = DataCleaner()
cleaner.run()
```

Methods:
- `run()` - Execute full pipeline
- `create_daily_clean_data()` - Merge indicators
- `create_weekly_clean_data()` - Weekly summaries
- `create_climatology()` - Compute baselines
- `create_metadata()` - Generate logs

## Using Clean Data in Backend
```python
from data.processing.config import GCS_CLEAN_PATH
import pandas as pd

# Load clean data
df = pd.read_parquet(f"{GCS_CLEAN_PATH}/daily/iowa_corn_daily_20160501_20251031.parquet")

# Query by county
adair = df[df['fips'] == '19001']
```

## Troubleshooting

**Missing GCS files:**
```bash
gsutil ls gs://agriguard-ac215-data/data_clean/
```

**Permission denied:**
```bash
gcloud auth application-default login
```

**Module not found:**
Make sure you're at project root:
```bash
# ✅ Correct
cd /path/to/AgriGuard
python -m data.processing.cleaner.clean_data

# ❌ Wrong
cd data/processing
python -m cleaner.clean_data
```

---

**Status:** ✅ Production ready - processes 770K→182K clean records
