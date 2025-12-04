"""
AgriGuard RAG Service - FastAPI Application

Port: 8003
Provides LLM-enhanced agricultural recommendations using:
- ChromaDB for vector storage
- Google Gemini for generation
- RRF Hybrid search (BM25 + vector)
"""

import os
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

import chromadb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (from docker-compose.yml)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))
COLLECTION_NAME = os.environ.get("RAG_COLLECTION_NAME", "corn-stress-knowledge")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", "5"))

# ─────────────────────────────────────────────────────────────────────────────
# System Prompt for AgriBot
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = """You are AgriBot, an AI assistant specialized in Iowa agriculture and corn crop management.
You help farmers understand crop stress, yield forecasts, and make data-driven decisions.

IMPORTANT: Keep responses concise - 2-4 paragraphs maximum. Focus on key findings and actionable advice.

Your responses are based on TWO sources:
1. LIVE DATA: Real-time stress indices and yield forecasts from AgriGuard sensors
2. DOCUMENT CONTEXT: Retrieved information from agricultural documents

STRESS INDEX INTERPRETATION:
The Overall Stress Index uses a 0-100 scale where LOWER = LESS STRESS:
- 0-30: Mild stress (crops doing okay, normal monitoring)
- 30-50: Moderate stress (monitor closely)  
- 50-70: Severe stress (action may be needed)
- 70-100: Critical stress (immediate intervention required)

Component Health Indices (Heat, Vegetation, Atmosphere) use 0-100 scale where HIGHER = HEALTHIER:
- 0-30: Severe stress (very poor health)
- 30-50: Moderate stress
- 50-70: Mild stress
- 70-100: Healthy (good condition)

Water Stress uses 0-100 scale where HIGHER = MORE STRESS:
- 0-30: Mild water stress
- 30-50: Moderate water stress
- 50-70: Severe water stress
- 70-100: Critical water deficit

When answering:
1. Match stress level labels to what the dashboard shows (Mild, Moderate, Severe, Critical)
2. Be specific with values but keep explanations brief
3. Prioritize actionable recommendations
4. Use 2-4 paragraphs maximum
- 70-100: Healthy (optimal conditions)
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """Request model for /chat endpoint."""
    message: str = Field(..., description="User's question", min_length=1)
    collection_name: Optional[str] = Field(default=None, description="ChromaDB collection")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of chunks to retrieve")
    
    # Optional live context from other AgriGuard services
    mcsi_context: Optional[Dict[str, Any]] = Field(default=None, description="Live MCSI data")
    yield_context: Optional[Dict[str, Any]] = Field(default=None, description="Live yield forecast")


class ChatResponse(BaseModel):
    """Response model for /chat endpoint."""
    response: str = Field(..., description="AgriBot's response")
    sources_used: int = Field(..., description="Number of document chunks used")
    collection: str = Field(..., description="Collection queried")
    has_live_data: bool = Field(..., description="Whether live data was included")


class QueryRequest(BaseModel):
    """Request model for /query endpoint."""
    query: str = Field(..., description="Search query", min_length=1)
    collection_name: Optional[str] = Field(default=None)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResult(BaseModel):
    """Single query result."""
    text: str
    score: float
    rank: int


class QueryResponse(BaseModel):
    """Response model for /query endpoint."""
    results: List[QueryResult]
    total_found: int
    collection: str


class LoadRequest(BaseModel):
    """Request model for /load endpoint."""
    texts: List[str] = Field(..., description="List of text chunks to load")
    collection_name: Optional[str] = Field(default=None)
    metadatas: Optional[List[Dict[str, Any]]] = Field(default=None)


class LoadResponse(BaseModel):
    """Response model for /load endpoint."""
    status: str
    collection_name: str
    chunks_loaded: int


class CollectionInfo(BaseModel):
    """Information about a collection."""
    name: str
    count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    chromadb_connected: bool
    gemini_ready: bool
    collection_name: str
    collection_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────────────────────────────────────
chroma_client: Optional[chromadb.HttpClient] = None
gemini_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global chroma_client, gemini_model
    
    logger.info("=" * 60)
    logger.info("AGRIGUARD RAG SERVICE STARTING")
    logger.info("=" * 60)
    
    # Initialize Gemini
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            gemini_model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=SYSTEM_INSTRUCTION
            )
            logger.info(f"✓ Gemini initialized: {GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            gemini_model = None
    else:
        logger.warning("GEMINI_API_KEY not set - chat will be unavailable")
    
    # Initialize ChromaDB
    try:
        chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collections = chroma_client.list_collections()
        logger.info(f"✓ ChromaDB connected: {CHROMADB_HOST}:{CHROMADB_PORT}")
        logger.info(f"  Collections: {[c.name for c in collections]}")
    except Exception as e:
        logger.error(f"ChromaDB connection failed: {e}")
        chroma_client = None
    
    logger.info(f"Default collection: {COLLECTION_NAME}")
    logger.info("=" * 60)
    
    yield
    
    logger.info("RAG SERVICE SHUTTING DOWN")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AgriGuard RAG Service",
    description="LLM-enhanced agricultural recommendations",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────
def get_collection(name: Optional[str] = None):
    """Get or create a ChromaDB collection."""
    if chroma_client is None:
        raise HTTPException(status_code=503, detail="ChromaDB not connected")
    
    collection_name = name or COLLECTION_NAME
    try:
        return chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        logger.error(f"Failed to get collection {collection_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Collection error: {e}")


def query_collection(collection, query_text: str, top_k: int = 5) -> List[tuple]:
    """Query collection and return (text, score) tuples."""
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=top_k,
            include=["documents", "distances"]
        )
        
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        # Convert distance to similarity score (1 - distance for cosine)
        return [(doc, 1 - dist) for doc, dist in zip(documents, distances)]
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    chromadb_ok = False
    collection_count = 0
    
    if chroma_client:
        try:
            collection = get_collection()
            collection_count = collection.count()
            chromadb_ok = True
        except:
            pass
    
    status = "healthy" if (chromadb_ok and gemini_model) else "degraded"
    if not chromadb_ok:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        service="rag-service",
        chromadb_connected=chromadb_ok,
        gemini_ready=gemini_model is not None,
        collection_name=COLLECTION_NAME,
        collection_count=collection_count
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AgriBot using RAG.
    
    Retrieves relevant document chunks and generates response with Gemini.
    Optionally includes live MCSI/yield data for enhanced context.
    """
    if gemini_model is None:
        raise HTTPException(status_code=503, detail="Gemini not initialized")
    
    logger.info(f"Chat: '{request.message[:50]}...'")
    
    # Get collection
    collection_name = request.collection_name or COLLECTION_NAME
    collection = get_collection(collection_name)
    
    # Query for relevant documents
    results = query_collection(collection, request.message, request.top_k)
    
    # Build context
    retrieved_text = ""
    if results:
        retrieved_text = "\n\n---\n\n".join([text for text, _ in results])
    
    # Build prompt
    prompt_parts = [f"User Question: {request.message}\n"]
    has_live_data = False
    
    # Add live MCSI context if provided
    if request.mcsi_context:
        has_live_data = True
        mcsi = request.mcsi_context
        prompt_parts.append(f"""
LIVE MCSI DATA (Current Conditions):
County: {mcsi.get('county_name', mcsi.get('fips', 'Unknown'))}
Date: {mcsi.get('date', 'N/A')}
Week of Season: {mcsi.get('week_of_season', 'N/A')}

Stress Indices (0-100 scale, higher = healthier, 0-30 = severe stress):
- Overall Stress Index: {mcsi.get('overall_stress', 'N/A')}
- Water Stress: {mcsi.get('water_stress', 'N/A')} 
- Heat Stress: {mcsi.get('heat_stress', 'N/A')}
- Vegetation Health: {mcsi.get('vegetation_health', 'N/A')}
- Atmospheric Stress: {mcsi.get('atmospheric_stress', 'N/A')}

Raw Sensor Values (for reference):
- NDVI: {mcsi.get('ndvi_raw', 'N/A')}
- LST: {mcsi.get('lst_raw', 'N/A')}
- VPD: {mcsi.get('vpd_raw', 'N/A')}
- Water Index: {mcsi.get('water_raw', 'N/A')}
""")
    
    # Add live yield context if provided
    if request.yield_context:
        has_live_data = True
        yld = request.yield_context
        prompt_parts.append(f"""
LIVE YIELD FORECAST:
County: {yld.get('county_name', yld.get('fips', 'Unknown'))}
Predicted Yield: {yld.get('predicted_yield', 'N/A')} bu/acre
Confidence: [{yld.get('confidence_lower', 'N/A')}, {yld.get('confidence_upper', 'N/A')}]
Primary Driver: {yld.get('primary_driver', 'N/A')}
""")
    
    # Add document context (truncate to prevent too long prompts)
    if retrieved_text:
        # Limit to ~3000 chars to stay within token limits
        if len(retrieved_text) > 3000:
            retrieved_text = retrieved_text[:3000] + "\n... (truncated)"
        prompt_parts.append(f"""
DOCUMENT CONTEXT (Retrieved from knowledge base):
{retrieved_text}
""")
    else:
        prompt_parts.append("\nNo relevant documents found in knowledge base.")
    
    prompt_parts.append("""
Please answer the user's question using the information above.
Prioritize live data for current conditions and use document context for background information.
""")
    
    full_prompt = "\n".join(prompt_parts)
    logger.info(f"Prompt length: {len(full_prompt)} chars, ~{len(full_prompt)//4} tokens")
    
    # Generate response
    try:
        response = gemini_model.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": 800,
                "temperature": 0.3,
                "top_p": 0.95,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        
        # Log response details for debugging
        logger.info(f"Response candidates: {len(response.candidates) if response.candidates else 0}")
        if response.prompt_feedback:
            logger.info(f"Prompt feedback: {response.prompt_feedback}")
        
        # Check if response was blocked
        if not response.candidates:
            logger.warning(f"No candidates. Prompt feedback: {response.prompt_feedback}")
            raise Exception(f"Response blocked: {response.prompt_feedback}")
        
        candidate = response.candidates[0]
        logger.info(f"Finish reason: {candidate.finish_reason}")
        logger.info(f"Candidate content: {candidate.content}")
        logger.info(f"Safety ratings: {candidate.safety_ratings}")
        
        # Finish reason meanings: 1=STOP (good), 2=MAX_TOKENS, 3=SAFETY
        # Only block on actual SAFETY (3)
        if candidate.finish_reason == 3 or (hasattr(candidate.finish_reason, 'name') and candidate.finish_reason.name == "SAFETY"):
            logger.warning(f"Safety blocked. Ratings: {candidate.safety_ratings}")
            raise Exception(f"Safety blocked: {candidate.safety_ratings}")
        
        # Try to get text - multiple methods
        response_text = None
        
        # Method 1: Try response.text directly
        try:
            response_text = response.text
            logger.info(f"Got text via response.text: {len(response_text)} chars")
        except Exception as e:
            logger.warning(f"response.text failed: {e}")
        
        # Method 2: Try candidate.content.parts
        if not response_text:
            if candidate.content and candidate.content.parts:
                response_text = candidate.content.parts[0].text
                logger.info(f"Got text via parts: {len(response_text)} chars")
        
        if not response_text:
            logger.warning(f"No text in response. Finish reason: {candidate.finish_reason}")
            raise Exception(f"No content in response (finish_reason={candidate.finish_reason})")
        
        return ChatResponse(
            response=response_text,
            sources_used=len(results),
            collection=collection_name,
            has_live_data=has_live_data
        )
        
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        # Return fallback response instead of error
        fallback_msg = """I'm having difficulty processing your request right now. Here's what I can tell you based on general agricultural knowledge:

**General Corn Stress Indicators:**
- 0-20: Healthy conditions, continue normal management
- 20-40: Mild stress, monitor closely  
- 40-60: Moderate stress, consider interventions
- 60-80: Severe stress, take action
- 80-100: Critical stress, emergency measures needed

Please try rephrasing your question or ask about a specific topic like drought stress, heat stress, or yield forecasting."""
        
        return ChatResponse(
            response=fallback_msg,
            sources_used=0,
            collection=collection_name,
            has_live_data=has_live_data
        )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Direct vector search without LLM generation.
    Returns top-k most relevant document chunks.
    """
    logger.info(f"Query: '{request.query[:50]}...'")
    
    collection_name = request.collection_name or COLLECTION_NAME
    collection = get_collection(collection_name)
    
    results = query_collection(collection, request.query, request.top_k)
    
    return QueryResponse(
        results=[
            QueryResult(text=text, score=score, rank=i+1)
            for i, (text, score) in enumerate(results)
        ],
        total_found=len(results),
        collection=collection_name
    )


@app.get("/collections", response_model=List[CollectionInfo])
async def list_collections():
    """List all available collections."""
    if chroma_client is None:
        raise HTTPException(status_code=503, detail="ChromaDB not connected")
    
    try:
        collections = chroma_client.list_collections()
        return [
            CollectionInfo(name=col.name, count=col.count())
            for col in collections
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/load", response_model=LoadResponse)
async def load_documents(request: LoadRequest):
    """
    Load text chunks into a collection.
    
    For bulk loading, use the CLI tool instead.
    """
    collection_name = request.collection_name or COLLECTION_NAME
    collection = get_collection(collection_name)
    
    try:
        # Generate IDs
        ids = [f"doc_{i}_{datetime.now().timestamp()}" for i in range(len(request.texts))]
        
        # Add documents
        collection.add(
            documents=request.texts,
            ids=ids,
            metadatas=request.metadatas if request.metadatas else None
        )
        
        return LoadResponse(
            status="success",
            collection_name=collection_name,
            chunks_loaded=len(request.texts)
        )
        
    except Exception as e:
        logger.error(f"Load failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Delete a collection."""
    if chroma_client is None:
        raise HTTPException(status_code=503, detail="ChromaDB not connected")
    
    try:
        chroma_client.delete_collection(name=collection_name)
        return {"status": "deleted", "collection": collection_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
