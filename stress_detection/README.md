# AgriGuard — Iowa Corn Stress Detection & Yield Forecast (Milestone 4)

**Iowa-only.** All endpoints and data access are constrained to **Iowa counties** (FIPS prefix `19`).

## Models (supervised calibration, annual)
Two interpretable models trained on **annual** county yields:

1) **Yield anomaly regression (Elastic Net)**  
   Features: `CSI_mean, CSI_max, CSI_AUC, CSI_early_mean, CSI_poll_mean, CSI_grain_mean`  
   Target: relative anomaly `(yield - county_mean)/county_mean`  
   Expectation: higher CSI → more negative anomaly.

2) **Stress-year classifier (Logistic)**  
   Label: `stress_year = 1 if y_anom <= -0.15 else 0`  
   Output: `P(stress_year)`.

**Cross-val metrics**: ROC-AUC, Brier score (see `agriguard/models/csi_calibrator_metrics.json` after training).

## Real-time usage (partial season)
At date `t` within year `y`, the API builds **partial-season** features up to `t` and applies the trained models:
- `/stress` → CSI for that date
- `/stress/prob` or `/forecast` → predicted yield anomaly and stress-year probability

## Quickstart
```bash
docker build -t agriguard:latest .
docker run --rm -p 8000:8000 agriguard:latest
# http://localhost:8000/docs
```

## Train the calibrator (offline)
If you mounted data (GCS or local mirror) and want to retrain:
```bash
docker run --rm -e AG_BUCKET_ROOT=gs://agriguard-ac215-data -e AG_DATA_PREFIX=data_raw agriguard:latest   python -m agriguard.models.train_calibrator
```
This writes:
- `agriguard/models/csi_calibrator.joblib` (elastic-net + logistic pipelines)
- `agriguard/models/csi_calibrator_metrics.json` (ROC-AUC, Brier, N, prevalence)

## Endpoints
- `GET /health`
- `GET /dates`
- `GET /counties`
- `GET /stress?date=YYYY-MM-DD&fips=19xxx,19yyy`
- `GET /stress/prob?date=YYYY-MM-DD&fips=19xxx`
- `GET /forecast?date=YYYY-MM-DD&fips=19xxx`

## Dev
```bash
make format && make lint && make test
```
