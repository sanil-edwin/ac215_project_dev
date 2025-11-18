# Iowa Corn Yield Downloader - Cloud Run Container

Automated download of Iowa county-level corn yield data from USDA NASS Quick Stats API for years 2017 onwards.

## Overview

- **Downloads**: County-level corn yield data from USDA NASS (2017-present)
- **Processes**: Cleans and standardizes yield records (bushels/acre)
- **Uploads**: To Google Cloud Storage bucket
- **Smart**: Only downloads missing years
- **Automatic**: Checks for new years automatically

## Output Data

```
gs://agriguard-ac215-data/data_raw/yields/
├── iowa_corn_yields_2017_2024.csv    # Combined file
├── iowa_corn_yields_2017.csv         # Individual year files
├── iowa_corn_yields_2018.csv
├── ...
└── iowa_corn_yields_2024.csv
```

**File Schema:**
```csv
year,state,state_fips,county,county_fips,yield_bu_per_acre,unit,fips
2017,IOWA,19,ADAIR,1,175.2,BU / ACRE,19001
2017,IOWA,19,ADAMS,3,179.9,BU / ACRE,19003
```

**Columns:**
- `year`: Harvest year (integer)
- `state`: State name (IOWA)
- `state_fips`: State FIPS code (19)
- `county`: County name
- `county_fips`: County FIPS code (1-197)
- `yield_bu_per_acre`: Corn yield in bushels per acre (float)
- `unit`: Unit of measurement (BU / ACRE)
- `fips`: Combined 5-digit FIPS code (state + county)

## Quick Setup

### Prerequisites
- Google Cloud SDK installed (`gcloud`)
- Docker Desktop (for local testing)
- GCP project with billing enabled
- NASS API key (free, see below)

### 0. Get NASS API Key

1. Visit: https://quickstats.nass.usda.gov/api
2. Request a free API key (instant approval)
3. Save your key - you'll need it later

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
- Service account: `yield-downloader@PROJECT.iam.gserviceaccount.com`
- GCS bucket: `agriguard-ac215-data`
- Required permissions

### 2. Set Your API Key

**Windows:**
```powershell
$env:NASS_API_KEY = "your_key_here"
```

**Linux/Mac:**
```bash
export NASS_API_KEY="your_key_here"
```

### 3. Deploy to Cloud Run

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

### 4. Execute Job

```bash
# Run the job now
gcloud run jobs execute yield-downloader --region=us-central1

# Check status
gcloud run jobs executions list --job=yield-downloader --region=us-central1
```

### 5. Schedule Monthly Updates

```bash
# Run on 1st of every month at midnight
gcloud scheduler jobs create http yield-downloader-monthly \
    --location=us-central1 \
    --schedule='0 0 1 * *' \
    --uri='https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/agriguard-ac215/jobs/yield-downloader:run' \
    --http-method=POST \
    --oauth-service-account-email=yield-downloader@agriguard-ac215.iam.gserviceaccount.com \
    --description="Monthly corn yield update" \
    --time-zone="America/Chicago"
```

## How It Works

### Smart Downloading
1. Checks GCS bucket for existing yield files
2. Downloads only missing years from USDA NASS API
3. Cleans and standardizes data format
4. Uploads individual year files and combined dataset to GCS

### Automatic Future Updates
The container automatically checks for new years:
- **2025**: Checks 2017-2025, downloads 2025 if available
- **2026**: Checks 2017-2026, downloads 2026 if available
- No code changes needed - future-proof!

### Typical Execution Times
- First run (2017-2024): ~2-5 minutes (downloads 8 years)
- Subsequent runs: ~30 seconds (checks only, downloads nothing)
- New year available: ~1 minute (downloads 1 year)

## Data Update Schedule

USDA NASS releases county yield data:
- **Growing Season**: Spring-Fall (e.g., 2025)
- **Data Release**: December-February (e.g., Jan-Feb 2026)
- **Your Monthly Job**: Catches within ~30 days of release

## Costs

| Item | Cost |
|------|------|
| Cloud Run (checking only) | $0.01/month × 11 = $0.11/year |
| Cloud Run (downloading 1 year) | $0.05/year |
| GCS storage (8 years) | $0.05/month = $0.60/year |
| **Total Annual** | **~$0.76/year** |

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
gcloud run jobs update yield-downloader \
    --region=us-central1 \
    --set-env-vars="START_YEAR=2010"

# Download specific years only
gcloud run jobs update yield-downloader \
    --region=us-central1 \
    --set-env-vars="YIELD_YEARS=2020,2021,2022,2023,2024"

