"""
Yield Forecast router.

Handles all endpoints related to yield forecasting.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import httpx
import logging
import os

from api.utils.http_utils import try_request

logger = logging.getLogger(__name__)

router = APIRouter()

# Service URLs (from environment or defaults)
MCSI_URL = os.environ.get("MCSI_URL", "http://mcsi:8000")
MCSI_URL_LOCAL = os.environ.get("MCSI_URL_LOCAL", "http://localhost:8000")
YIELD_URL = os.environ.get("YIELD_URL", "http://yield:8001")
YIELD_URL_LOCAL = os.environ.get("YIELD_URL_LOCAL", "http://localhost:8001")


@router.get("/yield/{fips}")
async def get_yield_forecast(
    fips: str,
    week: Optional[int] = Query(None, description="Week of season")
):
    """
    Get yield forecast for a county.
    
    Args:
        fips: County FIPS code
        week: Optional week of season
        
    Returns:
        Yield forecast data including predicted yield, confidence intervals, etc.
    """
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
            
    except httpx.HTTPError as e:
        logger.error(f"Yield error: {e}")
        raise HTTPException(status_code=503, detail="Yield service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error in yield forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

