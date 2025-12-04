"""
AgriGuard API Orchestrator

Routes requests to microservices:
- MCSI Service (Port 8000) - Crop stress indices
- Yield Service (Port 8001) - Yield forecasting  
- RAG Service (Port 8003) - AI chat with agricultural knowledge

Port: 8002
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
from typing import Optional, Dict, Any, List
import logging
import os

app = FastAPI(
    title="AgriGuard API Orchestrator",
    description="Unified API for AgriGuard agricultural intelligence platform",
    version="1.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs (from environment or defaults)
MCSI_URL = os.environ.get("MCSI_URL", "http://mcsi:8000")
YIELD_URL = os.environ.get("YIELD_URL", "http://yield:8001")
RAG_URL = os.environ.get("RAG_URL", "http://rag:8003")

# Fallback URLs for local development
MCSI_URL_LOCAL = "http://localhost:8000"
YIELD_URL_LOCAL = "http://localhost:8001"
RAG_URL_LOCAL = "http://localhost:8003"


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class StressData(BaseModel):
    """Pre-computed stress indices from frontend."""
    overall_stress: Optional[float] = None
    water_stress: Optional[float] = None
    heat_stress: Optional[float] = None
    vegetation_health: Optional[float] = None
    atmospheric_stress: Optional[float] = None
    predicted_yield: Optional[float] = None
    yield_uncertainty: Optional[float] = None


class ChatRequest(BaseModel):
    """Request model for /chat endpoint."""
    message: str = Field(..., description="User's question")
    fips: Optional[str] = Field(default=None, description="County FIPS code for live data")
    week: Optional[int] = Field(default=None, description="Week of season for data lookup")
    include_live_data: bool = Field(default=True, description="Include live MCSI/yield data")
    stress_data: Optional[StressData] = Field(default=None, description="Pre-computed stress indices from frontend")


class ChatResponse(BaseModel):
    """Response model for /chat endpoint."""
    response: str
    sources_used: int
    has_live_data: bool
    county: Optional[str] = None
    mcsi_summary: Optional[Dict[str, Any]] = None
    yield_summary: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

async def try_request(client: httpx.AsyncClient, primary_url: str, 
                     fallback_url: str, method: str = "GET", **kwargs):
    """Try primary URL, fall back to local URL on failure."""
    try:
        if method == "GET":
            response = await client.get(primary_url, **kwargs)
        else:
            response = await client.post(primary_url, **kwargs)
        return response
    except:
        if method == "GET":
            return await client.get(fallback_url, **kwargs)
        else:
            return await client.post(fallback_url, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Check health of all services."""
    services = {
        "mcsi": {"url": MCSI_URL, "local": MCSI_URL_LOCAL, "healthy": False},
        "yield": {"url": YIELD_URL, "local": YIELD_URL_LOCAL, "healthy": False},
        "rag": {"url": RAG_URL, "local": RAG_URL_LOCAL, "healthy": False},
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, svc in services.items():
            try:
                r = await client.get(f"{svc['url']}/health")
                svc["healthy"] = r.status_code == 200
            except:
                try:
                    r = await client.get(f"{svc['local']}/health")
                    svc["healthy"] = r.status_code == 200
                except:
                    pass
    
    all_healthy = all(s["healthy"] for s in services.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {name: "healthy" if s["healthy"] else "unhealthy" 
                    for name, s in services.items()}
    }


# ─────────────────────────────────────────────────────────────────────────────
# MCSI Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/mcsi/{fips}/timeseries")
async def get_mcsi_timeseries(
    fips: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = 30
):
    """Get MCSI timeseries for a county."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"{MCSI_URL}/mcsi/county/{fips}/timeseries?limit={limit}"
            url_local = f"{MCSI_URL_LOCAL}/mcsi/county/{fips}/timeseries?limit={limit}"
            
            if start_date:
                url += f"&start_date={start_date}"
                url_local += f"&start_date={start_date}"
            if end_date:
                url += f"&end_date={end_date}"
                url_local += f"&end_date={end_date}"
            
            response = await try_request(client, url, url_local)
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"MCSI timeseries error: {e}")
        raise HTTPException(status_code=503, detail="MCSI service unavailable")


@app.get("/mcsi/{fips}")
async def get_mcsi(fips: str, week: Optional[int] = None):
    """Get MCSI for a county, optionally for a specific week."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # If week specified, get timeseries and filter
            if week:
                response = await try_request(
                    client,
                    f"{MCSI_URL}/mcsi/county/{fips}/timeseries?limit=30",
                    f"{MCSI_URL_LOCAL}/mcsi/county/{fips}/timeseries?limit=30"
                )
                response.raise_for_status()
                timeseries = response.json()
                
                if isinstance(timeseries, list):
                    # Find the data for the specific week
                    for item in timeseries:
                        if item.get("week_of_season") == week:
                            return item
                    # If week not found, return closest available
                    if timeseries:
                        return min(timeseries, 
                                   key=lambda x: abs(x.get("week_of_season", 0) - week))
                return timeseries
            else:
                # Get latest
                response = await try_request(
                    client,
                    f"{MCSI_URL}/mcsi/county/{fips}",
                    f"{MCSI_URL_LOCAL}/mcsi/county/{fips}"
                )
                response.raise_for_status()
                return response.json()
            
    except Exception as e:
        logger.error(f"MCSI error: {e}")
        raise HTTPException(status_code=503, detail="MCSI service unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# Yield Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/yield/{fips}")
async def get_yield_forecast(fips: str, week: Optional[int] = None):
    """Get yield forecast for a county."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get MCSI timeseries for yield model input
            ts_response = await try_request(
                client,
                f"{MCSI_URL}/mcsi/county/{fips}/timeseries?limit=30",
                f"{MCSI_URL_LOCAL}/mcsi/county/{fips}/timeseries?limit=30"
            )
            ts_response.raise_for_status()
            timeseries = ts_response.json()
            
            if not isinstance(timeseries, list):
                timeseries = [timeseries]
            
            # Determine current week
            current_week = week if week else max(
                item.get("week_of_season", 0) for item in timeseries
            )
            filtered = [
                item for item in timeseries 
                if item.get("week_of_season", 0) <= current_week
            ]
            
            # Build raw_data for yield model
            raw_data = {}
            for item in filtered:
                w = item.get("week_of_season", 0)
                indicators = item.get("indicators", {})
                raw_data[str(w)] = {
                    "water_deficit_mean": indicators.get("water_deficit_mean", 0),
                    "lst_days_above_32C": int(indicators.get("lst_mean", 0)),
                    "ndvi_mean": indicators.get("ndvi_mean", 0.5),
                    "vpd_mean": indicators.get("vpd_mean", 0),
                    "pr_sum": indicators.get("precipitation_mean", 0)
                }
            
            # Call yield service
            yield_req = {
                "fips": fips,
                "current_week": current_week,
                "year": 2025,
                "raw_data": raw_data
            }
            
            logger.info(f"Yield forecast for {fips} week {current_week}")
            
            yield_response = await try_request(
                client,
                f"{YIELD_URL}/forecast",
                f"{YIELD_URL_LOCAL}/forecast",
                method="POST",
                json=yield_req,
                timeout=15.0
            )
            yield_response.raise_for_status()
            ydata = yield_response.json()
            
            return {
                "fips": fips,
                "week": current_week,
                "predicted_yield": ydata.get("yield_forecast_bu_acre"),
                "confidence_interval": ydata.get("forecast_uncertainty", 0.31),
                "confidence_lower": ydata.get("confidence_interval_lower"),
                "confidence_upper": ydata.get("confidence_interval_upper"),
                "primary_driver": ydata.get("primary_driver", "unknown"),
                "model_r2": ydata.get("model_r2", 0.835),
            }
            
    except Exception as e:
        logger.error(f"Yield error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# RAG/Chat Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AgriBot - AI assistant for agricultural recommendations.
    
    Enriches queries with live MCSI and yield data when a FIPS code is provided.
    Uses the specified week for data lookup if provided.
    """
    logger.info(f"Chat request: '{request.message[:50]}...' fips={request.fips} week={request.week}")
    
    mcsi_context = None
    yield_context = None
    county_name = None
    timeseries = None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch live data if FIPS provided
        if request.fips and request.include_live_data:
            # Get MCSI for the specific week (or latest if no week specified)
            try:
                mcsi_url = f"{MCSI_URL}/mcsi/county/{request.fips}/timeseries?limit=30"
                mcsi_url_local = f"{MCSI_URL_LOCAL}/mcsi/county/{request.fips}/timeseries?limit=30"
                
                mcsi_response = await try_request(client, mcsi_url, mcsi_url_local)
                
                if mcsi_response.status_code == 200:
                    timeseries = mcsi_response.json()
                    
                    if isinstance(timeseries, list) and timeseries:
                        # Find data for the specific week or use latest
                        target_week = request.week
                        mcsi_data = None
                        
                        if target_week:
                            # Find exact week or closest
                            for item in timeseries:
                                if item.get("week_of_season") == target_week:
                                    mcsi_data = item
                                    break
                            if not mcsi_data:
                                # Get closest week
                                mcsi_data = min(timeseries, 
                                               key=lambda x: abs(x.get("week_of_season", 0) - target_week))
                        else:
                            # Get latest (highest week)
                            mcsi_data = max(timeseries, key=lambda x: x.get("week_of_season", 0))
                        
                        county_name = mcsi_data.get("county_name", request.fips)
                        
                        # Format for RAG service - use frontend stress values if available
                        mcsi_context = {
                            "fips": request.fips,
                            "county_name": county_name,
                            "date": mcsi_data.get("date"),
                            "week_of_season": mcsi_data.get("week_of_season"),
                            # Use frontend stress indices if provided, otherwise use raw values
                            "overall_stress": request.stress_data.overall_stress if request.stress_data else None,
                            "water_stress": request.stress_data.water_stress if request.stress_data else None,
                            "heat_stress": request.stress_data.heat_stress if request.stress_data else None,
                            "vegetation_health": request.stress_data.vegetation_health if request.stress_data else None,
                            "atmospheric_stress": request.stress_data.atmospheric_stress if request.stress_data else None,
                            # Also include raw values for reference
                            "ndvi_raw": mcsi_data.get("indicators", {}).get("ndvi_mean"),
                            "lst_raw": mcsi_data.get("indicators", {}).get("lst_mean"),
                            "vpd_raw": mcsi_data.get("indicators", {}).get("vpd_mean"),
                            "water_raw": mcsi_data.get("indicators", {}).get("water_deficit_mean"),
                        }
                        logger.info(f"Got MCSI context for {county_name} week {mcsi_context.get('week_of_season')}")
                    elif not isinstance(timeseries, list):
                        # Single item returned
                        mcsi_data = timeseries
                        county_name = mcsi_data.get("county_name", request.fips)
                        mcsi_context = {
                            "fips": request.fips,
                            "county_name": county_name,
                            "date": mcsi_data.get("date"),
                            "week_of_season": mcsi_data.get("week_of_season"),
                            # Use frontend stress indices if provided
                            "overall_stress": request.stress_data.overall_stress if request.stress_data else None,
                            "water_stress": request.stress_data.water_stress if request.stress_data else None,
                            "heat_stress": request.stress_data.heat_stress if request.stress_data else None,
                            "vegetation_health": request.stress_data.vegetation_health if request.stress_data else None,
                            "atmospheric_stress": request.stress_data.atmospheric_stress if request.stress_data else None,
                            # Also include raw values
                            "ndvi_raw": mcsi_data.get("indicators", {}).get("ndvi_mean"),
                            "lst_raw": mcsi_data.get("indicators", {}).get("lst_mean"),
                            "vpd_raw": mcsi_data.get("indicators", {}).get("vpd_mean"),
                            "water_raw": mcsi_data.get("indicators", {}).get("water_deficit_mean"),
                        }
                        logger.info(f"Got MCSI context for {county_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch MCSI: {e}")
            
            # If mcsi_context wasn't created from backend but we have frontend stress_data, use that
            if mcsi_context is None and request.stress_data:
                mcsi_context = {
                    "fips": request.fips,
                    "county_name": county_name or request.fips,
                    "week_of_season": request.week,
                    "overall_stress": request.stress_data.overall_stress,
                    "water_stress": request.stress_data.water_stress,
                    "heat_stress": request.stress_data.heat_stress,
                    "vegetation_health": request.stress_data.vegetation_health,
                    "atmospheric_stress": request.stress_data.atmospheric_stress,
                }
                logger.info(f"Using frontend stress_data for context")
            
            # Get yield forecast for the specific week
            try:
                # We already have timeseries data, build yield request directly
                if isinstance(timeseries, list) and timeseries:
                    current_week = request.week if request.week else max(
                        item.get("week_of_season", 0) for item in timeseries
                    )
                    filtered = [
                        item for item in timeseries 
                        if item.get("week_of_season", 0) <= current_week
                    ]
                    
                    # Build raw_data for yield model
                    raw_data = {}
                    for item in filtered:
                        w = item.get("week_of_season", 0)
                        indicators = item.get("indicators", {})
                        raw_data[str(w)] = {
                            "water_deficit_mean": indicators.get("water_deficit_mean", 0),
                            "lst_days_above_32C": int(indicators.get("lst_mean", 0)),
                            "ndvi_mean": indicators.get("ndvi_mean", 0.5),
                            "vpd_mean": indicators.get("vpd_mean", 0),
                            "pr_sum": indicators.get("precipitation_mean", 0)
                        }
                    
                    # Call yield service directly
                    yield_req = {
                        "fips": request.fips,
                        "current_week": current_week,
                        "year": 2025,
                        "raw_data": raw_data
                    }
                    
                    yield_response = await try_request(
                        client,
                        f"{YIELD_URL}/forecast",
                        f"{YIELD_URL_LOCAL}/forecast",
                        method="POST",
                        json=yield_req,
                        timeout=15.0
                    )
                    
                    if yield_response.status_code == 200:
                        ydata = yield_response.json()
                        # Use frontend yield values if provided, otherwise use backend values
                        yield_context = {
                            "fips": request.fips,
                            "county_name": county_name or request.fips,
                            "week": current_week,
                            "predicted_yield": request.stress_data.predicted_yield if request.stress_data and request.stress_data.predicted_yield else ydata.get("yield_forecast_bu_acre"),
                            "yield_uncertainty": request.stress_data.yield_uncertainty if request.stress_data and request.stress_data.yield_uncertainty else ydata.get("forecast_uncertainty"),
                            "confidence_lower": ydata.get("confidence_interval_lower"),
                            "confidence_upper": ydata.get("confidence_interval_upper"),
                            "primary_driver": ydata.get("primary_driver"),
                            "model_r2": ydata.get("model_r2"),
                        }
                        logger.info(f"Got yield context for week {current_week}: {yield_context.get('predicted_yield')} bu/acre")
            except Exception as e:
                logger.warning(f"Failed to fetch yield: {e}")
            
            # If yield_context wasn't created from backend but we have frontend data, use that
            if yield_context is None and request.stress_data and request.stress_data.predicted_yield:
                yield_context = {
                    "fips": request.fips,
                    "county_name": county_name or request.fips,
                    "week": request.week,
                    "predicted_yield": request.stress_data.predicted_yield,
                    "yield_uncertainty": request.stress_data.yield_uncertainty,
                }
                logger.info(f"Using frontend yield data: {yield_context.get('predicted_yield')} bu/acre")
        
        # Call RAG service
        try:
            rag_payload = {
                "message": request.message,
                "mcsi_context": mcsi_context,
                "yield_context": yield_context,
            }
            
            rag_response = await try_request(
                client,
                f"{RAG_URL}/chat",
                f"{RAG_URL_LOCAL}/chat",
                method="POST",
                json=rag_payload,
                timeout=60.0
            )
            rag_response.raise_for_status()
            rag_data = rag_response.json()
            
            return ChatResponse(
                response=rag_data.get("response", "Unable to generate response"),
                sources_used=rag_data.get("sources_used", 0),
                has_live_data=rag_data.get("has_live_data", False),
                county=county_name,
                mcsi_summary=mcsi_context,
                yield_summary=yield_context,
            )
            
        except httpx.HTTPError as e:
            logger.error(f"RAG service error: {e}")
            raise HTTPException(status_code=503, detail="RAG service unavailable")


@app.post("/query")
async def query_knowledge_base(query: str, top_k: int = 5):
    """
    Direct vector search on knowledge base (no LLM generation).
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await try_request(
                client,
                f"{RAG_URL}/query",
                f"{RAG_URL_LOCAL}/query",
                method="POST",
                json={"query": query, "top_k": top_k}
            )
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=503, detail="RAG service unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
