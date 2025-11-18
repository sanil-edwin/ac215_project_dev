# Build and push Docker container to Google Container Registry

param(
    [string]$ProjectId = "agriguard-ac215",
    [string]$ImageName = "mask-downloader",
    [string]$Version = "latest",
    [string]$Region = "us-central1"
)

# Use proper string concatenation to avoid colon parsing issues
$FullImageName = "gcr.io/" + $ProjectId + "/" + $ImageName + ":" + $Version

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Building Mask Downloader Container" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Project ID: $ProjectId"
Write-Host "  Image: $FullImageName"
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "âœ" Docker is running" -ForegroundColor Green
} catch {
    Write-Host "âœ— Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Build the Docker image
Write-Host ""
Write-Host "Building Docker image..." -ForegroundColor Yellow
Write-Host "  (This may take several minutes)" -ForegroundColor Gray
Write-Host ""

docker build -t "${ImageName}:${Version}" .

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "âœ— Build failed" -ForegroundColor Red
    exit 1
}

# Tag for GCR
docker tag "${ImageName}:${Version}" $FullImageName

Write-Host ""
Write-Host "âœ" Build complete: $FullImageName" -ForegroundColor Green

# Ask to push to GCR
Write-Host ""
Write-Host "Push to Google Container Registry? (Y/N)" -ForegroundColor Yellow
$response = Read-Host

if ($response -eq 'Y' -or $response -eq 'y') {
    Write-Host ""
    Write-Host "Configuring Docker for GCR..." -ForegroundColor Yellow
    gcloud auth configure-docker --quiet
    
    Write-Host "Pushing to GCR..." -ForegroundColor Yellow
    Write-Host "  (This may take several minutes)" -ForegroundColor Gray
    Write-Host ""
    
    docker push $FullImageName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "âœ" Image pushed to GCR" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "======================================" -ForegroundColor Green
        Write-Host "Next Steps:" -ForegroundColor Green
        Write-Host "======================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "1. Deploy to Cloud Run:" -ForegroundColor Cyan
        Write-Host "   .\scripts\Deploy-CloudRun.ps1" -ForegroundColor White
        Write-Host ""
        Write-Host "2. Or run manually:" -ForegroundColor Cyan
        Write-Host "   gcloud run jobs create mask-downloader ``" -ForegroundColor White
        Write-Host "     --image $FullImageName ``" -ForegroundColor White
        Write-Host "     --region $Region ``" -ForegroundColor White
        Write-Host "     --service-account mask-downloader@${ProjectId}.iam.gserviceaccount.com" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "âœ— Failed to push image" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "âœ" Build script complete" -ForegroundColor Green
