# AgriGuard Data Ingestion Pipeline

Automated pipeline for downloading and processing Iowa corn agricultural data to Google Cloud Storage.

## 📊 Data Overview

The pipeline collects three types of data for comprehensive corn yield prediction and stress monitoring:

### 1. **Corn Yields** (USDA NASS Quick Stats API)

County-level corn yield data from 2017-present.

**Sample data:**
```csv
year,state,state_fips,county,county_fips,yield_bu_per_acre,unit,fips
2017,IOWA,19,ADAIR,1,175.2,BU / ACRE,19001
2017,IOWA,19,ADAMS,3,179.9,BU / ACRE,19003
2017,IOWA,19,ALLAMAKEE,5,190.5,BU / ACRE,19005
```

**Specifications:**
- **Coverage:** 99 Iowa counties
- **Years:** 2017-2025
- **Location:** `gs://agriguard-ac215-data/raw/yields/`
- **Format:** CSV (one file per year + combined file)
- **File:** `iowa_corn_yields_2017_2025.csv`

**Loading data:**
```bash
# View from command line
gsutil cat gs://agriguard-ac215-data/raw/yields/iowa_corn_yields_2017_2025.csv | head

# Load in Python
import pandas as pd
yields = pd.read_csv("gs://agriguard-ac215-data/raw/yields/iowa_corn_yields_2017_2025.csv")
```

---

### 2. **Corn Masks** (USDA NASS Cropland Data Layer)

Binary raster masks identifying corn-growing areas derived from the USDA NASS Cropland Data Layer (CDL).

**File Details:**
- **Filename:** `iowa_corn_mask_{year}.tif`
- **Example:** `gs://agriguard-ac215-data/raw/masks/corn/iowa_corn_mask_2024.tif`
- **Format:** GeoTIFF (single-band, 8-bit unsigned integer)
- **Resolution:** 30 meters (resampled from CDL)
- **Coordinate System:** Same as source CDL (typically Albers Equal Area)
- **Compression:** LZW (lossless)

**Pixel Values:**
```
0 = Not corn (other crops, forest, urban, water, etc.)
1 = Corn (classified as corn in USDA CDL for that year)
```

**Technical Specifications:**
```python
# Raster properties
Data Type: uint8 (0-255, but only 0 and 1 used)
No Data Value: None (all pixels have valid values)
Extent: Iowa state boundary
Typical File Size: 50-100 MB per year
```

**Coverage Statistics (typical):**
- Total pixels: ~100-150 million (varies by year)
- Corn pixels: ~15-25% of Iowa land area
- Spatial extent: Clipped to Iowa state boundaries
- Years available: 2017-2024

**Data Source:**
- **Original:** USDA NASS Cropland Data Layer (CDL)
- **URL:** https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php
- **Method:** CDL raster filtered to corn classification (code = 1), clipped to Iowa

**Use Cases:**
- Masking satellite data to corn-only pixels
- Calculating corn acreage per county
- Analyzing corn distribution patterns
- Training/validation masks for ML models
- Time series analysis of corn extent changes

**Viewing the Data:**

Using GDAL:
```bash
# Get raster info
gdalinfo gs://agriguard-ac215-data/raw/masks/corn/iowa_corn_mask_2024.tif

# Get statistics
gdalinfo -stats gs://agriguard-ac215-data/raw/masks/corn/iowa_corn_mask_2024.tif
```

**Quality Considerations:**
- CDL has ~85-95% accuracy for corn classification
- Some edge pixels may have mixed classification
- Urban/water areas correctly classified as non-corn (0)
- Annual variations reflect actual crop rotation and planting decisions

---

### 3. **Satellite Indicators** (Google Earth Engine - MODIS)

County-aggregated MODIS time series data for corn stress monitoring.

**Products Available:**

| Product  | Bands              | Source        | Temporal Resolution | Spatial Resolution | Description               |
|----------|--------------------|---------------|---------------------|--------------------|---------------------------|
| **NDVI** | NDVI, EVI          | MOD13A1.061   | 16-day composite    | 500m               | Vegetation health indices |
| **ET**   | ET, PET            | MOD16A2GF.061 | 8-day composite     | 500m               | Water stress indicators   |
| **LST**  | LST_Day, LST_Night | MOD11A2.061   | 8-day composite     | 1km                | Heat stress (°C)          |

**File Format:** Parquet (columnar storage, optimized for analytics)

