import os
from typing import List, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: waiting for Artem to confirm prediction endpoint URL and schema
YIELD_PREDICTION_API_URL = os.getenv("YIELD_PREDICTION_API_URL")


class CountyMetrics(BaseModel):
    id: str
    name: str
    ndvi: float
    soil_moisture: float
    stress_index: float


class TrendPoint(BaseModel):
    date: str
    stress_index: float


class ChatRequest(BaseModel):
    question: str
    county_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str


class QueryTransformRequest(BaseModel):
    question: str
    county_id: Optional[str] = None


class QueryTransformResponse(BaseModel):
    intent: Literal["metrics", "yield_forecast", "general_chat"]
    expanded_query: str


class EmbeddingRequest(BaseModel):
    queries: List[str]


class EmbeddingVector(BaseModel):
    values: List[float]


class EmbeddingBatchResponse(BaseModel):
    vectors: List[EmbeddingVector]


class YieldForecastRequest(BaseModel):
    county_id: str
    as_of_date: Optional[str] = None


class YieldForecastResponse(BaseModel):
    county_id: str
    as_of_date: Optional[str]
    predicted_yield: float
    lower_ci: Optional[float] = None
    upper_ci: Optional[float] = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/county-metrics", response_model=CountyMetrics)
def get_county_metrics(county_id: str):
    if county_id == "19015":
        name = "Boone County"
    elif county_id == "19017":
        name = "Bremer County"
    else:
        name = f"County {county_id}"

    return CountyMetrics(
        id=county_id,
        name=name,
        ndvi=0.72,
        soil_moisture=0.43,
        stress_index=0.18,
    )


@app.get("/api/county-trend", response_model=List[TrendPoint])
def get_county_trend(county_id: str):
    return [
        TrendPoint(date="2024-07-01", stress_index=0.25),
        TrendPoint(date="2024-07-08", stress_index=0.22),
        TrendPoint(date="2024-07-15", stress_index=0.18),
    ]


@app.post("/api/query/transform", response_model=QueryTransformResponse)
def transform_query(req: QueryTransformRequest):
    q_lower = req.question.lower()

    if "yield" in q_lower or "production" in q_lower:
        intent = "yield_forecast"
    elif any(word in q_lower for word in ["stress", "ndvi", "soil", "moisture"]):
        intent = "metrics"
    else:
        intent = "general_chat"

    context_parts: List[str] = []
    if req.county_id:
        context_parts.append(f"county FIPS {req.county_id} in Iowa")
    context_parts.append("Iowa corn fields")
    context_parts.append("current growing season")

    expanded_query = req.question + " | context: " + "; ".join(context_parts)

    return QueryTransformResponse(intent=intent, expanded_query=expanded_query)


@app.post("/api/query/embeddings", response_model=EmbeddingBatchResponse)
def get_query_embeddings(req: EmbeddingRequest):
    vectors: List[EmbeddingVector] = []

    for query in req.queries:
        length_feature = float(len(query))
        dummy_values = [
            length_feature,
            1.0 if "yield" in query.lower() else 0.0,
            1.0 if "stress" in query.lower() else 0.0,
            1.0 if "ndvi" in query.lower() else 0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]
        vectors.append(EmbeddingVector(values=dummy_values))

    return EmbeddingBatchResponse(vectors=vectors)


@app.post("/api/yield-forecast", response_model=YieldForecastResponse)
async def get_yield_forecast(req: YieldForecastRequest):
    if not YIELD_PREDICTION_API_URL:
        raise HTTPException(
            status_code=500,
            detail="YIELD_PREDICTION_API_URL not configured in environment.",
        )

    payload = {
        "county_id": req.county_id,
        "as_of_date": req.as_of_date,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(YIELD_PREDICTION_API_URL, json=payload)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error contacting yield prediction service: {e}",
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Yield prediction service error: {resp.text}",
        )

    data = resp.json()

    predicted = (
        data.get("predicted_yield")
        or data.get("predicted_yield_bu_acre")
        or data.get("yield")
    )
    if predicted is None:
        raise HTTPException(
            status_code=500,
            detail="Yield prediction service did not return a 'predicted_yield' field.",
        )

    return YieldForecastResponse(
        county_id=data.get("county_id", req.county_id),
        as_of_date=data.get("as_of_date", req.as_of_date),
        predicted_yield=float(predicted),
        lower_ci=data.get("lower_ci") or data.get("ci_lower"),
        upper_ci=data.get("upper_ci") or data.get("ci_upper"),
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    transform = transform_query(
        QueryTransformRequest(
            question=req.question,
            county_id=req.county_id,
        )
    )

    if transform.intent == "metrics":
        if not req.county_id:
            answer = (
                "I can summarize stress metrics if you tell me which county. "
                "Try asking, for example: 'What is the stress level in Boone County (19015)?'"
            )
            return ChatResponse(answer=answer)

        metrics = get_county_metrics(county_id=req.county_id)
        trend = get_county_trend(county_id=req.county_id)

        latest = trend[-1] if trend else None
        trend_phrase = ""
        if latest:
            trend_phrase = (
                f" Recent trend shows stress index at {latest.stress_index:.2f} "
                f"as of {latest.date}."
            )

        answer = (
            f"For {metrics.name} (FIPS {metrics.id}), the current NDVI is {metrics.ndvi:.2f}, "
            f"soil moisture is {metrics.soil_moisture:.2f}, and the composite stress index "
            f"is {metrics.stress_index:.2f}.{trend_phrase}"
        )
        return ChatResponse(answer=answer)

    if transform.intent == "yield_forecast":
        if not req.county_id:
            answer = (
                "I can provide a yield forecast if you include a county_id in your question. "
                "For example: 'What is the expected yield for county 19015?'"
            )
            return ChatResponse(answer=answer)

        yf = await get_yield_forecast(
            YieldForecastRequest(
                county_id=req.county_id,
                as_of_date=None,
            )
        )

        ci_part = ""
        if yf.lower_ci is not None and yf.upper_ci is not None:
            ci_part = (
                f" A {yf.lower_ci:.1f}–{yf.upper_ci:.1f} bu/acre interval "
                "captures most likely outcomes."
            )

        answer = (
            f"The current expected yield for county {yf.county_id} is "
            f"{yf.predicted_yield:.1f} bushels per acre.{ci_part}"
        )
        return ChatResponse(answer=answer)

    return ChatResponse(
        answer=(
            "Right now I specialize in crop stress metrics and yield forecasts. "
            "Try asking about NDVI, soil moisture, stress, or yield for a specific Iowa county."
        )
    )
