# AgriGuard Preprocessing Container - Interactive Shell (PowerShell)
$ErrorActionPreference = "Stop"

$IMAGE_NAME = "agriguard-preprocessing"
$CONTAINER_NAME = "agriguard-preprocessing-shell"

if (-not (Test-Path "secrets")) {
    Write-Host "Error: secrets/ directory not found" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "secrets/gcp-key.json")) {
    Write-Host "Error: secrets/gcp-key.json not found" -ForegroundColor Red
    exit 1
}

$imageExists = docker images -q $IMAGE_NAME 2>$null
if (-not $imageExists) {
    Write-Host "Image not found. Building $IMAGE_NAME..." -ForegroundColor Yellow
    docker build -t $IMAGE_NAME .
}

$env:GCS_BUCKET_NAME = if ($env:GCS_BUCKET_NAME) { $env:GCS_BUCKET_NAME } else { "agriguard-ac215-data" }
$env:GCP_PROJECT_ID = if ($env:GCP_PROJECT_ID) { $env:GCP_PROJECT_ID } else { "agriguard-ac215" }
$env:YEAR = if ($env:YEAR) { $env:YEAR } else { "2025" }

Write-Host "Starting interactive shell for $IMAGE_NAME" -ForegroundColor Green
Write-Host "Environment:"
Write-Host "  - GCS_BUCKET_NAME: $($env:GCS_BUCKET_NAME)"
Write-Host "  - GCP_PROJECT_ID: $($env:GCP_PROJECT_ID)"
Write-Host "  - YEAR: $($env:YEAR)"
Write-Host ""

docker run --rm -it `
    --name $CONTAINER_NAME `
    -v "${PWD}/secrets:/secrets:ro" `
    -v "${PWD}/src:/app/src" `
    -v "${PWD}/config:/app/config" `
    -v "${PWD}/logs:/app/logs" `
    -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json `
    -e GCS_BUCKET_NAME=$env:GCS_BUCKET_NAME `
    -e GCP_PROJECT_ID=$env:GCP_PROJECT_ID `
    -e YEAR=$env:YEAR `
    $IMAGE_NAME `
    /bin/bash

Write-Host "Shell session ended" -ForegroundColor Green