#### Sample Data - Vegetation Health (NDVI):

    fips county_name       date  band product      mean       std     min     max  pixel_count    median       p25       p75
0  19053     Decatur 2017-05-09  NDVI    ndvi  0.681497  0.126000  0.2853  0.8977         5722  0.681497  0.597077  0.765918
1  19053     Decatur 2017-05-09   EVI    ndvi  0.484431  0.109341  0.1539  0.8057         5722  0.484431  0.411173  0.557690
2  19031       Cedar 2017-05-09  NDVI    ndvi  0.396318  0.136402  0.2039  0.8691         6264  0.396318  0.304928  0.487707
3  19031       Cedar 2017-05-09   EVI    ndvi  0.272284  0.107198  0.1182  0.7403         6264  0.272284  0.200462  0.344107
4  19027     Carroll 2017-05-09  NDVI    ndvi  0.337460  0.095135  0.2254  0.7828         6117  0.337460  0.273720  0.401200

#### Sample Data - Water Stress (ET):

    fips county_name       date band product       mean       std   min   max  pixel_count     median        p25        p75
0  19053     Decatur 2017-05-01   ET      et  14.947265  3.860354   8.3  36.6         5709  14.947265  12.360828  17.533702
1  19053     Decatur 2017-05-01  PET      et  39.848542  0.590951  38.1  43.0         5709  39.848542  39.452605  40.244479
2  19031       Cedar 2017-05-01   ET      et  12.186661  0.980995  10.8  25.9         6257  12.186661  11.529395  12.843928
3  19031       Cedar 2017-05-01  PET      et  35.479568  0.809251  33.1  39.3         6257  35.479568  34.937370  36.021767
4  19027     Carroll 2017-05-01   ET      et   9.308282  0.904438   8.0  19.5         6104   9.308282   8.702309   9.914256

#### Sample Data - Heat Stress (LST):

    fips county_name       date       band product       mean       std    min    max  pixel_count     median        p25        p75
0  19053     Decatur 2017-05-01    LST_Day     lst  23.992050  0.668204  20.95  26.07         1487  23.992050  23.544353  24.439747
1  19053     Decatur 2017-05-01  LST_Night     lst   6.760741  1.016170   4.23  10.71         1487   6.760741   6.079907   7.441575
2  19031       Cedar 2017-05-01    LST_Day     lst  24.734119  2.931866  11.15  30.21         1604  24.734119  22.769768  26.698469
3  19031       Cedar 2017-05-01  LST_Night     lst   5.306836  0.972889   2.43   8.35         1615   5.306836   4.655000   5.958672
4  19027     Carroll 2017-05-01    LST_Day     lst  29.266813  1.415663  22.51  32.65         1565  29.266813  28.318319  30.215308
5  19027     Carroll 2017-05-01  LST_Night     lst   5.869135  1.058621   2.71   8.83         1565   5.869135   5.159859   6.578412


#### Common Schema (All MODIS Products):

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `fips` | string | 5-digit county FIPS code (state + county) | `19053` |
| `county_name` | string | County name | `Decatur` |
| `date` | datetime | Start date of 8/16-day composite period | `2017-05-01` |
| `band` | string | Specific measurement band | `NDVI`, `EVI`, `ET`, `PET`, `LST_Day`, `LST_Night` |
| `product` | string | Product category | `ndvi`, `et`, `lst` |
| `mean` | float | County-wide mean value for corn pixels | `0.681` |
| `std` | float | Standard deviation across county | `0.126` |
| `min` | float | Minimum value in county | `0.2853` |
| `max` | float | Maximum value in county | `0.8977` |
| `pixel_count` | int | Number of valid pixels in county | `5722` |
| `median` | float | Approximate median (from mean) | `0.681` |
| `p25` | float | Approximate 25th percentile | `0.597` |
| `p75` | float | Approximate 75th percentile | `0.766` |

#### Units and Ranges by Band:

