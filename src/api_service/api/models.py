"""
Pydantic models for API request/response validation.

Defines the data models used throughout the API for type safety
and automatic validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


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
    stress_data: Optional[StressData] = Field(
        default=None,
        description="Pre-computed stress indices from frontend"
    )


class ChatResponse(BaseModel):
    """Response model for /chat endpoint."""
    response: str
    sources_used: int
    has_live_data: bool
    county: Optional[str] = None
    mcsi_summary: Optional[Dict[str, Any]] = None
    yield_summary: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    """Individual chat message model."""
    message_id: str
    role: str  # "user" or "assistant"
    content: str


class ChatHistoryResponse(BaseModel):
    """Response model for chat history endpoints."""
    chat_id: str
    title: str
    dts: int  # Timestamp
    messages: list[ChatMessage]

