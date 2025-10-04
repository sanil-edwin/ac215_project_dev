# AgriGuard - Multi-Sensor Crop Stress Detection for Iowa Corn

**AC215/E115 Course Project - Harvard University**

## Project Overview

Agricultural producers and insurance companies need accurate, timely information about crop health and expected yields. AgriGuard addresses this by:

1. **Stress Detection (Unsupervised):** Identifies anomalous crop patterns indicating stress
2. **Yield Forecasting (Supervised):** Predicts corn yields 2-3 months before harvest

## Important Note: Synthetic Satellite Features 

**For Milestone 2, we use synthetic remote sensing data.** The preprocessing container generates simulated satellite features (NDVI, SAR, ET) that correlate with actual yields but are not real satellite imagery.

Real satellite downloads from Sentinel-2, Sentinel-1, and MODIS will be implemented in Milestone 2. The current synthetic features demonstrate the ML pipeline architecture and prove the containerized workflow functions correctly.

**What this means:**
- Container 2 generates realistic but simulated satellite features
- Models train successfully but show limited performance (Test R² = 0.01)
- With real Sentinel imagery, we expect R² > 0.70 based on literature

## Architecture

┌─────────────────┐
│  Container 1    │  Data Ingestion
│  USDA NASS API  │  Downloads Iowa corn yields (2015-2024)
└────────┬────────┘
         │ iowa_corn_yields_2015_2024.csv (1,162 records)
         ↓
┌─────────────────┐
│  Container 2    │  Preprocessing & Feature Engineering
│  Preprocessing  │  Creates ML features from yields + synthetic satellite
└────────┬────────┘
         │ train/val/test.parquet
         ↓
    ┌────┴────┐
    │         │
┌───▼──┐   ┌──▼────┐
│ C3   │   │ C4    │
│Stress│   │Yield  │
│Model │   │Model  │
└──────┘   └───────┘
Autoencoder XGBoost
(Anomaly)   (Regressor)


## Containers

### Container 1: Data Ingestion
- Downloads Iowa corn yield data from USDA NASS
- Output: 1,162 county-year records (2015-2024)

### Container 2: Preprocessing
- Feature engineering for ML models
- Creates historical yields + synthetic satellite features

### Container 3: Stress Detection
- Unsupervised anomaly detection using Autoencoder

### Container 4: Yield Forecasting
- XGBoost regression model predicts yields in bu/acre

## Project Structure

agriguard/
├── data-ingestion/              # Container 1
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── docker-shell.ps1
│   ├── src/
│   └── configs/
├── data-preprocessing/          # Container 2
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── docker-shell.ps1
│   ├── src/
│   └── configs/
├── model-stress-detection/      # Container 3
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── docker-shell.ps1
│   ├── src/
│   └── configs/
├── model-yield-forecasting/     # Container 4
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── docker-shell.ps1
│   ├── src/
│   └── configs/
└── data/                        # Generated (not in Git)
    ├── raw/
    ├── processed/
    └── models/


## Quick Start

Prerequisites: Docker Desktop, PowerShell, USDA NASS API Key

Run each container in sequence following instructions in individual container folders.

## Dataset

- Source: USDA NASS QuickStats API
- Geographic Scope: Iowa (101 counties)
- Crop: Corn
- Time Period: 2015-2024
- Records: 1,162 county-year observations

## Technology Stack

- Containers: Docker
- Language: Python 3.11
- ML Frameworks: TensorFlow, XGBoost, scikit-learn

## Team

BINH VU, SANIL EDWIN, MOODY FARRA, ARTEM BIRIUKOV
Harvard AC215/E115 Fall 2025