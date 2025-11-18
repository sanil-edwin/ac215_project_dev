# stress_detection/agriguard/api/main.py

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import fsspec
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agriguard.models.csi_features import (
    available_dates as csi_available_dates,
    get_csi_for_date,
    PATHS,
)
from agriguard.models.csi_partial import build_partial_features
from agriguard.models.csi_calibrator import CSICalibrator

# Optional: Gemini for RAG
try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None  # RAG endpoints will raise if called without key/model.


# -----------------------------------------------------------------------------
# Pydantic models
# -----------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str


class StressItem(BaseModel):
    fips: str
    date: str
    CSI: float
    category: str


class StressResponse(BaseModel):
    results: List[StressItem]
    note: Optional[str] = None


class DatesResponse(BaseModel):
    dates: List[str]


class CountyItem(BaseModel):
    fips: str
    county_name: str


class CountiesResponse(BaseModel):
    counties: List[CountyItem]


class StressProbPrediction(BaseModel):
    pred_yield_anom: float
    stress_prob: float


class StressProbResponse(BaseModel):
    fips: str
    date: str
    season_progress: float
    features_used: List[str]
    prediction: StressProbPrediction
    contributions: Dict[str, Dict[str, float]]
    explanation: str


class CalibratorRowResponse(BaseModel):
    fips: str
    date: str
    season_progress: float
    features: Dict[str, float]
    prediction: Optional[StressProbPrediction] = None
    explanation: Optional[str] = None


# RAG schemas ---------------------------------------------------------------

class RagIngestResponse(BaseModel):
    ingested: int
    docs_dir: str


class RagStatsResponse(BaseModel):
    num_docs: int
    doc_ids: List[str]


class RagChatRequest(BaseModel):
    message: str
    fips: Optional[str] = None
    date: Optional[str] = None
    top_k: int = 3


class RagChatResponse(BaseModel):
    answer: str
    used_docs: List[str]
    meta: Dict[str, Optional[str]]


# -----------------------------------------------------------------------------
# FastAPI app & CORS
# -----------------------------------------------------------------------------

app = FastAPI(
    title="AgriGuard Iowa Corn Stress API",
    description="CSI stress detection, yield calibration, and RAG agronomy assistant.",
    version="0.1.0",
)

# Normally you’d tighten this in prod; for MS4 it’s convenient to allow localhost UI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Model loading helpers
# -----------------------------------------------------------------------------

def _model_path() -> Path:
    env_path = os.environ.get("AG_MODEL_PATH")
    if env_path:
        return Path(env_path)
    # Fallback to package-relative
    here = Path(__file__).resolve()
    return here.parent.parent / "models" / "csi_calibrator.joblib"


@lru_cache(maxsize=1)
def _load_calibrator_bundle() -> Dict:
    path = _model_path()
    if not path.exists():
        raise RuntimeError(f"Calibrator joblib not found at {path}")
    bundle = joblib.load(path)
    # Expect either bare CSICalibrator or a dict {model, features, meta}
    if isinstance(bundle, CSICalibrator):
        return {"model": bundle, "features": getattr(bundle, "feature_names_", [])}
    if isinstance(bundle, dict) and "model" in bundle:
        return bundle
    raise RuntimeError(f"Unexpected calibrator object in {path}")


def _load_calibrator() -> CSICalibrator:
    return _load_calibrator_bundle()["model"]  # type: ignore[return-value]


def _calibrator_features() -> List[str]:
    feats = _load_calibrator_bundle().get("features")
    if isinstance(feats, list) and feats:
        return [str(f) for f in feats]
    # Fallback: default feature ordering
    return [
        "CSI_mean",
        "CSI_max",
        "CSI_AUC",
        "CSI_early_mean",
        "CSI_poll_mean",
        "CSI_grain_mean",
    ]


# -----------------------------------------------------------------------------
# County metadata
# -----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_ndvi_table_sample() -> pd.DataFrame:
    """
    Read a small sample of the NDVI parquet to get (fips, county_name).
    Uses the same PATHS['ndvi'] as the CSI computation.
    """
    path = PATHS["ndvi"]
    with fsspec.open(path, "rb") as f:
        df = pd.read_parquet(f, columns=["fips", "county_name"], engine="pyarrow")
    df = df.drop_duplicates(subset=["fips", "county_name"]).sort_values("fips")
    df["fips"] = df["fips"].astype(str).str.zfill(5)
    return df


@lru_cache(maxsize=1)
def _county_index() -> List[CountyItem]:
    df = _load_ndvi_table_sample()
    return [
        CountyItem(fips=row["fips"], county_name=row["county_name"])
        for _, row in df.iterrows()
    ]


