# Iowa Corn Mask Downloader - Cloud Run Container

Automated download and processing of Iowa corn field masks from USDA NASS Cropland Data Layer (CDL) for years 2010 onwards.

## Overview

- **Downloads**: Iowa corn field masks from USDA NASS CDL (2010-present)
- **Processes**: Binary rasters (1=corn, 0=non-corn) at 30m resolution
- **Uploads**: To Google Cloud Storage bucket
- **Smart**: Only downloads missing years
- **Automatic**: Checks for new years automatically

## Output Data

```
gs://agriguard-ac215-data/data_raw/masks/
├── iowa_counties.geojson          # 99 Iowa counties with FIPS codes
├── iowa_corn_mask_2010.tif        # Binary corn masks
├── iowa_corn_mask_2011.tif        # 30m resolution
├── ...                            # LZW compressed
└── iowa_corn_mask_2024.tif        # Updates annually
```

**File Specifications:**
- Format: GeoTIFF (single-band, 8-bit unsigned integer)
- Resolution: 30 meters
- Projection: Albers Equal Area (matches CDL source)
- Compression: LZW (lossless)
- Values: 1 = corn, 0 = non-corn

## Quick Setup

### Prerequisites
- Google Cloud SDK installed (`gcloud`)
- Docker Desktop (for local testing)
- GCP project with billing enabled

### 1. Setup GCP Resources (One-time)

**Windows:**
```powershell
.\scripts\Setup-GCP.ps1
```

**Linux/Mac:**
```bash
./scripts/setup-gcp.sh
```

This creates:
- Service account: `mask-downloader@PROJECT.iam.gserviceaccount.com`
- GCS bucket: `agriguard-ac215-data`
- Required permissions

### 2. Deploy to Cloud Run

**Windows:**
```powershell
# Build and push container
.\scripts\Build-Container.ps1

# Deploy to Cloud Run
.\scripts\Deploy-CloudRun.ps1
```

**Linux/Mac:**
```bash
# Build and push container
./scripts/build.sh

# Deploy to Cloud Run
./scripts/deploy-cloudrun.sh
```

### 3. Execute Job

```bash
# Run the job now
gcloud run jobs execute mask-downloader --region=us-central1

# Check status
gcloud run jobs executions list --job=mask-downloader --region=us-central1
```

### 4. Schedule Monthly Updates

```bash
# Run on 1st of every month at midnight
gcloud scheduler jobs create http mask-downloader-monthly \
    --location=us-central1 \
    --schedule='0 0 1 * *' \
    --uri='https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/agriguard-ac215/jobs/mask-downloader:run' \
    --http-method=POST \
    --oauth-service-account-email=mask-downloader@agriguard-ac215.iam.gserviceaccount.com \
    --description="Monthly corn mask update" \
    --time-zone="America/Chicago"
```

## How It Works

### Smart Downloading
1. Checks GCS bucket for existing masks
2. Downloads only missing years from USDA NASS
3. Processes Iowa region (clips from nationwide data)
4. Creates binary corn masks
5. Uploads to GCS with LZW compression

### Automatic Future Updates
The container automatically checks for new years:
- **2025**: Checks 2010-2025, downloads 2025 if available
- **2026**: Checks 2010-2026, downloads 2026 if available
- No code changes needed - future-proof!

### Typical Execution Times
- First run (2010-2024): ~2-4 hours (downloads 15 years)
- Subsequent runs: ~2 minutes (checks only, downloads nothing)
- New year available: ~15 minutes (downloads 1 year)

## Data Update Schedule

USDA NASS CDL releases annually:
- **Growing Season**: Spring-Fall (e.g., 2025)
- **Data Release**: December-February (e.g., Dec 2025 - Feb 2026)
- **Your Monthly Job**: Catches within ~30 days of release

## Costs

| Item | Cost |
|------|------|
| Cloud Run (checking only) | $0.02/month × 11 = $0.22/year |
| Cloud Run (downloading 1 year) | $0.10/year |
| GCS storage (15 years) | $0.20/month = $2.40/year |
| **Total Annual** | **~$2.72/year** |

## Monitoring

**Windows:**
```powershell
# View status
.\scripts\View-Status.ps1 status

# View logs
.\scripts\View-Status.ps1 logs

# List executions
.\scripts\View-Status.ps1 list
```

**Linux/Mac:**
```bash
# View status
./scripts/view-status.sh status

# View logs
./scripts/view-status.sh logs
```

## Configuration

Update environment variables in Cloud Run job:

```bash
# Change start year
gcloud run jobs update mask-downloader \
    --region=us-central1 \
    --set-env-vars="START_YEAR=2015"

# Download specific years only
gcloud run jobs update mask-downloader \
    --region=us-central1 \
    --set-env-vars="MASK_YEARS=2022,2023,2024"

# Increase resources for faster processing
gcloud run jobs update mask-downloader \
    --region=us-central1 \
    --memory=8Gi --cpu=4
```

## Local Testing (Optional)

Set credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

Run with Docker Compose:
```bash
docker-compose up
```

## Data Sources

- **CDL Masks**: [USDA NASS Cropland Data Layer](https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php)
- **County Boundaries**: [US Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)

## File Structure

```
mask-downloader-container/
├── mask_downloader.py          # Main download script
├── utils/
│   ├── gcs_utils.py           # GCS operations
│   └── __init__.py
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Local testing
├── .dockerignore              # Exclude from build
├── .gitignore                 # Exclude from git
└── scripts/
    ├── Setup-GCP.ps1          # Windows GCP setup
    ├── Build-Container.ps1    # Windows build
    ├── Deploy-CloudRun.ps1    # Windows deploy
    ├── View-Status.ps1        # Windows monitoring
    ├── setup-gcp.sh           # Linux/Mac setup
    ├── build.sh               # Linux/Mac build
    ├── deploy-cloudrun.sh     # Linux/Mac deploy
    └── view-status.sh         # Linux/Mac monitoring
```

## Troubleshooting

### "Permission denied"
```bash
# Re-run setup to grant permissions
./scripts/setup-gcp.sh
```

### "Year XXXX failed to download"
Some years may not be available in CDL archives. Check manually at:
https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php

### "Out of memory"
```bash
# Increase Cloud Run resources
gcloud run jobs update mask-downloader \
    --region=us-central1 \
    --memory=8Gi --cpu=4
```

## Security

- ✅ Service account with least-privilege permissions
- ✅ No hardcoded credentials
- ✅ Workload Identity for Cloud Run (no keys needed)
- ✅ Secrets excluded from container build
- ✅ HTTPS for all data transfers

## Support

- [USDA NASS CDL Documentation](https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php)
- [Google Cloud Run Jobs](https://cloud.google.com/run/docs/create-jobs)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)

## License

Part of the AgriGuard AC215 project.
