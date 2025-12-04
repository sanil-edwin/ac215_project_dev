"""
HTTP utility functions for making requests to microservices.

Provides helper functions for making HTTP requests with fallback URLs
for local development.
"""
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


async def try_request(
    client: httpx.AsyncClient,
    primary_url: str,
    fallback_url: str,
    method: str = "GET",
    **kwargs
) -> httpx.Response:
    """
    Try primary URL, fall back to local URL on failure.
    
    This is useful for development where services might be running
    on localhost instead of Docker service names.
    
    Args:
        client: httpx AsyncClient instance
        primary_url: Primary service URL (e.g., http://mcsi:8000)
        fallback_url: Fallback URL for local development (e.g., http://localhost:8000)
        method: HTTP method ("GET" or "POST")
        **kwargs: Additional arguments to pass to the HTTP request
        
    Returns:
        httpx.Response object
        
    Raises:
        httpx.HTTPError: If both primary and fallback requests fail
    """
    try:
        if method == "GET":
            response = await client.get(primary_url, **kwargs)
        elif method == "POST":
            response = await client.post(primary_url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        return response
    except Exception as e:
        logger.debug(f"Primary URL failed ({primary_url}): {e}, trying fallback...")
        try:
            if method == "GET":
                response = await client.get(fallback_url, **kwargs)
            elif method == "POST":
                response = await client.post(fallback_url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            return response
        except Exception as fallback_error:
            logger.error(f"Both primary and fallback URLs failed. Fallback error: {fallback_error}")
            raise


async def check_service_health(
    client: httpx.AsyncClient,
    service_url: str,
    fallback_url: str,
    timeout: float = 5.0
) -> bool:
    """
    Check if a service is healthy.
    
    Args:
        client: httpx AsyncClient instance
        service_url: Primary service URL
        fallback_url: Fallback URL for local development
        timeout: Request timeout in seconds
        
    Returns:
        True if service is healthy, False otherwise
    """
    try:
        response = await try_request(
            client,
            f"{service_url}/health",
            f"{fallback_url}/health",
            method="GET",
            timeout=timeout
        )
        return response.status_code == 200
    except Exception:
        return False