# -----------------------------------------------------------------------------
# Dates: 2010–2025, based on remote-sensing coverage
# -----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _all_dates_iso() -> List[str]:
    """
    All composite dates available for CSI, in ISO 'YYYY-MM-DD' format.

    Under the hood this is driven by the MODIS/weather parquet coverage:
    2010-05-01 through ~2025-10-31, per data_raw_README.
    """
    dates = csi_available_dates()
    dates = sorted(dates)
    return [d.date().isoformat() for d in dates]


# -----------------------------------------------------------------------------
# Simple endpoints
# -----------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/dates", response_model=DatesResponse)
def list_dates() -> DatesResponse:
    """
    All composite dates where CSI can be computed (2010–2025).
    """
    return DatesResponse(dates=_all_dates_iso())


@app.get("/counties", response_model=CountiesResponse)
def list_counties() -> CountiesResponse:
    """
    Iowa counties with remote-sensing coverage.
    """
    return CountiesResponse(counties=_county_index())


# -----------------------------------------------------------------------------
# CSI snapshot endpoints
# -----------------------------------------------------------------------------

def _build_stress_items(df: pd.DataFrame) -> List[StressItem]:
    items: List[StressItem] = []
    for _, row in df.iterrows():
        try:
            items.append(
                StressItem(
                    fips=str(row["fips"]).zfill(5),
                    date=pd.to_datetime(row["date"]).date().isoformat(),
                    CSI=float(row["CSI"]),
                    category=str(row.get("category", "")),
                )
            )
        except Exception:
            # Skip malformed rows rather than fail whole request
            continue
    return items


