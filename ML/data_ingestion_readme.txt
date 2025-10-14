# AgriGuard Data Ingestion

Multi-sensor data ingestion pipeline for Iowa corn field monitoring with **corn field masking** from USDA CDL.

## 🌽 Features

- **Corn Field Masking**: Uses USDA Cropland Data Layer to identify and mask corn fields
- **Multi-Source Data**: USDA NASS yields, Sentinel-2 NDVI, Sentinel-1 SAR (planned), MODIS ET (planned)
- **Cloud-Native**: Direct upload to Google Cloud Storage
- **Containerized**: Fully Dockerized for reproducibility
- **County-Level**: Process all 99 Iowa counties or specific subsets

## 📁 Structure

```
data-ingestion/
├── src/
│   ├── download_corn_masks.py       # USDA CDL corn field masks
│   ├── download_yield_data.py       # USDA NASS yield data
│   ├── download_sentinel2_data.py   # Sentinel-2 NDVI (corn fields only)
│   ├── pipeline_orchestrator.py     # Main pipeline coordinator
│   └── utils/
│       ├── gcs_utils.py             # GCS operations
│       └── logging_utils.py         # Logging setup
├── configs/
│   └── data_config.yaml             # Configuration
├── tests/                           # Unit tests
├── Dockerfile                       # Container definition
├── docker-shell.ps1                 # PowerShell wrapper
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- Docker installed
- Google Cloud Platform account
- Google Earth Engine account (free)
- USDA NASS API key (optional, will use sample data without it)

### 2. Setup

**Create secrets directory and add GCP credentials:**
```powershell
# Create secrets directory
mkdir ..\secrets

# Copy your GCP service account key
cp path\to\your\gcp-key.json ..\secrets\gcp-key.json
```

**Create `.env` file in data-ingestion folder:**
```env
GCS_BUCKET=agriguard-ac215-data
USDA_NASS_API_KEY=your-api-key-here
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcp-key.json
```

### 3. Build Container

```powershell
.\docker-shell.ps1 build
```

### 4. Authenticate Earth Engine

```powershell
.\docker-shell.ps1 ee-auth
```

Follow the prompts to authenticate with your Google account that has Earth Engine access.

### 5. Run Pipeline

**Option A: Full Pipeline (recommended for testing)**
```powershell
# Run with sample yield data and priority counties
.\docker-shell.ps1 pipeline `
    --start-date 2024-06-01 `
    --end-date 2024-08-31 `
    --sample-yields `
    --counties Story `
    --counties Hamilton `
    --verbose
```

**Option B: Individual Components**

Download corn masks:
```powershell
.\docker-shell.ps1 masks --year 2024 --counties Story --verbose
```

Download yield data:
```powershell
.\docker-shell.ps1 yields --start-year 2020 --end-year 2024 --verbose
```

Download Sentinel-2 NDVI (corn fields only):
```powershell
.\docker-shell.ps1 sentinel2 `
    --start-date 2024-06-01 `
    --end-date 2024-08-31 `
    --counties Story `
    --verbose
```

## 📊 Data Sources

### 1. USDA Cropland Data Layer (CDL)
- **Purpose**: Corn field identification masks
- **Resolution**: 30m
- **Source**: Earth Engine `USDA/NASS/CDL`
- **Output**: Binary masks (1=corn, 0=other)
- **GCS Path**: `raw/masks/corn/iowa/{year}/`

### 2. USDA NASS Yields
- **Purpose**: County-level corn yields
- **API**: QuickStats
- **Output**: CSV with yields in bu/acre
- **GCS Path**: `raw/yields/iowa/{year}/`

### 3. Sentinel-2 (Optical)
- **Purpose**: NDVI/EVI vegetation indices
- **Resolution**: 10m
- **Masking**: Only corn pixels processed
- **Cloud filtering**: <20% cloud cover
- **Output**: County-level statistics CSV
- **GCS Path**: `raw/sentinel2/iowa/{year}/{date}/`

### 4. Sentinel-1 (SAR) - Planned
- **Purpose**: All-weather moisture detection
- **Resolution**: 10m

### 5. MODIS ET - Planned
- **Purpose**: Evapotranspiration anomalies
- **Resolution**: 500m

## 🗂️ Output Data Structure

### Local Storage
```
data/
├── raw/
│   ├── masks/
│   │   └── corn/
│   │       ├── corn_mask_Story_2024.tif
│   │       └── corn_mask_stats_2024.json
│   ├── yields/
│   │   ├── iowa_corn_yields_2020_2024.csv
│   │   └── iowa_corn_yields_2020_2024_metadata.json
│   └── sentinel2/
│       ├── iowa_corn_sentinel2_ndvi_2024-06-01_2024-08-31.csv
│       └── iowa_corn_sentinel2_ndvi_2024-06-01_2024-08-31_metadata.json
└── logs/
    └── pipeline_reports/
        └── pipeline_report_20241009_143022.json