# Update API key (if changed)
gcloud run jobs update yield-downloader \
    --region=us-central1 \
    --set-env-vars="NASS_API_KEY=your_new_key"
```

## Local Testing (Optional)

1. Create `.env` file from template:
```bash
cp .env.template .env
# Edit .env and add your NASS_API_KEY
```

2. Set credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

3. Run with Docker Compose:
```bash
docker-compose up
```

## Data Sources

- **Yield Data**: [USDA NASS Quick Stats API](https://quickstats.nass.usda.gov/api)
  - Commodity: Corn
  - Category: Yield (BU / ACRE)
  - Level: County
  - State: Iowa
  - Source: Survey data

## Data Quality

**Coverage:**
- 99 Iowa counties
- Years: 2017-present
- ~800 records total (99 counties × 8 years)

**Quality Checks:**
- Removes non-numeric values
- Validates FIPS codes
- Sorts by year and county
- Creates combined 5-digit FIPS for easy joining

**Example Statistics (2017-2024):**
- Mean yield: ~180-200 bu/acre
- Range: ~150-230 bu/acre
- Standard deviation: ~20-30 bu/acre

## File Structure

```
yield-downloader-container/
├── yield_downloader.py          # Main download script
├── utils/
│   ├── gcs_utils.py            # GCS operations
│   └── __init__.py
├── Dockerfile                   # Container definition
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Local testing
├── .dockerignore               # Exclude from build
├── .gitignore                  # Exclude from git
├── .env.template               # Environment template
└── scripts/
    ├── Setup-GCP.ps1           # Windows GCP setup
    ├── Build-Container.ps1     # Windows build
    ├── Deploy-CloudRun.ps1     # Windows deploy
    ├── View-Status.ps1         # Windows monitoring
    ├── setup-gcp.sh            # Linux/Mac setup
    ├── build.sh                # Linux/Mac build
    ├── deploy-cloudrun.sh      # Linux/Mac deploy
    └── view-status.sh          # Linux/Mac monitoring
```

## Troubleshooting

### "NASS_API_KEY not set"
```bash
# Get your key at: https://quickstats.nass.usda.gov/api
# Then set it:
export NASS_API_KEY='your_key_here'  # Linux/Mac
$env:NASS_API_KEY = 'your_key_here'  # Windows
```

### "Permission denied"
```bash
# Re-run setup to grant permissions
./scripts/setup-gcp.sh
```

### "No data returned for year XXXX"
Some years may not be published yet. USDA releases data ~2 months after harvest:
- 2024 harvest: October 2024
- 2024 data release: December 2024 - February 2025

Check data availability: https://quickstats.nass.usda.gov/

### API Rate Limits
USDA NASS API limits:
- Free tier: Sufficient for this use case
- Rate limit: Not typically an issue for sequential year downloads
- If rate limited: Job will retry automatically

## Integration with AgriGuard

This yield downloader is part of the AgriGuard ML pipeline:

```
yield-downloader (this container)
    ↓
gs://agriguard-ac215-data/data_raw/yields/
    ↓
ML Pipeline (preprocessing container)
    ↓
Model Training (yield forecasting)
```

**Used by:**
- Baseline computation (historical norms)
- Model training (target variable)
- Validation (ground truth)
- Performance metrics (RMSE, R²)

## Security

- ✅ Service account with least-privilege permissions
- ✅ No hardcoded credentials
- ✅ Workload Identity for Cloud Run (no keys needed)
- ✅ Secrets excluded from container build
- ✅ HTTPS for all API calls

## Support

- [USDA NASS Quick Stats API](https://quickstats.nass.usda.gov/api)
- [USDA NASS API Documentation](https://quickstats.nass.usda.gov/api_info)
- [Google Cloud Run Jobs](https://cloud.google.com/run/docs/create-jobs)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)

## License

Part of the AgriGuard AC215 project.

## Additional Notes

### Why County-Level?
- USDA NASS provides reliable county-level data
- Sufficient resolution for Iowa-wide analysis
- Matches spatial resolution of satellite aggregations
- Reduces noise compared to field-level estimates

### Data Completeness
- Most recent year may be incomplete (in-season)
- Final yields released 2-3 months post-harvest
- Historical data is stable and complete
- Missing counties are rare and usually indicate non-production

### Best Practices
1. Run monthly to catch new data releases
2. Monitor for API changes (rare but possible)
3. Validate downloaded data against USDA website
4. Keep service account permissions minimal
5. Use Cloud Scheduler for automated updates
