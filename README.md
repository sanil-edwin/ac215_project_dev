# AgriGuard - Multi-Sensor Crop Stress Detection for Iowa Corn

**Harvard AC215/E115 Fall 2025**

**Team:** Binh Vu, Sanil Edwin, Moody Farra, Artem Biriukov

---

## Table of Contents

- [Project Vision](#project-vision)
  - [Full System Components](#full-system-components)
  - [Differentiation](#differentiation)
- [Current Implementation Status](#current-implementation-status)
  - [Milestone 2 (Current)](#-milestone-2-oct-16---current-stage)
  - [Milestone 3 (In Progress)](#-milestone-3-oct-28---in-progress)
  - [Milestone 4 (Planned)](#-milestone-4-nov-25---planned)
  - [Milestone 5 (Planned)](#-milestone-5-dec-11---planned)
- [System Architecture](#system-architecture)
- [Containers (MS2)](#containers-ms2---current)
  - [Container 1: Data Ingestion](#container-1-data-ingestion)
  - [Container 2: Preprocessing](#container-2-preprocessing--feature-engineering)
  - [Container 3: Stress Detection](#container-3-stress-detection-unsupervised)
  - [Container 4: Yield Forecasting](#container-4-yield-forecasting-supervised)
- [Getting Started](#getting-started)
- [Dataset](#dataset)
- [Model Performance](#model-performance)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Development Roadmap](#development-roadmap)
- [References](#references)
- [License](#license)

---

## Project Vision

AgriGuard is a cloud-deployed system that combines multi-sensor remote sensing (Sentinel-2 NDVI, Sentinel-1 SAR, MODIS ET) to deliver:

1. **Early-warning crop stress alerts** - Detect drought, disease, and pest stress before visible damage
2. **Yield forecasting** - Predict corn yields 2-3 months before harvest with confidence intervals
3. **Explainable insights** - Understand why stress is occurring and what yields are expected

Serving Iowa corn producers, insurers, and policymakers with real-time, transparent, and actionable intelligence.

### Full System Components

1. **Multi-sensor stress detection** - Fuse Sentinel-2 NDVI + Sentinel-1 SAR + MODIS ET with Iowa-specific baselines
2. **Explainable AI** - Driver cards showing attribution (drought vs. disease), confidence bands, SHAP values
3. **RAG-based Q&A assistant** - Natural language queries grounded in agronomy documents ("Which counties are most stressed and why?")
4. **Web dashboard** - Interactive maps, county panels, time-series charts, PDF export
5. **Yield forecasting** - LSTM/XGBoost models with uncertainty quantification
6. **Price analysis** (stretch) - USDA WASDE reports + CME futures integration

### Differentiation

- **All-weather detection**: SAR penetrates clouds when optical fails
- **Multi-sensor fusion**: Reduces false alarms vs. NDVI-only
- **Explainability**: Driver cards + confidence bands + Iowa baselines
- **Open pipelines**: Auditable MLOps, not black-box commercial
- **RAG assistant**: Cited answers from agronomy literature

---

## Current Implementation Status

**This README reflects the full project vision. The system is being built incrementally across course milestones (MS2-MS5). Each milestone adds capability toward the complete system.**

### ✅ Milestone 2 (Oct 16) - CURRENT STAGE

**Status:** Containerized ML pipeline with synthetic satellite features

**What's Built:**
- ✅ Container 1: Data Ingestion (USDA NASS API)
- ✅ Container 2: Preprocessing & Feature Engineering
- ✅ Container 3: Stress Detection (Autoencoder)
- ✅ Container 4: Yield Forecasting (XGBoost)
- ✅ Docker containerization
- ✅ Version control (Git)
- ✅ Documentation (README, TESTING.md)

**Current Capabilities:**
- Download 1,162 Iowa corn yield records (2015-2024)
- Generate ML features (historical lags + synthetic satellite)
- Train autoencoder for anomaly detection (~5% stress rate)
- Train XGBoost for yield prediction
- Export trained models and predictions

**Current Limitations (Temporary):**
- Uses synthetic satellite features (not real Sentinel/MODIS imagery)
- No web dashboard (command-line only)
- No API deployment
- No explainability features
- Limited to proof-of-concept scale

**Why Synthetic Features Now?**  
MS2 focuses on proving the containerized workflow architecture. Synthetic features (simulated NDVI, SAR, ET) correlate with actual yields and enable model training while we build satellite download infrastructure for MS3.

**Performance (MS2 baseline):**
- Stress Detection: 5.1% anomaly rate
- Yield Forecasting: Test RMSE 84 bu/acre, R² = 0.01

Expected improvement to R² > 0.70 when real satellite data is integrated (MS3).

---

### 🚧 Milestone 3 (Oct 28) - IN PROGRESS

**Planned:**
- [ ] Real satellite downloads via Google Earth Engine
  - [ ] Sentinel-2: NDVI/EVI (10m optical)
  - [ ] Sentinel-1: VV/VH backscatter (10m SAR)
  - [ ] MODIS: MOD16A2 ET anomalies (500m)
- [ ] FastAPI service for model inference
- [ ] Initial web UI (maps + county dashboards)
- [ ] Driver cards showing stress attribution
- [ ] RAG prototype (document retrieval + Q&A)

---

### 📅 Milestone 4 (Nov 25) - PLANNED

**Planned:**
- [ ] Full web dashboard with interactive maps
- [ ] Distributed processing (Dask/Prefect) for <2hr statewide refresh
- [ ] CI/CD pipelines with monitoring
- [ ] Workflow orchestration (Vertex AI Pipelines)
- [ ] Confidence bands and uncertainty quantification
- [ ] LLM fine-tuning (LoRA for agronomy domain)

---

### 📅 Milestone 5 (Dec 11) - PLANNED

**Planned:**
- [ ] Production deployment on GCP
- [ ] Complete RAG assistant with cited sources
- [ ] PDF export functionality  
- [ ] SHAP explainability for yield predictions
- [ ] Stretch: LSTM yield forecasting
- [ ] Stretch: Price analysis (USDA WASDE + CME futures)

---

## System Architecture

### Current Architecture (MS2)
**MS2 Containerized Pipeline:**

- **Data Ingestion (Container 1)**
  - USDA NASS QuickStats API
  - Downloads Iowa corn yields 2015-2024
  - Outputs: `iowa_corn_yields_2015_2024.csv` (1,162 records)

- **Preprocessing (Container 2)**
  - Inputs: Raw yield CSV
  - Creates historical lag features (1-3 years)
  - Generates synthetic satellite features (NDVI, SAR, ET, GDD, stress indicators)
  - Splits into train (2015-2021), val (2022), test (2023-2024)
  - Outputs: Two Parquet datasets (stress_features, yield_features)

- **Model Training (Containers 3 & 4 - parallel)**
  - **Container 3: Stress Detection**
    - Autoencoder (15→10→5→10→15)
    - Anomaly detection via reconstruction error
    - Outputs: `autoencoder_model.keras`, threshold, stress scores
  
  - **Container 4: Yield Forecasting**
    - XGBoost regression (200 trees)
    - Predicts yields in bu/acre
    - Outputs: `xgboost_model.json`, predictions, feature importance

### Target Architecture (MS3-MS5)

**Full Production System:**

- **Layer 1: Data Collection**
  - Satellite data via Google Earth Engine (Sentinel-2 NDVI, Sentinel-1 SAR)
  - Climate data via MODIS (ET anomalies)
  - Weather APIs (temperature, precipitation)

- **Layer 2: Feature Engineering**
  - Multi-sensor fusion combining optical + SAR + climate
  - Iowa-specific baseline calibration
  - Temporal aggregation (daily → weekly → seasonal)
  - Anomaly detection rules

- **Layer 3: ML Models**
  - Stress detection → Stress probability maps
  - Yield forecasting → County-level yield predictions with confidence intervals
  - Price analysis (optional) → Market impact estimates

- **Layer 4: Application Services**
  - FastAPI: REST endpoints for predictions
  - RAG Assistant: Q&A with document retrieval + LLM
  - Web Dashboard: Interactive maps, county panels, time-series charts
  - Export: PDF briefs for decision-making
 
## Containers (MS2 - Current)

### Container 1: Data Ingestion

Downloads historical yield data from USDA NASS QuickStats API.

**Input:**
- USDA NASS API key
- Year range (2015-2024)
- State filter (Iowa)

**Output:**
- CSV with 1,162 county-year records
- Columns: year, county, state, commodity_desc, yield_bu_per_acre

**Run:**
```bash
cd data-ingestion
.\docker-shell.ps1 build
.\docker-shell.ps1 run python src/download_yield_data.py --start-year 2015 --end-year 2024
```


### Container 2: Preprocessing & Feature Engineering

Transforms raw yields into ML-ready features.

**Processing**

1. **Historical lags**: Previous 1-3 years yields per county

2. **Synthetic satellite features** (MS2 temporary):
   - NDVI: Early/mid/late season vegetation indices
   - SAR: Soil moisture proxies (VV/VH polarization)
   - ET: Evapotranspiration totals and anomalies
   - GDD: Growing degree days
   - Stress indicators: Day count and severity

3. **Two feature sets**:
   - `stress_features/`: For unsupervised (no yield labels)
   - `yield_features/`: For supervised (with yield target)

4. **Temporal split**: Train (2015-2021), Val (2022), Test (2023-2024)

**Output**

- Parquet datasets: `data/processed/{stress,yield}_features/{train,val,test}.parquet`

**Run**
```bash
cd data-preprocessing
.\docker-shell.ps1 run python src/preprocess_data.py
```

### Container 3: Stress Detection (Unsupervised)

Autoencoder for anomaly detection identifying stressed crops.

**Model**

- Architecture: 15 → 10 → 5 → 10 → 15
- Loss: MSE (reconstruction error)
- Anomaly: 95th percentile threshold

**Output**

- Model: `autoencoder_model.keras`
- Per-sample stress scores
- Anomaly flags (5.1% of samples)

**Run**
```bash
cd model-stress-detection
.\docker-shell.ps1 run python src/train_model.py
```

### Container 4: Yield Forecasting (Supervised)

XGBoost regression predicting yields in bushels/acre.

**Model**

- 200 trees, max_depth=6, lr=0.05
- Early stopping on validation RMSE

**Output**

- Model: `xgboost_model.json`
- Predictions CSVs
- Feature importance rankings

**Performance (MS2)**

- Test RMSE: 84 bu/acre
- Test R²: 0.01 (baseline with synthetic features)

**Run**
```bash
cd model-yield-forecasting
.\docker-shell.ps1 run python src/train_model.py
```








## Testing Instructions

### Prerequisites
- Docker Desktop installed and running
- Git installed
- PowerShell (Windows) or Bash (Linux/Mac)
- USDA NASS API Key (get free at https://quickstats.nass.usda.gov/api)

### Steps
1.Clone repository: 
(powershell)
git clone https://github.com/sanil-edwin/ac215_project_dev.git
cd ac215_project_dev

(bash)
git clone https://github.com/sanil-edwin/ac215_project_dev.git
cd ac215_project_dev

2.Set API key: 
(powershell)
$env:USDA_NASS_API_KEY = "YOUR-API-KEY"

(bash)
export USDA_NASS_API_KEY="YOUR-API-KEY"

3. Make scripts executable (bash only):
find . -name "docker-shell.sh" -exec chmod +x {} \;
   
4. Pipiline test 
(powershell)
# Container 1: Download dataset
cd data-ingestion
.\docker-shell.ps1 run python src/download_yield_data.py --start-year 2015 --end-year 2024 --skip-upload

# Container 2: Preprocess
cd ..\data-preprocessing
.\docker-shell.ps1 run python src/preprocess_data.py

# Container 3: Train stress model
cd ..\model-stress-detection
.\docker-shell.ps1 run python src/train_model.py

# Container 4: Train yield model
cd ..\model-yield-forecasting
.\docker-shell.ps1 run python src/train_model.py

(bash)
# Container 1: Download dataset
cd data-ingestion
./docker-shell.sh run python src/download_yield_data.py --start-year 2015 --end-year 2024 --skip-upload

# Container 2: Preprocess
cd ../data-preprocessing
./docker-shell.sh run python src/preprocess_data.py

# Container 3: Train stress model
cd ../model-stress-detection
./docker-shell.sh run python src/train_model.py

# Container 4: Train yield model
cd ../model-yield-forecasting
./docker-shell.sh run python src/train_model.py