| Band | Unit | Typical Range | Stress Threshold | Interpretation |
|------|------|---------------|------------------|----------------|
| **Vegetation Health** ||||
| `NDVI` | Index | 0.0 - 1.0 | <0.4 = stressed | Normalized Difference Vegetation Index |
| `EVI` | Index | 0.0 - 1.0 | <0.3 = stressed | Enhanced Vegetation Index (less saturation) |
| **Water Stress** ||||
| `ET` | mm/8-day | 0 - 100 | <20 = drought | Actual evapotranspiration |
| `PET` | mm/8-day | 0 - 100 | - | Potential evapotranspiration (atmospheric demand) |
| `ET/PET ratio` | - | 0.0 - 1.0 | <0.5 = severe stress | Water stress indicator (derived) |
| **Heat Stress** ||||
| `LST_Day` | °Celsius | 15 - 45°C | >35°C = heat stress | Daytime land surface temperature |
| `LST_Night` | °Celsius | 5 - 25°C | >20°C = hot nights | Nighttime land surface temperature |
| `DTR` | °C | 5 - 25°C | >20°C = high stress | Diurnal temperature range (derived) |

#### Corn Growth Stages and NDVI Patterns:

```
Early May (Planting):         NDVI ~0.2-0.3 (bare soil/emergence)
Late May-June (Vegetative):   NDVI ~0.4-0.6 (rapid growth)
July (Tasseling/Silking):     NDVI ~0.7-0.9 (peak greenness)
August (Grain Fill):          NDVI ~0.6-0.8 (mature canopy)
September (Maturity):         NDVI ~0.4-0.6 (senescence begins)
October (Harvest):            NDVI ~0.2-0.4 (drying down)
```

---

## 🗂️ GCS Bucket Structure

```
gs://agriguard-ac215-data/
│
├── raw/
│   ├── yields/
│   │   ├── iowa_corn_yields_2017_2025.csv        # Combined file
│   │   ├── iowa_corn_yields_2017.csv             # Individual years
│   │   ├── iowa_corn_yields_2018.csv
│   │   └── ...
│   │
│   └── masks/
│       ├── iowa_counties.geojson                 # County boundaries
│       └── corn/
│           ├── iowa_corn_mask_2017.tif
│           ├── iowa_corn_mask_2018.tif
│           └── ...
│
└── processed/
    └── modis/
        ├── ndvi/
        │   └── iowa_counties_ndvi_20170501_20251012.parquet    (~38,610 records)
        ├── et/
        │   └── iowa_counties_et_20170501_20251012.parquet      (~75,735 records)
        └── lst/
            └── iowa_counties_lst_20170501_20251013.parquet     (~75,735 records)
```

---

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Platform:**
   - GCP project with Earth Engine API enabled
   - Service account with Earth Engine Resource Viewer role
   - Service account key JSON file

