"""
MCSI (Multi-source Crop Stress Index) router.

Handles all endpoints related to crop stress monitoring.
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


@router.get("/mcsi/{fips}/timeseries")
async def get_mcsi_timeseries(
    fips: str,
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    limit: Optional[int] = Query(30, description="Maximum number of records to return")
):
    """
    Get MCSI timeseries for a county.
    
    Args:
        fips: County FIPS code
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of records
        
    Returns:
        List of MCSI data points over time
    """
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
            
    except httpx.HTTPError as e:
        logger.error(f"MCSI timeseries error: {e}")
        raise HTTPException(status_code=503, detail="MCSI service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error in MCSI timeseries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcsi/{fips}")
async def get_mcsi(fips: str, week: Optional[int] = Query(None, description="Week of season")):
    """
    Get MCSI for a county, optionally for a specific week.
    
    Args:
        fips: County FIPS code
        week: Optional week of season
        
    Returns:
        MCSI data for the county (and week if specified)
    """
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
            
    except httpx.HTTPError as e:
        logger.error(f"MCSI error: {e}")
        raise HTTPException(status_code=503, detail="MCSI service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error in MCSI: {e}")
        raise HTTPException(status_code=500, detail=str(e))

