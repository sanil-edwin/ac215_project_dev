# AgriGuard - Data Preprocessing Container

Compute historical baselines and detect anomalies from MODIS satellite data for Iowa corn crop monitoring.

## Overview

This container performs two key preprocessing steps:

1. **Baseline Computation** - Calculate historical norms (2017-2023) for each county, indicator, and day of year
2. **Anomaly Detection** - Compute Z-scores and classify stress severity

## Quick Start

### Build Container

```bash
cd preprocessing
docker build -t agriguard-preprocessing .
```

### Run Full Pipeline

```bash
# Default: Process year 2024
docker run --rm \
  -v $(pwd)/secrets:/secrets:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json \
  -e GCS_BUCKET_NAME=agriguard-ac215-data \
  -e GCP_PROJECT_ID=agriguard-ac215 \
  -e YEAR=2024 \
  agriguard-preprocessing
```

### PowerShell (Windows)

```powershell
docker run --rm `
  -v ${PWD}/secrets:/secrets:ro `
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json `
  -e GCS_BUCKET_NAME=agriguard-ac215-data `
  -e GCP_PROJECT_ID=agriguard-ac215 `
  -e YEAR=2024 `
  agriguard-preprocessing
```

### Interactive Shell (Recommended for Development)

For easier development and debugging, use the provided shell scripts:

**Linux/Mac:**
```bash
./docker-shell.sh
```

**Windows PowerShell:**
```powershell
.\docker-shell.ps1
```

The shell script will:
- Check for required credentials
- Build the image if needed
- Mount source code for live editing
- Start an interactive bash session

Inside the shell, you can run individual scripts:
```bash
python src/preprocessing/compute_baselines.py
python src/preprocessing/compute_anomalies.py
python src/preprocessing/quick_inspect.py
```

### Run Individual Steps (Without Shell)

```bash
# Compute baselines only
docker run --rm \
  -v $(pwd)/secrets:/secrets:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json \
  -e GCS_BUCKET_NAME=agriguard-ac215-data \
  agriguard-preprocessing \
  python src/preprocessing/compute_baselines.py

# Compute anomalies for specific year
docker run --rm \
  -v $(pwd)/secrets:/secrets:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json \
  -e GCS_BUCKET_NAME=agriguard-ac215-data \
  -e YEAR=2023 \
  agriguard-preprocessing \
  python src/preprocessing/compute_anomalies.py

# Inspect outputs
docker run --rm \
  -v $(pwd)/secrets:/secrets:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json \
  -e GCS_BUCKET_NAME=agriguard-ac215-data \
  agriguard-preprocessing \
  python src/preprocessing/quick_inspect.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GCS_BUCKET_NAME` | GCS bucket for data storage | `agriguard-ac215-data` |
| `GCP_PROJECT_ID` | Google Cloud project ID | `agriguard-ac215` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key | `/secrets/gcp-key.json` |
| `YEAR` | Target year for anomaly detection | `2024` |
| `START_YEAR` | Baseline period start | `2017` |
| `END_YEAR` | Baseline period end | `2023` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Feature Configuration

Edit `config/feature_config.yaml` to customize:
- Growth stage definitions (day of year ranges)
- Anomaly thresholds (z-score cutoffs)
- Persistence windows (7, 14, 21, 30 days)
- Rolling window sizes

## Pipeline Details

### Step 1: Baseline Computation

**Script:** `compute_baselines.py`

**Input:** Historical MODIS data (2017-2023)
```
gs://agriguard-ac215-data/processed/modis/{product}/*.parquet
```

**Output:** Baseline statistics
```
gs://agriguard-ac215-data/processed/baselines/
├── ndvi_baseline_daily.parquet      # Per day-of-year
├── ndvi_baseline_stages.parquet     # Per growth stage
├── et_baseline_daily.parquet
├── et_baseline_stages.parquet
├── lst_baseline_daily.parquet
└── lst_baseline_stages.parquet
```

**What it computes:**
- Mean, std, median, 25th/75th percentiles
- Aggregated by: county × product × band × day-of-year
- Also by: county × product × band × growth-stage

