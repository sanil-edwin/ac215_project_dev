from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import json

# Mount point from docker compose
DATA = Path("/app/data")

# Folders (some may not exist yet if those steps aren’t implemented)
SUMMARIES = DATA / "summaries"          
DRIVERS = DATA / "drivers"                    # e.g., data/drivers/County_Year.json

# UPDATED to match your current pipeline outputs:
STRESS_MODELS = DATA / "models" / "stress_detector"     
YIELD_MODELS  = DATA / "models" / "yield_forecaster"    

app = FastAPI(title="AgriGuard API", version="0.1.0")

class InferenceRequest(BaseModel):
    state: str = "IOWA"
    county: str
    year: int

def latest(path: Path, pattern: str):
    files = sorted(path.glob(pattern))
    return files[-1] if files else None

# Keep your health endpoint
@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "data_dir_exists": DATA.exists(),
        "stress_model_present": STRESS_MODELS.exists(),
        "yield_model_present": YIELD_MODELS.exists(),
    }

# Add a lightweight /status (handy for dashboards/uptime checks)
@app.get("/status")
def status() -> Dict[str, Any]:
    return {
        "models": {
            "stress_detector": STRESS_MODELS.exists(),
            "yield_forecaster": YIELD_MODELS.exists(),
        },
        "processed_available": (DATA / "processed").exists(),
        "summaries_available": SUMMARIES.exists(),
        "drivers_available": DRIVERS.exists(),
    }

@app.get("/summaries/counties")
def county_summaries(limit: int = Query(5, ge=1, le=500)):
    """
    Returns a small sample from the latest county summaries parquet.
    Note: This will 503 until the workflow writes data/summaries/*county_summaries.parquet
    """
    f = latest(SUMMARIES, "**/*county_summaries.parquet")
    if not f:
        raise HTTPException(503, "No county summaries yet. Run the pipeline first.")
    df = pd.read_parquet(f)
    return {"file": str(f), "rows": len(df), "sample": df.head(limit).to_dict(orient="records")}

@app.get("/drivers/{county}")
def driver_card(county: str, year: int | None = None):
    """
    Returns the most recent driver card JSON for a county (optionally a specific year).
    Note: This will 503 until the workflow writes data/drivers/<County>_<Year>.json
    """
    pattern = f"{county}_{year or '*'}*.json"
    candidates = list(DRIVERS.glob(pattern))
    if not candidates:
        raise HTTPException(503, "No driver card available yet.")
    with open(sorted(candidates)[-1]) as fh:
        return json.load(fh)

# Minimal stubs for predict endpoints (wire real models later)
@app.post("/predict/stress")
def predict_stress(req: InferenceRequest):
    score = (hash((req.state.upper(), req.county.upper(), req.year)) % 100) / 100.0
    return {"county": req.county, "year": req.year, "stress_score": round(score, 3)}

@app.post("/predict/yield")
def predict_yield(req: InferenceRequest):
    base = 175.0
    adj = (hash((req.county.upper(), req.year)) % 31) - 15
    return {"county": req.county, "year": req.year, "predicted_yield_bu_per_acre": base + adj}
