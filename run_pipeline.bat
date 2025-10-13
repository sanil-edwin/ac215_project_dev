@echo off
setlocal enabledelayedexpansion

echo === Ingestion ===
docker compose run --rm data-ingestion python src/download_yield_data.py --start-year 2015 --end-year 2024 --sample
if errorlevel 1 goto :err

echo === Preprocessing ===
docker compose run --rm data-preprocessing python src/preprocess_data.py
if errorlevel 1 goto :err

echo === Stress model ===
docker compose run --rm model-stress-detection python src/train_model.py --save /app/data/models/stress --write-summaries /app/data/summaries --write-drivers /app/data/drivers
if errorlevel 1 goto :err

echo === Yield model ===
docker compose run --rm model-yield-forecasting python src/train_model.py --save /app/data/models/yield
if errorlevel 1 goto :err

echo === DONE ===
exit /b 0

:err
echo *** FAILED with errorlevel %errorlevel% ***
exit /b %errorlevel%