**Example output:**
```
fips  product  band  doy  baseline_mean  baseline_std  growth_stage
19001 ndvi     NDVI  180  0.72          0.08          vegetative
19001 et       ET    180  4.2           0.6           vegetative
19001 lst      LST   180  28.5          2.3           vegetative
```

### Step 2: Anomaly Detection

**Script:** `compute_anomalies.py`

**Input:** 
- Current year MODIS data (e.g., 2024)
- Baseline statistics from Step 1

**Output:** Anomaly classifications
```
gs://agriguard-ac215-data/processed/anomalies/
├── ndvi_anomalies_2024.parquet
├── et_anomalies_2024.parquet
└── lst_anomalies_2024.parquet
```

**What it computes:**

For each observation:
- **Z-score:** `(value - baseline_mean) / baseline_std`
- **Percentile:** Approximate historical rank (0-100)
- **Anomaly flag:** `normal | mild | moderate | severe`
- **Persistence:** Consecutive anomalous days (7d, 14d, 21d, 30d windows)
- **Rolling features:** Moving averages of values and z-scores

**Anomaly Thresholds:**
```
Normal:   -1.5 ≤ z-score ≤ 1.5
Mild:     -2.5 ≤ z-score < -1.5  or  1.5 < z-score ≤ 2.5
Moderate: -3.5 ≤ z-score < -2.5  or  2.5 < z-score ≤ 3.5
Severe:   z-score < -3.5  or  z-score > 3.5
```

**Example output:**
```
fips  date       band  mean  z_score  anomaly_flag  days_persistent_14d
19001 2024-07-15 NDVI  0.55  -2.1     mild         7
19001 2024-07-22 NDVI  0.48  -3.0     moderate     14
19001 2024-07-29 NDVI  0.45  -3.4     severe       21
```

## Output Examples (2025 Run)

### Baseline Data Summary

**Daily Baselines:**
- **Records:** 4,554 (covering 99 Iowa counties)
- **Columns:** 12 (fips, county_name, product, band, doy, baseline statistics, growth_stage)
- **Date Range:** Day of year 1-365
- **Products:** NDVI (EVI, NDVI bands)

**Sample Daily Baseline Records:**

| fips  | county_name | product | band | doy | baseline_mean | baseline_std | growth_stage |
|-------|-------------|---------|------|-----|---------------|--------------|--------------|
| 19001 | Adair       | ndvi    | EVI  | 129 | 0.314         | 0.019        | planting     |
| 19001 | Adair       | ndvi    | EVI  | 145 | 0.364         | 0.021        | planting     |
| 19001 | Adair       | ndvi    | NDVI | 180 | 0.729         | 0.088        | vegetative   |
| 19021 | Buena Vista | ndvi    | EVI  | 241 | 0.578         | 0.071        | maturity     |
| 19027 | Carroll     | ndvi    | EVI  | 337 | 0.124         | 0.063        | unknown      |

**Growth Stage Baselines:**
- **Records:** 990
- **Aggregation:** By growth stage (planting, vegetative, reproductive, maturity)

| fips  | county_name | band | growth_stage | baseline_mean | baseline_std | n_observations |
|-------|-------------|------|--------------|---------------|--------------|----------------|
| 19001 | Adair       | EVI  | planting     | 0.339         | 0.032        | 14             |
| 19001 | Adair       | EVI  | vegetative   | 0.540         | 0.080        | 21             |
| 19001 | Adair       | EVI  | reproductive | 0.610         | 0.045        | 14             |
| 19001 | Adair       | EVI  | maturity     | 0.425         | 0.109        | 21             |
| 19001 | Adair       | NDVI | vegetative   | 0.729         | 0.088        | 21             |

### Anomaly Data Summary (2025)

**Dataset Overview:**
- **Total Observations:** 3,366
- **Date Range:** January 1 - September 14, 2025
- **Counties Covered:** 99 Iowa counties
- **Bands:** EVI, NDVI
- **Features:** 36 columns (includes z-scores, persistence, rolling averages)

**Anomaly Distribution:**

