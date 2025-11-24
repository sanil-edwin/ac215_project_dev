# ==========================================
# COPY THIS ENTIRE FILE AND SAVE AS Deploy-CloudRun.ps1
# ==========================================

# Deploy yield downloader to Google Cloud Run as a Job
# Cloud Run Jobs are ideal for batch processing tasks like data downloads

param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$ImageName = "yield-downloader",
    [string]$Version = "latest",
    [string]$Region = "us-central1",
    [string]$JobName = "yield-downloader",
    [string]$NassApiKey = $env:NASS_API_KEY
)

if (-not $ProjectId) {
    $ProjectId = "agriguard-ac215"
}

if (-not $NassApiKey) {
    Write-Host "ERROR: NASS_API_KEY not set!" -ForegroundColor Red
    Write-Host "Get your free API key at: https://quickstats.nass.usda.gov/api" -ForegroundColor Yellow
    Write-Host "`nSet it with:`n  `$env:NASS_API_KEY = 'your_key_here'" -ForegroundColor Yellow
    exit 1
}

$ServiceAccount = "yield-downloader@$ProjectId.iam.gserviceaccount.com"
$FullImageName = "gcr.io/$ProjectId/$ImageName`:$Version"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Deploying to Google Cloud Run Job" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Job: $JobName"
Write-Host "Image: $FullImageName"
Write-Host "======================================"

# Check if job already exists
$null = gcloud run jobs describe $JobName --region=$Region --project=$ProjectId 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nUpdating existing Cloud Run Job..." -ForegroundColor Yellow
    gcloud run jobs update $JobName `
        --image=$FullImageName `
        --region=$Region `
        --project=$ProjectId `
        --set-env-vars="GCS_BUCKET_NAME=agriguard-ac215-data,START_YEAR=2010,NASS_API_KEY=$NassApiKey" `
        --memory=2Gi `
        --cpu=1 `
        --max-retries=1 `
        --task-timeout=1800 `
        --service-account=$ServiceAccount
}
else {
    Write-Host "`nCreating new Cloud Run Job..." -ForegroundColor Yellow
    gcloud run jobs create $JobName `
        --image=$FullImageName `
        --region=$Region `
        --project=$ProjectId `
        --set-env-vars="GCS_BUCKET_NAME=agriguard-ac215-data,START_YEAR=2010,NASS_API_KEY=$NassApiKey" `
        --memory=2Gi `
        --cpu=1 `
        --max-retries=1 `
        --task-timeout=1800 `
        --service-account=$ServiceAccount
}

Write-Host "`n✓ Deployment complete!" -ForegroundColor Green

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "1. Run the job:"
Write-Host "   gcloud run jobs execute $JobName --region=$Region`n"
Write-Host "2. Check job status:"
Write-Host "   gcloud run jobs executions list --job=$JobName --region=$Region`n"
Write-Host "3. View logs:"
Write-Host "   .\scripts\View-Status.ps1 logs`n"
Write-Host "4. Schedule with Cloud Scheduler (optional):"
Write-Host "   gcloud scheduler jobs create http yield-downloader-schedule \"
Write-Host "     --location=$Region \"
Write-Host "     --schedule='0 0 1 * *' \"
Write-Host "     --uri='https://$Region-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$ProjectId/jobs/$JobName`:run' \"
Write-Host "     --http-method=POST \"
Write-Host "     --oauth-service-account-email=$ServiceAccount"
Write-Host "======================================"
