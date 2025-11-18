# Deploy mask downloader to Google Cloud Run as a Job
# Updated to use Artifact Registry instead of GCR

param(
    [string]$ProjectId = "agriguard-ac215",
    [string]$ImageName = "mask-downloader",
    [string]$Version = "latest",
    [string]$Region = "us-central1",
    [string]$JobName = "mask-downloader",
    [string]$BucketName = "agriguard-ac215-data",
    [string]$StartYear = "2010"
)

# Use Artifact Registry path (not GCR)
$FullImageName = "us-central1-docker.pkg.dev/" + $ProjectId + "/" + $ImageName + "/" + $ImageName + ":" + $Version
$ServiceAccount = $JobName + "@" + $ProjectId + ".iam.gserviceaccount.com"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Deploying to Google Cloud Run Job" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Project: $ProjectId"
Write-Host "  Region: $Region"
Write-Host "  Job: $JobName"
Write-Host "  Image: $FullImageName"
Write-Host "  Service Account: $ServiceAccount"
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if job already exists
Write-Host "Checking if job exists..." -ForegroundColor Yellow
$jobExists = gcloud run jobs describe $JobName --region=$Region --project=$ProjectId 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Updating existing Cloud Run Job..." -ForegroundColor Yellow
    
    gcloud run jobs update $JobName `
        --image=$FullImageName `
        --region=$Region `
        --project=$ProjectId `
        --set-env-vars="GCS_BUCKET_NAME=$BucketName,START_YEAR=$StartYear,GCP_PROJECT_ID=$ProjectId" `
        --memory=4Gi `
        --cpu=2 `
        --max-retries=1 `
        --task-timeout=3600 `
        --service-account=$ServiceAccount
        
} else {
    Write-Host "Creating new Cloud Run Job..." -ForegroundColor Yellow
    
    gcloud run jobs create $JobName `
        --image=$FullImageName `
        --region=$Region `
        --project=$ProjectId `
        --set-env-vars="GCS_BUCKET_NAME=$BucketName,START_YEAR=$StartYear,GCP_PROJECT_ID=$ProjectId" `
        --memory=4Gi `
        --cpu=2 `
        --max-retries=1 `
        --task-timeout=3600 `
        --service-account=$ServiceAccount
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "? Deployment complete!" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "======================================" -ForegroundColor Green
    Write-Host "Next Steps:" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Run the job:" -ForegroundColor Cyan
    Write-Host "   gcloud run jobs execute $JobName --region=$Region" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Monitor execution:" -ForegroundColor Cyan
    Write-Host "   .\scripts\View-Status.ps1 logs" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Verify data in GCS:" -ForegroundColor Cyan
    Write-Host "   gsutil ls gs://$BucketName/data_raw/masks/corn/" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "? Deployment failed" -ForegroundColor Red
    exit 1
}
