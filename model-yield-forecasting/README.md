# AgriGuard - Yield Forecasting Model
by AgriGuard Team - AC215 Fall 2025 - Binh Vu, Sanil Edwin, Moody Farra, Artem Biriukov

Rolling window corn yield forecasting for Iowa counties using multi-sensor satellite data fusion.

## 🌟 Features

- **Any-Date Predictions**: Forecast yield for any date from May 1 to September 30
- **Multi-Sensor Fusion**: Combines MODIS ET, LST, NDVI, and EVI satellite data
- **Progressive Accuracy**: Uncertainty decreases from ±17 to ±11 bu/acre as season progresses
- **Interactive Interface**: User-friendly menu system for county-level predictions
- **Production Ready**: Containerized with Docker, versioned with DVC, deployed on GCP

## 📊 Model Performance

- **Algorithm**: XGBoost Regressor (Rolling Window)
- **RMSE**: ~10-11 bu/acre
- **R²**: 0.82-0.87
- **Training Data**: 5,696 samples (8 years × 8 forecast dates × 99 counties)
- **Features**: 130 (temporal, ET, LST, NDVI, EVI, combined)

## 🛰️ Data Sources

| Source         | Description                            | Resolution    | Use Case                               |
|----------------|----------------------------------------|---------------|----------------------------------------|
| **MODIS ET**   | Evapotranspiration                     | 500m, 8-day   | Water stress detection                 |
| **MODIS LST**  | Land Surface Temperature               | 1km, daily    | Heat stress detection                  |
| **MODIS NDVI** | Normalized Difference Vegetation Index |  500m, 16-day | Early season vegetation                |
| **MODIS EVI**  | Enhanced Vegetation Index              | 500m, 16-day  | Dense canopy (reproductive/grain fill) |
| **USDA NASS**  | Historical yields                      | County-level  | Training targets                       |

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- GCP credentials in `../secrets/gcp-key.json`

### Build Container
```bash
docker-compose build
docker-compose run --rm yield-forecasting bash -c "\
  python scripts/1_prepare_features.py && \
  python scripts/2_train_models.py && \
  python scripts/3_evaluate_models.py && \
  python scripts/4_predict_current_year.py"
```

### Interactive Forecasting
```bash
docker-compose run --rm yield-forecasting python scripts/interactive_forecast.py
```

## 📁 Project Structure

```
model-yield-forecasting/
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
├── .dockerignore              # Docker build exclusions
├── .gitignore                 # Git exclusions
├── Makefile                   # Convenience commands
├── scripts/
│   ├── 1_prepare_features.py        # Feature engineering (130 features)
│   ├── 2_train_models.py            # XGBoost training with CV
│   ├── 3_evaluate_models.py         # Performance evaluation
│   ├── 4_predict_current_year.py    # 2025 predictions
│   └── interactive_forecast.py      # User interface
└── utils/
    ├── data_loader.py               # GCS data loading (ET, LST, NDVI, EVI)
    ├── feature_engineering.py       # Rolling window feature creation
    └── __init__.py                  # Package marker
```

## 🎯 Usage Examples

### 1. Generate Features
```bash
docker-compose run --rm yield-forecasting python scripts/1_prepare_features.py
```
Creates 130 features from ET, LST, NDVI, and EVI data for 8 forecast dates per year.

### 2. Train Model
```bash
docker-compose run --rm yield-forecasting python scripts/2_train_models.py
```
Trains XGBoost with 5-fold cross-validation grouped by county.

### 3. Evaluate Performance
```bash
docker-compose run --rm yield-forecasting python scripts/3_evaluate_models.py
```
Generates performance metrics and visualization charts.

### 4. Make Predictions
```bash
docker-compose run --rm yield-forecasting python scripts/4_predict_current_year.py
```
Generates 2025 yield forecasts for all 99 Iowa counties.

### 5. Interactive Forecasting
```bash
docker-compose run --rm yield-forecasting python scripts/interactive_forecast.py
```
Menu-driven interface for county-specific, date-specific predictions.

## 📊 Outputs

