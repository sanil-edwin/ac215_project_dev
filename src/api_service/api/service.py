"""
AgriGuard API Service

Main FastAPI application entry point.
Routes requests to microservices:
- MCSI Service (Port 8000) - Crop stress indices
- Yield Service (Port 8001) - Yield forecasting  
- RAG Service (Port 8003) - AI chat with agricultural knowledge

Port: 8002
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
import os

from api.routers import mcsi, yield_forecast, chat
from api.utils.http_utils import check_service_health

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs (from environment or defaults)
MCSI_URL = os.environ.get("MCSI_URL", "http://mcsi:8000")
MCSI_URL_LOCAL = os.environ.get("MCSI_URL_LOCAL", "http://localhost:8000")
YIELD_URL = os.environ.get("YIELD_URL", "http://yield:8001")
YIELD_URL_LOCAL = os.environ.get("YIELD_URL_LOCAL", "http://localhost:8001")
RAG_URL = os.environ.get("RAG_URL", "http://rag:8003")
RAG_URL_LOCAL = os.environ.get("RAG_URL_LOCAL", "http://localhost:8003")

# Setup FastAPI app
app = FastAPI(
    title="AgriGuard API Orchestrator",
    description="Unified API for AgriGuard agricultural intelligence platform",
    version="1.4.0"
)

# Enable CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(mcsi.router, tags=["MCSI"])
app.include_router(yield_forecast.router, tags=["Yield"])
app.include_router(chat.router, tags=["Chat"])


@app.get("/")
async def get_index():
    """Root endpoint."""
    return {
        "message": "Welcome to AgriGuard API",
        "version": "1.4.0",
        "endpoints": {
            "health": "/health",
            "mcsi": "/mcsi/{fips}",
            "yield": "/yield/{fips}",
            "chat": "/chat",
            "query": "/query"
        }
    }


@app.get("/health")
async def health_check():
    """
    Check health of all services.
    
    Returns:
        Status of all microservices
    """
    services = {
        "mcsi": {"url": MCSI_URL, "local": MCSI_URL_LOCAL, "healthy": False},
        "yield": {"url": YIELD_URL, "local": YIELD_URL_LOCAL, "healthy": False},
        "rag": {"url": RAG_URL, "local": RAG_URL_LOCAL, "healthy": False},
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, svc in services.items():
            svc["healthy"] = await check_service_health(
                client, svc["url"], svc["local"]
            )
    
    all_healthy = all(s["healthy"] for s in services.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {name: "healthy" if s["healthy"] else "unhealthy" 
                    for name, s in services.items()}
    }


# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

