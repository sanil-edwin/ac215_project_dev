# Setup GCP resources for mask downloader
param(
    [string]$ProjectId = "agriguard-ac215",
    [string]$BucketName = "agriguard-ac215-data",
    [string]$ServiceAccountName = "mask-downloader"
)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Setting up GCP Resources" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Project: $ProjectId"
Write-Host "  Bucket: $BucketName"
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$ServiceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"

# Check gcloud
Write-Host "Checking gcloud CLI..." -ForegroundColor Yellow
$null = gcloud version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: gcloud CLI not found" -ForegroundColor Red
    exit 1
}
Write-Host "OK: gcloud CLI found" -ForegroundColor Green

# Set project
Write-Host ""
Write-Host "Setting project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable APIs
Write-Host ""
Write-Host "Enabling APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com containerregistry.googleapis.com cloudbuild.googleapis.com storage-api.googleapis.com --project=$ProjectId

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: APIs enabled" -ForegroundColor Green
}

# Create service account
Write-Host ""
Write-Host "Creating service account..." -ForegroundColor Yellow
$null = gcloud iam service-accounts describe $ServiceAccountEmail --project=$ProjectId 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Service account exists" -ForegroundColor Green
}
else {
    gcloud iam service-accounts create $ServiceAccountName --display-name="Mask Downloader" --project=$ProjectId
    Write-Host "OK: Service account created" -ForegroundColor Green
}

# Grant permissions
Write-Host ""
Write-Host "Granting permissions..." -ForegroundColor Yellow
$null = gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$ServiceAccountEmail" --role="roles/storage.objectAdmin" 2>&1
$null = gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$ServiceAccountEmail" --role="roles/run.invoker" 2>&1
Write-Host "OK: Permissions granted" -ForegroundColor Green

# Create bucket
Write-Host ""
Write-Host "Checking bucket..." -ForegroundColor Yellow
$null = gsutil ls gs://$BucketName 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Bucket exists" -ForegroundColor Green
}
else {
    gsutil mb -p $ProjectId -l US gs://$BucketName
    Write-Host "OK: Bucket created" -ForegroundColor Green
}

# Create folders
Write-Host ""
Write-Host "Creating folders..." -ForegroundColor Yellow
$null = "" | gsutil cp - gs://$BucketName/data_raw/masks/.gitkeep 2>&1
Write-Host "OK: Folders created" -ForegroundColor Green

# Download key
Write-Host ""
Write-Host "Download service account key? (Y/N)" -ForegroundColor Yellow
$response = Read-Host

if ($response -eq 'Y' -or $response -eq 'y') {
    if (-not (Test-Path ".\secrets")) {
        New-Item -ItemType Directory -Path ".\secrets" | Out-Null
    }
    
    Write-Host "Downloading key..." -ForegroundColor Yellow
    gcloud iam service-accounts keys create .\secrets\service-account.json --iam-account=$ServiceAccountEmail --project=$ProjectId
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: Key downloaded" -ForegroundColor Green
        $fullPath = (Resolve-Path .\secrets\service-account.json).Path
        Write-Host ""
        Write-Host "Set this variable:" -ForegroundColor Cyan
        Write-Host "`$env:GOOGLE_APPLICATION_CREDENTIALS = `"$fullPath`"" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next: .\Test-Local.ps1" -ForegroundColor Cyan