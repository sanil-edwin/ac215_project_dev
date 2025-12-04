# Build Docker image for yield downloader
# This script builds and optionally pushes to Google Container Registry

param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$ImageName = "yield-downloader",
    [string]$Version = "latest",
    [string]$Region = "us-central1"
)

if (-not $ProjectId) {
    $ProjectId = "agriguard-ac215"
}

# Full image name
$FullImageName = "gcr.io/$ProjectId/$ImageName`:$Version"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Building Yield Downloader Container" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Project ID: $ProjectId"
Write-Host "Image: $FullImageName"
Write-Host "======================================"

# Build the Docker image
Write-Host "`nBuilding Docker image..." -ForegroundColor Yellow
docker build -t "$ImageName`:$Version" .
docker tag "$ImageName`:$Version" $FullImageName

Write-Host "`n✓ Build complete: $FullImageName" -ForegroundColor Green

# Ask if user wants to push to GCR
$response = Read-Host "`nPush to Google Container Registry? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "`nPushing to GCR..." -ForegroundColor Yellow
    docker push $FullImageName
    Write-Host "✓ Image pushed to GCR" -ForegroundColor Green
    
    Write-Host "`n======================================" -ForegroundColor Cyan
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "1. Deploy to Cloud Run:"
    Write-Host "   .\scripts\Deploy-CloudRun.ps1`n"
    Write-Host "2. Or run manually:"
    Write-Host "   gcloud run jobs create yield-downloader \"
    Write-Host "     --image $FullImageName \"
    Write-Host "     --region $Region \"
    Write-Host "     --service-account yield-downloader@$ProjectId.iam.gserviceaccount.com"
}

Write-Host "`n✓ Build script complete" -ForegroundColor Green
