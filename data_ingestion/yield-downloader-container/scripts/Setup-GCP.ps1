# ==========================================
# COPY THIS ENTIRE FILE AND SAVE AS Setup-GCP.ps1
# ==========================================

# Setup script for Google Cloud Platform resources
# Creates service account and grants necessary permissions

param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$ServiceAccountName = "yield-downloader",
    [string]$BucketName = "agriguard-ac215-data"
)

if (-not $ProjectId) {
    $ProjectId = "agriguard-ac215"
}

$ServiceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Setting up GCP Resources" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Project: $ProjectId"
Write-Host "Service Account: $ServiceAccountEmail"
Write-Host "Bucket: $BucketName"
Write-Host "======================================"

# Enable required APIs
Write-Host "`nEnabling required APIs..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    containerregistry.googleapis.com `
    cloudbuild.googleapis.com `
    storage-api.googleapis.com `
    --project=$ProjectId

# Create service account if it doesn't exist
Write-Host "`nCreating service account..." -ForegroundColor Yellow
$null = gcloud iam service-accounts describe $ServiceAccountEmail --project=$ProjectId 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Service account already exists" -ForegroundColor Green
}
else {
    gcloud iam service-accounts create $ServiceAccountName `
        --display-name="Yield Downloader Service Account" `
        --description="Service account for downloading and processing corn yield data" `
        --project=$ProjectId
    Write-Host "✓ Service account created" -ForegroundColor Green
}

# Grant permissions to service account
Write-Host "`nGranting permissions..." -ForegroundColor Yellow

# Storage permissions (to read/write to GCS bucket)
gcloud projects add-iam-policy-binding $ProjectId `
    --member="serviceAccount:$ServiceAccountEmail" `
    --role="roles/storage.objectAdmin" `
    --condition=None

# Cloud Run permissions (to run jobs)
gcloud projects add-iam-policy-binding $ProjectId `
    --member="serviceAccount:$ServiceAccountEmail" `
    --role="roles/run.invoker" `
    --condition=None

Write-Host "✓ Permissions granted" -ForegroundColor Green

# Check if GCS bucket exists
Write-Host "`nChecking GCS bucket..." -ForegroundColor Yellow
$null = gsutil ls gs://$BucketName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Bucket already exists: gs://$BucketName" -ForegroundColor Green
}
else {
    Write-Host "Creating bucket..." -ForegroundColor Yellow
    gsutil mb -p $ProjectId -l US gs://$BucketName
    Write-Host "✓ Bucket created: gs://$BucketName" -ForegroundColor Green
}

# Create folder structure in bucket
Write-Host "`nCreating folder structure in bucket..." -ForegroundColor Yellow
$emptyFile = New-TemporaryFile
"" | Out-File $emptyFile
gsutil cp $emptyFile gs://$BucketName/data_raw/yields/.gitkeep
Remove-Item $emptyFile

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service Account: $ServiceAccountEmail"
Write-Host "Bucket: gs://$BucketName"
Write-Host "Data location: gs://$BucketName/data_raw/yields/"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "1. Get your NASS API key at: https://quickstats.nass.usda.gov/api"
Write-Host "2. Set API key: `$env:NASS_API_KEY = 'your_key_here'"
Write-Host "3. Build the Docker image: .\scripts\Build-Container.ps1"
Write-Host "4. Deploy to Cloud Run: .\scripts\Deploy-CloudRun.ps1"
Write-Host "5. Run the job: gcloud run jobs execute yield-downloader --region=us-central1"
Write-Host "======================================"
