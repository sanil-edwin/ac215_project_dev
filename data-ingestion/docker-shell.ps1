# AgriGuard Data Ingestion Docker Shell

param(
    [Parameter(Position=0)]
    [string]$Command,
    
    [Parameter(Position=1, ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$IMAGE_NAME = "agriquard-data-ingestion:1.0.0"
$BASE_DIR = Get-Location
$SECRETS_DIR = Join-Path $BASE_DIR "..\secrets"
$DATA_DIR = Join-Path $BASE_DIR "..\data"

Write-Host "====================================================" -ForegroundColor Green
Write-Host "AgriGuard Data Ingestion Container" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host "Image: $IMAGE_NAME" -ForegroundColor White
Write-Host ""

switch ($Command) {
    "build" {
        Write-Host "Building Docker image..." -ForegroundColor Yellow
        docker build -t $IMAGE_NAME .
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n? Build successful!" -ForegroundColor Green
            docker images $IMAGE_NAME
        } else {
            Write-Host "`n? Build failed!" -ForegroundColor Red
        }
    }
    
    "run" {
        Write-Host "Running container..." -ForegroundColor Yellow
        
        # Create directories
        @($SECRETS_DIR, $DATA_DIR) | ForEach-Object {
            if (-not (Test-Path $_)) {
                New-Item -ItemType Directory -Path $_ -Force | Out-Null
            }
        }
        
        $GCS_BUCKET = if ($env:GCS_BUCKET) { $env:GCS_BUCKET } else { "agriguard-ac215-data" }
        $API_KEY = if ($env:USDA_NASS_API_KEY) { $env:USDA_NASS_API_KEY } else { "" }
        
        docker run --rm -it `
            --name agriquard-ingestion `
            -v "$($BASE_DIR)\src:/app/src" `
            -v "$($BASE_DIR)\configs:/app/configs" `
            -v "${SECRETS_DIR}:/app/secrets:ro" `
            -v "${DATA_DIR}:/app/data" `
            -e GCS_BUCKET=$GCS_BUCKET `
            -e USDA_NASS_API_KEY=$API_KEY `
            $IMAGE_NAME @Arguments
    }
    
    "shell" {
        Write-Host "Starting interactive shell..." -ForegroundColor Yellow
        
        docker run --rm -it `
            --name agriquard-shell `
            -v "$($BASE_DIR)\src:/app/src" `
            -v "$($BASE_DIR)\configs:/app/configs" `
            -v "${SECRETS_DIR}:/app/secrets:ro" `
            -v "${DATA_DIR}:/app/data" `
            $IMAGE_NAME /bin/bash
    }
    
    "clean" {
        Write-Host "Cleaning up..." -ForegroundColor Yellow
        docker rmi $IMAGE_NAME -f
        Write-Host "? Cleaned" -ForegroundColor Green
    }
    
    default {
        Write-Host "Usage:" -ForegroundColor Yellow
        Write-Host "  .\docker-shell.ps1 build                - Build image"
        Write-Host "  .\docker-shell.ps1 run [command]        - Run command"
        Write-Host "  .\docker-shell.ps1 shell                - Interactive shell"
        Write-Host "  .\docker-shell.ps1 clean                - Remove image"
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Yellow
        Write-Host "  .\docker-shell.ps1 run python src/download_yield_data.py --sample --verbose"
        Write-Host "  .\docker-shell.ps1 run python src/download_yield_data.py --start-year 2020 --end-year 2024"
    }
}