| Category | Count | Percentage |
|----------|-------|------------|
| Normal   | 2,253 | 66.9%      |
| Severe   | 1,113 | 33.1%      |

**Z-Score Statistics:**

| Metric | Value  |
|--------|--------|
| Mean   | 0.98   |
| Std    | 1.45   |
| Min    | -6.42  |
| 25%    | 0.25   |
| Median | 0.84   |
| 75%    | 1.68   |
| Max    | 16.68  |

**Sample Anomaly Records:**

| fips  | county_name | date       | band | mean  | z_score | anomaly_flag | days_persistent_14d |
|-------|-------------|------------|------|-------|---------|--------------|---------------------|
| 19001 | Adair       | 2025-01-17 | EVI  | 0.130 | 1.55    | severe       | 1                   |
| 19001 | Adair       | 2025-07-12 | EVI  | 0.740 | 3.11    | severe       | 1                   |
| 19001 | Adair       | 2025-07-28 | EVI  | 0.787 | 3.57    | severe       | 1                   |
| 19001 | Adair       | 2025-08-13 | EVI  | 0.728 | 3.04    | severe       | 1                   |
| 19001 | Adair       | 2025-09-14 | EVI  | 0.278 | -1.91   | severe       | 1                   |

**Top 10 Counties by Stress Days:**

| Rank | County     | Stress Days |
|------|------------|-------------|
| 1    | Kossuth    | 18          |
| 2    | Jefferson  | 17          |
| 3    | Marion     | 17          |
| 4    | Howard     | 16          |
| 5    | Washington | 16          |
| 6    | Poweshiek  | 16          |
| 7    | Emmet      | 15          |
| 8    | Clay       | 15          |
| 9    | Davis      | 15          |
| 10   | Tama       | 15          |

### Key Insights

1. **Seasonal Patterns:** Clear progression from planting (May) through vegetative (June-July) to reproductive (July-August) stages
2. **Stress Events:** Multiple severe stress events detected during critical reproductive period (July-August)
3. **Regional Variation:** Northern Iowa counties (Kossuth, Emmet, Howard) show higher stress frequency
4. **Extreme Anomalies:** Z-scores ranging from -6.42 to +16.68 indicate significant departures from historical norms

## Data Schema

### Baselines (`*_baseline_daily.parquet`)

| Column | Type | Description |
|--------|------|-------------|
| `fips` | str | County FIPS code |
| `product` | str | `ndvi`, `et`, or `lst` |
| `band` | str | `NDVI`, `EVI`, `ET`, `PET`, `LST_Day`, `LST_Night` |
| `doy` | int | Day of year (1-365) |
| `growth_stage` | str | `planting`, `vegetative`, `reproductive`, `maturity`, `unknown` |
| `baseline_mean` | float | Historical average |
| `baseline_std` | float | Historical standard deviation |
| `baseline_median` | float | Historical median |
| `baseline_p25` | float | 25th percentile |
| `baseline_p75` | float | 75th percentile |
| `n_years` | int | Number of years in baseline |

### Anomalies (`*_anomalies_{year}.parquet`)

| Column | Type | Description |
|--------|------|-------------|
| `fips` | str | County FIPS code |
| `county_name` | str | County name |
| `date` | datetime | Observation date |
| `doy` | int | Day of year |
| `product` | str | Product name |
| `band` | str | Band name |
| `growth_stage` | str | Growth stage |
| `mean` | float | Indicator value |
| `std` | float | Standard deviation of pixels |
| `min` | float | Minimum value |
| `max` | float | Maximum value |
| `median` | float | Median value |
| `p25` | float | 25th percentile |
| `p75` | float | 75th percentile |
| `pixel_count` | int | Number of pixels aggregated |
| `baseline_mean` | float | Expected value |
| `baseline_std` | float | Expected variability |
| `baseline_median` | float | Expected median |
| `baseline_p25` | float | Expected 25th percentile |
| `baseline_p75` | float | Expected 75th percentile |
| `z_score` | float | Standardized anomaly |
| `percentile` | float | Historical rank (0-100) |
| `anomaly_flag` | str | `normal`, `mild`, `moderate`, `severe` |
| `days_persistent_7d` | int | Consecutive anomalous days (7-day window) |
| `days_persistent_14d` | int | Consecutive anomalous days (14-day window) |
| `days_persistent_21d` | int | Consecutive anomalous days (21-day window) |
| `days_persistent_30d` | int | Consecutive anomalous days (30-day window) |
| `rolling_mean_7d` | float | 7-day moving average |
| `rolling_zscore_7d` | float | 7-day moving average of z-scores |
| `rolling_std_7d` | float | 7-day rolling standard deviation |
| `rolling_mean_14d` | float | 14-day moving average |
| `rolling_zscore_14d` | float | 14-day moving average of z-scores |
| `rolling_std_14d` | float | 14-day rolling standard deviation |
| `rolling_mean_30d` | float | 30-day moving average |
| `rolling_zscore_30d` | float | 30-day moving average of z-scores |
| `rolling_std_30d` | float | 30-day rolling standard deviation |

