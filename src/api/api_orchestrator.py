"""
AgriGuard API Orchestrator

Backward-compatible wrapper that imports from the new structured service.
This maintains compatibility with existing deployments while using the new structure.

Routes requests to microservices:
- MCSI Service (Port 8000) - Crop stress indices
- Yield Service (Port 8001) - Yield forecasting  
- RAG Service (Port 8003) - AI chat with agricultural knowledge

Port: 8002
"""

# Import the new structured service
from api.service import app

# Re-export models for backward compatibility
from api.models import (
    StressData,
    ChatRequest,
    ChatResponse
)

# Re-export app for backward compatibility
__all__ = ["app", "StressData", "ChatRequest", "ChatResponse"]