2. **API Keys:**
   - USDA NASS Quick Stats API key ([Get free key](https://quickstats.nass.usda.gov/api))
   - NASA EarthData token ([Generate token](https://urs.earthdata.nasa.gov/home))

3. **Docker:**
   - Docker and Docker Compose installed

### Setup

1. **Clone and configure:**
   ```bash
   cd data-ingestion
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Add GCP credentials:**
   ```bash
   mkdir -p secrets
   # Place your GCP service account key as secrets/gcp-key.json
   ```

3. **Run the pipeline:**
   ```bash
   # Run all downloaders in sequence (default)
   docker-compose up
   
   # Or run individual downloaders
   docker-compose run --rm data-ingestion python src/downloaders/mask_downloader.py
   docker-compose run --rm data-ingestion python src/downloaders/yield_downloader.py
   docker-compose run --rm data-ingestion python src/downloaders/gee_modis_downloader.py
   ```

## 📋 Components

### Data Downloaders

| Script | Purpose | Source | Output |
|--------|---------|--------|--------|
| `mask_downloader.py` | County boundaries & corn masks | USDA NASS CDL, Census TIGER | GeoTIFF, GeoJSON |
| `yield_downloader.py` | County corn yields | USDA NASS Quick Stats API | CSV |
| `gee_modis_downloader.py` | Satellite indicators | Google Earth Engine | Parquet |

### Key Features

✅ **Smart caching:** Checks GCS before downloading, skips existing data  
✅ **Incremental updates:** Only downloads missing years/dates  
✅ **Auto date detection:** Downloads from `START_YEAR` to present by default  
✅ **Error handling:** Continues on failures, reports summary  
✅ **Progress tracking:** Detailed logging with progress bars  

---

## ⚙️ Configuration

### Environment Variables

```bash
# GCS Configuration
GCS_BUCKET_NAME=agriguard-ac215-data
GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json
GCP_PROJECT_ID=your-project-id

# API Keys
NASS_API_KEY=your_nass_api_key
NASA_TOKEN=your_nasa_token

# Data Range
START_YEAR=2017                    # Default start year
# START_DATE=2020-05-01            # Optional: override with specific dates
# END_DATE=2020-10-31
# CORN_YEARS=2020,2021,2022        # Optional: specific years only

# Products (comma-separated)
PRODUCTS=ndvi,et,lst               # Which MODIS products to download

# Processing
NUM_WORKERS=4
TEMP_DIR=/temp
LOG_LEVEL=INFO
```

### Customization Examples

**Download specific years:**
```bash
docker-compose run --rm \
  -e CORN_YEARS="2020,2021,2022" \
  data-ingestion python src/downloaders/gee_modis_downloader.py
```

**Download specific products:**
```bash
docker-compose run --rm \
  -e PRODUCTS="ndvi,lst" \
  data-ingestion python src/downloaders/gee_modis_downloader.py
```

**Custom date range:**
```bash
docker-compose run --rm \
  -e START_DATE="2020-05-01" \
  -e END_DATE="2020-10-31" \
  data-ingestion python src/downloaders/gee_modis_downloader.py
```

---

## 🔍 Verifying Data

**List files in GCS:**
```bash
gsutil ls -r gs://agriguard-ac215-data/
```

**Check yield data:**
```bash
gsutil cat gs://agriguard-ac215-data/raw/yields/iowa_corn_yields_2017_2025.csv | head
```

**Check MODIS data:**
```bash
gsutil ls gs://agriguard-ac215-data/processed/modis/
```

**Download sample for inspection:**
```bash
gsutil cp gs://agriguard-ac215-data/processed/modis/ndvi/iowa_counties_ndvi_*.parquet .
```

---

## 🔗 Data Relationships

The three datasets work together to provide comprehensive corn analytics:

```
┌──────────────────────────────────────────────────────────────────┐
│                     SPATIAL HIERARCHY                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  iowa_counties.geojson (99 counties)                             │
│         ↓                                                        │
│  iowa_corn_mask_2024.tif (30m binary raster)                     │
│         ↓                                                        │
│  MODIS pixels (500m-1km) → masked to corn only                   │
│         ↓                                                        │
│  County aggregation → iowa_counties_et_*.parquet                 │
│         ↓                                                        │
│  Join with iowa_corn_yields_*.csv (target variable)              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## 📂 Project Structure

```
data-ingestion/
├── .env.example              # Template (commit)
├── .env                      # Your credentials (DO NOT commit)
├── .gitignore               # Git ignore rules
├── docker-compose.yml        # Docker orchestration
├── Dockerfile               # Container definition
├── pyproject.toml           # Python dependencies
├── README.md                # This file
│
├── src/
│   ├── downloaders/         # Data download scripts
│   │   ├── gee_modis_downloader.py
│   │   ├── mask_downloader.py
│   │   └── yield_downloader.py
│   │
│   └── utils/               # Shared utilities
│       └── gcs_utils.py     # GCS operations
│
├── secrets/                 # GCP keys (DO NOT commit)
├── temp/                    # Temporary files (auto-cleaned)
└── logs/                    # Application logs
```


## 📊 Data Statistics

**Typical dataset sizes:**
- **Yields:** ~100 counties × 8 years = ~800 records per file
- **Masks:** ~50-100 MB per year (30m resolution)
- **MODIS:** 
  - NDVI: ~38,610 records (23 composites/season × 8.5 years × 99 counties × 2 bands)
  - ET: ~75,735 records (45 composites/season × 8.5 years × 99 counties × 2 bands)
  - LST: ~75,735 records (45 composites/season × 8.5 years × 99 counties × 2 bands)

**Coverage:**
- **Spatial:** All 99 Iowa counties
- **Temporal:** 2017-present (8+ years)
- **Growing Season:** May 1 - October 31 each year
- **Frequency:** 8-16 day composites during growing season

**File Sizes (compressed Parquet):**
- NDVI: ~800 KB - 1.2 MB
- ET: ~1.5 MB - 2.0 MB
- LST: ~1.5 MB - 2.0 MB

---

## 🔒 Security Notes

⚠️ **Never commit:**
- `.env` file (contains API keys)
- `secrets/` directory (contains GCP keys)
- `temp/` directory (may contain downloaded data)

✅ **Safe to commit:**
- `.env.example` (template without real values)
- Source code in `src/`
- Configuration in `config/`