```

### GCS Storage
```
gs://agriguard-ac215-data/
├── raw/
│   ├── masks/corn/iowa/2024/
│   ├── yields/iowa/2020_2024/
│   └── sentinel2/iowa/2024/
└── logs/pipeline_reports/
```

## ⚙️ Configuration

Edit `configs/data_config.yaml` to customize:

```yaml
# Priority counties (for testing)
priority_counties:
  - Story
  - Hamilton
  - Wright
  - Kossuth
  - Pocahontas

# Sentinel-2 settings
sentinel2:
  cloud_threshold: 20  # Max cloud cover %
  resolution: 10       # meters
  
# GCS paths
gcs:
  bucket: "agriguard-ac215-data"
  paths:
    yields: "raw/yields/iowa/{year}"
    sentinel2: "raw/sentinel2/iowa/{year}/{date}"
    corn_masks: "raw/masks/corn/iowa/{year}"
```

## 🧪 Testing

Run unit tests:
```powershell
.\docker-shell.ps1 run pytest tests/ -v
```

## 📝 Command Reference

### Pipeline Orchestrator
```powershell
.\docker-shell.ps1 pipeline --help
```

Options:
- `--start-date`: Start date (YYYY-MM-DD)
- `--end-date`: End date (YYYY-MM-DD)
- `--counties`: Specific counties (repeat for multiple)
- `--sample-yields`: Use sample data instead of real USDA data
- `--skip-masks`: Skip corn mask download
- `--verbose`: Detailed logging

### Corn Masks
```powershell
.\docker-shell.ps1 masks --help
```

Options:
- `--year`: Year to download (required)
- `--counties`: Specific counties
- `--no-export`: Calculate stats only, skip GCS export
- `--monitor`: Wait for export tasks to complete

### Yield Data
```powershell
.\docker-shell.ps1 yields --help
```

Options:
- `--start-year`: Start year (default: 2020)
- `--end-year`: End year (default: 2024)
- `--sample`: Generate sample data
- `--skip-upload`: Local only, no GCS

### Sentinel-2 NDVI
```powershell
.\docker-shell.ps1 sentinel2 --help
```

Options:
- `--start-date`: Start date (YYYY-MM-DD)
- `--end-date`: End date (YYYY-MM-DD)
- `--counties`: Specific counties
- `--export-images`: Export full GeoTIFF images (in addition to stats)

## 🔧 Troubleshooting

### Earth Engine Authentication Error
```
earthengine authenticate
```
Then restart the container.

### GCS Permission Denied
- Ensure service account has Storage Object Admin role
- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid key

### No USDA Data Downloaded
- Check API key is set: `echo $env:USDA_NASS_API_KEY`
- Use `--sample` flag to generate test data

### Rate Limiting from Earth Engine
- Process fewer counties at a time
- Add delays between requests (built into code)

## 📈 Performance

**Typical execution times** (3 counties, 90 days):
- Corn masks: ~5 min (includes GCS export)
- Yield data: ~30 seconds
- Sentinel-2 NDVI: ~10 min (stats only)

**Processing all 99 counties**:
- Corn masks: ~2-3 hours
- Sentinel-2 NDVI: ~4-6 hours

## 🎯 MS2 Deliverables

This pipeline demonstrates:

✅ **Containerized ingestion** - Docker with reproducible environment  
✅ **Versioned data pipelines** - Metadata tracking and GCS versioning  
✅ **Multi-sensor data** - Yields + Sentinel-2 NDVI + CDL masks  
✅ **Scalable computing** - Earth Engine distributed processing  
✅ **Cloud storage** - Direct GCS upload  
✅ **Data quality** - Corn field masking and validation  

## 📚 Additional Resources

- [USDA NASS QuickStats](https://quickstats.nass.usda.gov/)
- [Google Earth Engine](https://earthengine.google.com/)
- [Sentinel-2 Documentation](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2)
- [USDA CDL](https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php)

## 👥 Team

AgriGuard Team - AC215/E115 Harvard IACS  
- Binh Vu
- Sanil Edwin
- Moody Farra
- Artem Biriukov

---

**Version**: 1.0.0  
**Last Updated**: October 2024
