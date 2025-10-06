from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import json

DATA = Path("/app/data")
SUMMARIES = DATA / "summaries"
DRIVERS = DATA / "drivers"
STRESS_MODELS = DATA / "models" / "stress"
YIELD_MODELS  = DATA / "models" / "yield"

app = FastAPI(title="AgriGuard API (MS2 minimal)")

class InferenceRequest(BaseModel):
    state: str = "IOWA"
    county: str
    year: int

def latest(path: Path, pattern: str):
    files = sorted(path.glob(pattern))
    return files[-1] if files else None

@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "data_dir_exists": DATA.exists(),
        "stress_model_present": STRESS_MODELS.exists(),
        "yield_model_present": YIELD_MODELS.exists(),
    }

@app.get("/summaries/counties")
def county_summaries(limit: int = Query(5, ge=1, le=500)):
    f = latest(SUMMARIES, "**/*county_summaries.parquet")
    if not f:
        raise HTTPException(503, "No county summaries yet. Run the pipeline first.")
    df = pd.read_parquet(f)
    return {"file": str(f), "rows": len(df), "sample": df.head(limit).to_dict(orient="records")}

@app.get("/drivers/{county}")
def driver_card(county: str, year: int | None = None):
    candidates = list(DRIVERS.glob(f"{county}_{year or '*'}*.json"))
    if not candidates:
        raise HTTPException(503, "No driver card available yet.")
    with open(sorted(candidates)[-1]) as fh:
        return json.load(fh)

@app.post("/predict/stress")
def predict_stress(req: InferenceRequest):
    # Minimal deterministic stub until a real model is wired in
    score = (hash((req.state.upper(), req.county.upper(), req.year)) % 100) / 100.0
    return {"county": req.county, "year": req.year, "stress_score": round(score, 3)}

@app.post("/predict/yield")
def predict_yield(req: InferenceRequest):
    # Minimal deterministic stub; replace with real model output later
    base = 175.0
    adj = (hash((req.county.upper(), req.year)) % 31) - 15
    return {"county": req.county, "year": req.year, "predicted_yield_bu_per_acre": base + adj}