## Development

### Interactive Development Shell

The easiest way to develop and test changes is using the interactive shell:

**Linux/Mac:**
```bash
chmod +x docker-shell.sh  # First time only
./docker-shell.sh
```

**Windows PowerShell:**
```powershell
# If execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then run the shell:
powershell -ExecutionPolicy Bypass -File .\docker-shell.ps1
```

**What the shell script does:**
- ✅ Validates credentials exist (`secrets/gcp-key.json`)
- ✅ Builds Docker image if not already built
- ✅ Mounts `src/`, `config/`, and `logs/` directories for live code editing
- ✅ Sets up all required environment variables
- ✅ Starts interactive bash session in the container

**Inside the shell you can:**
```bash
# Run individual scripts
python src/preprocessing/compute_baselines.py
python src/preprocessing/compute_anomalies.py
python src/preprocessing/quick_inspect.py

# Test Python imports
python -c "from utils.gcs_utils import get_gcs_manager; print('✓ Imports working')"

# Debug with Python REPL
python
>>> from utils.gcs_utils import get_gcs_manager
>>> gcs = get_gcs_manager()
>>> gcs.list_blobs('processed/baselines/')

# Exit the shell
exit
```

**Customize environment:**
```bash
# Linux/Mac
export YEAR=2024
./docker-shell.sh

# Windows PowerShell
$env:YEAR = "2024"
.\docker-shell.ps1
```

### Install Dependencies (Local)

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### Run Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff src/
```

## Troubleshooting

### Issue: Baselines not found

**Solution:** Run baseline computation first:
```bash
docker run ... agriguard-preprocessing python src/preprocessing/compute_baselines.py
```

### Issue: Insufficient historical data

**Error:** `ValueError: No data found for product: ndvi`

**Solution:** Ensure Container 1 (data-ingestion) has downloaded data for 2017-2023

### Issue: Memory errors

**Solution:** Reduce batch size or increase Docker memory:
```bash
docker run --memory=8g ... agriguard-preprocessing
```

## Performance

**Typical Runtime:**
- Baseline Computation: 10-20 minutes (processes 7 years of data)
- Anomaly Detection: 5-10 minutes (processes 1 year)
- Total Pipeline: 15-30 minutes

**Resource Requirements:**
- Memory: 4-8 GB recommended
- Storage: ~500 MB for outputs per year
- CPU: 2+ cores recommended

## Next Steps

After preprocessing, anomaly data is ready for:

1. **Container 3:** Stress Detection (rule-based + ML)
2. **Container 4:** Yield Forecasting models

Anomaly data includes all necessary features:
- Z-scores and anomaly classifications
- Persistence metrics (7d, 14d, 21d, 30d)
- Rolling averages and trends
- Growth stage information

## References

- Configuration: `config/feature_config.yaml`
- GCS Utils: `src/utils/gcs_utils.py`
- Main Pipeline: `src/preprocessing/run_preprocessing.py`
- Data Inspection: `src/preprocessing/quick_inspect.py`

## Authors

AgriGuard Team - Harvard AC215 Fall 2025
- Binh Vu
- Sanil Edwin
- Moody Farra
- Artem Biriukov