@app.get("/stress", response_model=StressResponse)
def stress_snapshot(
    date: Optional[str] = Query(
        default=None,
        description="Target date (YYYY-MM-DD). If omitted, uses latest available composite date.",
    ),
    fips: Optional[List[str]] = Query(
        default=None,
        description="Optional list of county FIPS (comma-separated in query string).",
    ),
) -> StressResponse:
    if date is None:
        # Use latest available composite date
        dates = _all_dates_iso()
        if not dates:
            raise HTTPException(status_code=503, detail="No CSI dates available")
        date = dates[-1]

    try:
        df = get_csi_for_date(date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if fips:
        fset = {s.zfill(5) for s in fips}
        df = df[df["fips"].astype(str).str.zfill(5).isin(fset)]

    items = _build_stress_items(df)
    return StressResponse(
        results=items,
        note="CSI in [0,1]; higher means more stress (Iowa counties only).",
    )


@app.get("/stress/{fips}", response_model=StressResponse)
def stress_for_county(
    fips: str,
    date: str = Query(..., description="Target date (YYYY-MM-DD)."),
) -> StressResponse:
    try:
        df = get_csi_for_date(date, fips=fips)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    items = _build_stress_items(df)
    return StressResponse(
        results=items,
        note="CSI in [0,1]; higher means more stress (Iowa counties only).",
    )


# -----------------------------------------------------------------------------
# Model metrics
# -----------------------------------------------------------------------------

@app.get("/model/metrics")
def model_metrics():
    """
    Return a lightweight summary: CV metrics + active feature names.

    If a metrics JSON is present alongside the joblib, use it; otherwise
    report that it's missing (your Docker training step can write it).
    """
    bundle = _load_calibrator_bundle()
    features = _calibrator_features()

    joblib_path = _model_path()
    metrics_path = joblib_path.with_name(joblib_path.stem + "_metrics.json")

    if metrics_path.exists():
        try:
            metrics = json.loads(metrics_path.read_text())
        except Exception:
            metrics = {"note": f"Failed to read metrics JSON at {metrics_path}"}
    else:
        metrics = {"note": f"{metrics_path.name} not found. Run training to generate it."}

    return {"metrics": metrics, "features": features}


# -----------------------------------------------------------------------------
# Stress probability + yield anomaly
# -----------------------------------------------------------------------------

@app.get("/stress/prob", response_model=StressProbResponse)
def stress_probability(
    date: str = Query(..., description="Target date (YYYY-MM-DD)."),
    fips: str = Query(..., description="County FIPS, e.g., 19001."),
) -> StressProbResponse:
    feats, season_progress = build_partial_features(fips, date)

    if not feats:
        raise HTTPException(
            status_code=404,
            detail=f"No CSI features available for fips={fips}, date={date}",
        )

    model = _load_calibrator()
    feature_names = _calibrator_features()

    # Build row vector in model's feature order
    X = np.array([[feats.get(name, np.nan) for name in feature_names]], dtype=float)

    # Basic NaN guard
    if not np.isfinite(X).all():
        raise HTTPException(
            status_code=500,
            detail="Non-finite values in feature vector; check CSI / climatology.",
        )

    # Predictions
    pred_y = float(model.predict_yield_anom(X)[0])
    stress_prob = float(model.predict_stress_prob(X)[0])

    expl = (
        f"Features: {', '.join(feature_names)}. "
        f"Predicted anomaly {pred_y * 100:.2f}%; P(stress)={stress_prob:.2f}."
    )

    return StressProbResponse(
        fips=fips,
        date=date,
        season_progress=season_progress,
        features_used=feature_names,
        prediction=StressProbPrediction(
            pred_yield_anom=pred_y,
            stress_prob=stress_prob,
        ),
        contributions={"regression": {}, "classification_logit": {}},
        explanation=expl,
    )


# -----------------------------------------------------------------------------
# Debug endpoints
# -----------------------------------------------------------------------------

@app.get("/debug/features")
def debug_features(
    fips: str = Query(...),
    date: str = Query(...),
):
    """
    Raw partial-season CSI features + season progress, *before* calibration.
    Useful for sanity-checking that:
      - features vary across counties and dates,
      - high stress years (e.g., 2012) show higher CSI aggregates.
    """
    feats, season_progress = build_partial_features(fips, date)
    if not feats:
        raise HTTPException(
            status_code=404,
            detail=f"No CSI features available for fips={fips}, date={date}",
        )

    return {
        "fips": fips,
        "date": date,
        "features_expected": list(feats.keys()),
        "values": feats,
        "season_progress": season_progress,
    }


@app.get("/debug/calibrator_row", response_model=CalibratorRowResponse)
def debug_calibrator_row(
    fips: str = Query(...),
    date: str = Query(...),
):
    """
    Diagnostic endpoint: shows exactly what the calibrator sees for (fips, date).

    Returns:
      - season_progress
      - features (name -> value)
      - prediction (if calibrator is loaded)
    """
    feats, season_progress = build_partial_features(fips, date)
    if not feats:
        raise HTTPException(
            status_code=404,
            detail=f"No CSI features available for fips={fips}, date={date}",
        )

    feature_names = _calibrator_features()
    model = _load_calibrator()

    X = np.array([[feats.get(name, np.nan) for name in feature_names]], dtype=float)
    if not np.isfinite(X).all():
        # still return features for inspection; just skip prediction
        return CalibratorRowResponse(
            fips=fips,
            date=date,
            season_progress=season_progress,
            features=feats,
            prediction=None,
            explanation="Non-finite values in feature vector; check CSI and climatology.",
        )

    pred_y = float(model.predict_yield_anom(X)[0])
    stress_prob = float(model.predict_stress_prob(X)[0])

    expl = (
        f"Using features: {', '.join(feature_names)}. "
        f"Predicted anomaly {pred_y * 100:.2f}%; P(stress)={stress_prob:.2f}."
    )

    return CalibratorRowResponse(
        fips=fips,
        date=date,
        season_progress=season_progress,
        features={name: float(feats.get(name, np.nan)) for name in feature_names},
        prediction=StressProbPrediction(
            pred_yield_anom=pred_y,
            stress_prob=stress_prob,
        ),
        explanation=expl,
    )


# -----------------------------------------------------------------------------
# Simple RAG over PDFs using Gemini
# -----------------------------------------------------------------------------

RAG_ROOT = Path(os.environ.get("AG_RAG_ROOT", "/app/rag_store")).resolve()
RAG_DOCS_DIR = RAG_ROOT / "docs"
RAG_INDEX_FILE = RAG_ROOT / "index.npy"
RAG_META_FILE = RAG_ROOT / "meta.json"

EMBED_MODEL_ID = os.environ.get("GEMINI_EMBED_MODEL_ID", "text-embedding-004")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-1.5-flash")


def _ensure_rag_dirs() -> None:
    RAG_ROOT.mkdir(parents=True, exist_ok=True)
    RAG_DOCS_DIR.mkdir(parents=True, exist_ok=True)


def _config_gemini():
    if genai is None:
        raise RuntimeError("google.generativeai is not installed in this image.")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set in the environment.")
    genai.configure(api_key=api_key)


def _load_rag_index():
    _ensure_rag_dirs()
    if not RAG_INDEX_FILE.exists() or not RAG_META_FILE.exists():
        return np.zeros((0, 768)), []  # empty index
    vecs = np.load(RAG_INDEX_FILE)
    meta = json.loads(RAG_META_FILE.read_text())
    return vecs, meta


def _save_rag_index(vecs: np.ndarray, meta: List[Dict]):
    _ensure_rag_dirs()
    np.save(RAG_INDEX_FILE, vecs)
    RAG_META_FILE.write_text(json.dumps(meta, indent=2))


@app.get("/rag/health")
def rag_health():
    return {
        "status": "ok",
        "component": "rag",
        "docs_dir": str(RAG_DOCS_DIR),
    }


@app.get("/rag/stats", response_model=RagStatsResponse)
def rag_stats():
    vecs, meta = _load_rag_index()
    return RagStatsResponse(
        num_docs=len(meta),
        doc_ids=[m.get("doc_id", f"chunk_{i}") for i, m in enumerate(meta)],
    )


@app.post("/rag/ingest", response_model=RagIngestResponse)
async def rag_ingest(files: List[UploadFile] = File(...)):
    """
    Ingest 1+ PDF files into a simple local vector store:
      - Extract text with PyPDF2.
      - Chunk into ~800-1000 char segments.
      - Embed with Gemini text-embedding-004.
      - Save vectors + metadata under /app/rag_store.
    """
    import uuid
    from PyPDF2 import PdfReader  # type: ignore

    _config_gemini()
    _ensure_rag_dirs()

    vecs_old, meta_old = _load_rag_index()
    new_vecs = []
    new_meta = []

    for up in files:
        raw = await up.read()
        reader = PdfReader(BytesIO(raw))

        # Simple page-level chunks
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            doc_id = str(uuid.uuid4())
            # Embed
            emb = genai.embed_content(
                model=EMBED_MODEL_ID,
                content=text,
            )["embedding"]["values"]
            new_vecs.append(emb)
            new_meta.append(
                {
                    "doc_id": doc_id,
                    "filename": up.filename,
                    "page": i,
                    "text": text,
                }
            )

    if new_vecs:
        arr_new = np.array(new_vecs, dtype=float)
        if vecs_old.size == 0:
            vecs_all = arr_new
            meta_all = new_meta
        else:
            vecs_all = np.vstack([vecs_old, arr_new])
            meta_all = meta_old + new_meta

        _save_rag_index(vecs_all, meta_all)

    return RagIngestResponse(ingested=len(new_meta), docs_dir=str(RAG_DOCS_DIR))


from io import BytesIO  # placed here to avoid circular import issues above


@app.post("/rag/chat", response_model=RagChatResponse)
async def rag_chat(req: RagChatRequest):
    """
    RAG chat:
      - Embed the query.
      - Retrieve top_k chunks from the local vector store.
      - Ask Gemini to answer, including:
          * retrieved agronomy text
          * optional stress probability summary from /stress/prob
    """
    _config_gemini()
    vecs, meta = _load_rag_index()
    if len(meta) == 0 or vecs.size == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested yet. POST to /rag/ingest first.",
        )

    # 1. Embed query
    query_text = req.message
    q_emb = genai.embed_content(
        model=EMBED_MODEL_ID,
        content=query_text,
    )["embedding"]["values"]
    q = np.array(q_emb, dtype=float)

    # 2. Cosine similarity retrieval
    norms = np.linalg.norm(vecs, axis=1) * np.linalg.norm(q)
    sims = (vecs @ q) / np.where(norms == 0, 1e-8, norms)
    top_k = max(1, min(req.top_k or 3, len(meta)))
    idx = np.argsort(-sims)[:top_k]

    context_chunks = [meta[i]["text"] for i in idx]
    used_ids = [meta[i].get("doc_id", f"chunk_{i}") for i in idx]

    # Optional: fetch stress prob summary for this county/date to feed to Gemini
    stress_summary = ""
    if req.fips and req.date:
        try:
            resp = stress_probability(date=req.date, fips=req.fips)
            stress_summary = (
                f"Model outputs for FIPS {req.fips} on {req.date}: "
                f"predicted yield anomaly = {resp.prediction.pred_yield_anom*100:.1f}%, "
                f"stress probability = {resp.prediction.stress_prob:.2f}."
            )
        except Exception:
            stress_summary = ""

    # 3. Call Gemini for answer
    full_prompt = (
        "You are an agronomy assistant helping corn farmers in Iowa.\n"
        "You are given:\n"
        "- Retrieved expert text about drought-stressed corn (from PDFs).\n"
        "- Optional model outputs (CSI-based stress probability and yield anomaly).\n\n"
        "User question:\n"
        f"{req.message}\n\n"
        "Context from guidance documents:\n"
        + "\n\n---\n\n".join(context_chunks)
    )

    if stress_summary:
        full_prompt += "\n\nModel summary:\n" + stress_summary

    model = genai.GenerativeModel(GEMINI_MODEL_ID)
    try:
        resp = model.generate_content(full_prompt)
        answer = resp.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {e}")

    return RagChatResponse(
        answer=answer,
        used_docs=used_ids,
        meta={
            "fips": req.fips,
            "date": req.date,
            "top_k": str(top_k),
        },
    )

