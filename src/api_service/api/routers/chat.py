"""
Chat/RAG router.

Handles all endpoints related to the AgriBot chat feature and RAG queries.
"""
from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, Dict, Any
import httpx
import logging
import os
import time
import uuid

from api.models import ChatRequest, ChatResponse
from api.utils.http_utils import try_request
from api.utils.chat_utils import ChatHistoryManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Service URLs (from environment or defaults)
MCSI_URL = os.environ.get("MCSI_URL", "http://mcsi:8000")
MCSI_URL_LOCAL = os.environ.get("MCSI_URL_LOCAL", "http://localhost:8000")
YIELD_URL = os.environ.get("YIELD_URL", "http://yield:8001")
YIELD_URL_LOCAL = os.environ.get("YIELD_URL_LOCAL", "http://localhost:8001")
RAG_URL = os.environ.get("RAG_URL", "http://rag:8003")
RAG_URL_LOCAL = os.environ.get("RAG_URL_LOCAL", "http://localhost:8003")

# Initialize chat history manager
chat_manager = ChatHistoryManager(model="agriguard")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AgriBot - AI assistant for agricultural recommendations.
    
    Enriches queries with live MCSI and yield data when a FIPS code is provided.
    Uses the specified week for data lookup if provided.
    
    Args:
        request: ChatRequest containing message, optional FIPS, week, etc.
        
    Returns:
        ChatResponse with AI-generated response and context data
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
        except Exception as e:
            logger.error(f"Unexpected error in chat: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_knowledge_base(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(5, description="Number of results to return")
):
    """
    Direct vector search on knowledge base (no LLM generation).
    
    Args:
        query: Search query string
        top_k: Number of results to return
        
    Returns:
        Search results from the knowledge base
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
            
    except httpx.HTTPError as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=503, detail="RAG service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats")
async def get_chats(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    limit: Optional[int] = Query(None, description="Limit number of chats returned")
):
    """
    Get all chats for a session, optionally limited to a specific number.
    
    Args:
        x_session_id: Session identifier from header
        limit: Optional limit on number of chats
        
    Returns:
        List of recent chats
    """
    if not x_session_id:
        x_session_id = "default"
    return chat_manager.get_recent_chats(x_session_id, limit)


@router.get("/chats/{chat_id}")
async def get_chat(
    chat_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Get a specific chat by ID.
    
    Args:
        chat_id: Unique chat identifier
        x_session_id: Session identifier from header
        
    Returns:
        Chat data or 404 if not found
    """
    if not x_session_id:
        x_session_id = "default"
    chat = chat_manager.get_chat(chat_id, x_session_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

