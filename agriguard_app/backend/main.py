from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Literal, Optional

app = FastAPI()

# CORS – allow frontend (React dev server) to call this API

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-only; can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for county metrics + trends

class CountyMetrics(BaseModel):
    id: str
    name: str
    ndvi: float
    soil_moisture: float
    stress_index: float


class TrendPoint(BaseModel):
    date: str
    stress_index: float


# Models for chat

class ChatRequest(BaseModel):
    question: str
    county_id: Optional[str] = None  # to support county-specific questions later


class ChatResponse(BaseModel):
    answer: str


# Models for query transformation (intent + expansion)

class QueryTransformRequest(BaseModel):
    question: str
    county_id: Optional[str] = None


class QueryTransformResponse(BaseModel):
    intent: Literal["metrics", "yield_forecast", "general_chat"]
    expanded_query: str


# Models for batched query embeddings (stub)

class EmbeddingRequest(BaseModel):
    queries: List[str]


class EmbeddingVector(BaseModel):
    values: List[float]


class EmbeddingBatchResponse(BaseModel):
    vectors: List[EmbeddingVector]


# Health check

@app.get("/api/health")
def health():
    return {"status": "ok"}


# County metrics + trends

@app.get("/api/county-metrics", response_model=CountyMetrics)
def get_county_metrics(county_id: str):
    # For now, return simple fake data; later can plug real data here.
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
    # Simple fixed trend; later can fetch from time-series store
    return [
        TrendPoint(date="2024-07-01", stress_index=0.25),
        TrendPoint(date="2024-07-08", stress_index=0.22),
        TrendPoint(date="2024-07-15", stress_index=0.18),
    ]


# Query transformation: intent classification + query expansion (stub)

@app.post("/api/query/transform", response_model=QueryTransformResponse)
def transform_query(req: QueryTransformRequest):
    q_lower = req.question.lower()

    # Very simple heuristic intent classification for now
    if "yield" in q_lower or "production" in q_lower:
        intent = "yield_forecast"
    elif any(word in q_lower for word in ["stress", "ndvi", "soil", "moisture"]):
        intent = "metrics"
    else:
        intent = "general_chat"

    # Naive context expansion; later this can be replaced by an LLM
    context_parts = []
    if req.county_id:
        context_parts.append(f"county FIPS {req.county_id} in Iowa")
    context_parts.append("Iowa corn fields")
    context_parts.append("current growing season")

    expanded_query = req.question + " | context: " + "; ".join(context_parts)

    return QueryTransformResponse(intent=intent, expanded_query=expanded_query)


# Batched query embeddings (stub)

@app.post("/api/query/embeddings", response_model=EmbeddingBatchResponse)
def get_query_embeddings(req: EmbeddingRequest):
    """
    Stub endpoint to demonstrate batched embeddings.

    Later, you can replace the dummy vectors with real embeddings
    from Vertex AI, OpenAI, or a local model. The important thing
    for Milestone 4 is:
      - This endpoint accepts a *batch* of queries.
      - It returns a list of vectors (one per query).
    """
    vectors: List[EmbeddingVector] = []

    # For now, we just return small fixed-length dummy vectors.
    for query in req.queries:
        # Example: encode length and a simple "hash" into the vector
        length_feature = float(len(query))
        # Very silly features, just to show shape
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


# Chat endpoint – currently rule-based, later can call RAG/LLM

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Simple placeholder chat endpoint.

    Later, we can:
      - Call /api/query/transform internally,
      - Use /api/query/embeddings to retrieve from your vector store,
      - Then pass context + question to an LLM.
    """
    q = req.question.lower()

    if "stress" in q:
        answer = (
            "Current stress indicators are mild to moderate based on recent NDVI trends."
        )
    elif "yield" in q:
        answer = "Expected yield is near the county average given current conditions."
    else:
        answer = "This is a placeholder answer. In the future this will use our RAG pipeline."

    return ChatResponse(answer=answer)
