param([Parameter(Position=0)][string]$Command, [Parameter(Position=1, ValueFromRemainingArguments=$true)][string[]]$Arguments)

$IMAGE_NAME = "agriquard-preprocessing:1.0.0"
$BASE_DIR = Get-Location
$DATA_DIR = Join-Path $BASE_DIR "..\data"

Write-Host "AgriGuard Data Preprocessing" -ForegroundColor Green

switch ($Command) {
    "build" {
        Write-Host "Building..." -ForegroundColor Yellow
        docker build -t $IMAGE_NAME .
        if ($LASTEXITCODE -eq 0) { Write-Host "`nBuild successful!" -ForegroundColor Green }
    }
    "run" {
        docker run --rm -it --name agriquard-preprocessing -v "$($BASE_DIR)\src:/app/src" -v "$($BASE_DIR)\configs:/app/configs" -v "${DATA_DIR}:/app/data" $IMAGE_NAME @Arguments
    }
    "shell" {
        docker run --rm -it --name agriquard-preprocessing-shell -v "$($BASE_DIR)\src:/app/src" -v "$($BASE_DIR)\configs:/app/configs" -v "${DATA_DIR}:/app/data" $IMAGE_NAME /bin/bash
    }
    default {
        Write-Host "Usage: .\docker-shell.ps1 build | run [cmd] | shell"
    }
}