All outputs saved to `gs://agriguard-ac215-data/model_yield_forecasting/`:

```
model_yield_forecasting/
├── features/                          # Engineered features
│   ├── rolling_window_training_features_ndvi_evi.parquet
│   └── feature_info_ndvi_evi.json
├── models/                            # Trained models
│   ├── rolling_window_model_ndvi_evi.joblib
│   ├── rolling_window_scaler_ndvi_evi.joblib
│   ├── rolling_window_features_ndvi_evi.json
│   ├── feature_importance_ndvi_evi.csv
│   └── training_metrics_ndvi_evi.json
├── evaluation/                        # Performance analysis
│   ├── model_performance.png
│   ├── feature_categories.png
│   └── evaluation_summary.txt
└── predictions/                       # 2025 forecasts
    ├── predictions_2025_ndvi_evi.parquet
    ├── predictions_2025_ndvi_evi.csv
    └── predictions_2025_summary_ndvi_evi.txt
```

## 🔧 Model Details

### Feature Categories (130 total)

- **Temporal (24)**: days_since_may1, data_completeness, week, month, etc.
- **ET-based (39)**: Water stress indicators, deficits, trends
- **LST-based (37)**: Heat stress days, temperature extremes
- **NDVI-based (30)**: Early season vegetation health, greenness
- **EVI-based (30)**: Dense canopy health, peak timing
- **Combined (5)**: NDVI/EVI ratios, peak timing differences

### Model Architecture
```
XGBoost Regressor
├── n_estimators: 300
├── learning_rate: 0.03
├── max_depth: 6
├── regularization: L1=0.1, L2=1.0
└── validation: 5-fold GroupKFold (by county)
```

## 🌽 Iowa Counties Covered

All 99 Iowa corn-producing counties, including:

- Story County (FIPS 19169) - Ames
- Polk County (FIPS 19153) - Des Moines
- Linn County (FIPS 19113) - Cedar Rapids
- Johnson County (FIPS 19103) - Iowa City
- And 95 more...

## 📈 Performance by Season

| Forecast Date | Data Available | Uncertainty | Confidence  | Use Case             |
|---------------|----------------|-------------|-------------|----------------------|
| June 15       | 30%            | ±17 bu/acre | LOW         | Early warning        |
| July 15       | 49%            | ±14 bu/acre | MEDIUM-LOW  | Planning             |
| July 31       | 59%            | ±13 bu/acre | MEDIUM      | Mid-season decisions |
| August 31     | 80%            | ±12 bu/acre | MEDIUM-HIGH | Insurance decisions  |
| September 30  | 100%           | ±11 bu/acre | HIGH        | Pre-harvest estimate |

## 🔬 Scientific Innovation

### Multi-Sensor Fusion Strategy

- **Water Stress (ET)**: Tracks soil moisture and crop water use
- **Heat Stress (LST)**: Monitors temperature extremes during critical growth stages
- **Early Vegetation (NDVI)**: Tracks emergence and early vegetative growth
- **Dense Canopy (EVI)**: Monitors reproductive and grain fill stages

### Growth Stage Adaptation

- **Planting (May)**: NDVI tracks emergence
- **Vegetative (June-July)**: NDVI tracks canopy development
- **Reproductive (July 15-Aug 15)**: EVI critical for silking/pollination
- **Grain Fill (Aug 15-Sept 30)**: EVI tracks maturity

## 🆚 Comparison with Existing Solutions

| Feature                    | OneSoil   | DataFarming  | Bayer FieldView  | AgriGuard                 |
|----------------------------|-----------|--------------|------------------|---------------------------|
| Multi-sensor               | NDVI only | NDVI only    | NDVI + machinery | ET+LST+NDVI+EVI           |
| Any-date forecasting       | ❌        | ❌          | ❌               | ✅                       |
| Explainability             | Limited   | Limited      | Limited          | Driver cards + confidence |
| Open source                | ❌        | ❌          | ❌               | ✅                       |
| Uncertainty quantification | ❌        | ❌          | ❌               | ✅                       |