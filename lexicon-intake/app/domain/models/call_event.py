"""Call event domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator


class CallEvent(BaseModel):
    """Inbound call event model."""
    
    call_id: str = Field(..., description="Unique identifier for the call")
    from_number: str = Field(..., description="Caller's phone number")
    to_number: str = Field(..., description="Called phone number")
    timestamp: datetime = Field(..., description="Call timestamp")
    caller_name: str | None = Field(None, description="Caller's name")
    service_requested: str | None = Field(None, description="Service type requested")
    urgency: str = Field("medium", description="Urgency level")
    budget: int | None = Field(None, description="Budget in dollars")
    location_zip: str | None = Field(None, description="Service location ZIP code")
    
    @validator("from_number", "to_number")
    def validate_phone_numbers(cls, v: str) -> str:
        """Validate phone number format."""
        if not v or len(v.strip()) < 10:
            raise ValueError("Invalid phone number")
        return v.strip()
    
    @validator("urgency")
    def validate_urgency(cls, v: str) -> str:
        """Validate urgency level."""
        allowed = ["low", "medium", "high"]
        if v.lower() not in allowed:
            raise ValueError(f"Urgency must be one of: {allowed}")
        return v.lower()
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CallEventResponse(BaseModel):
    """Response model for call event processing."""
    
    lead_id: str = Field(..., description="Generated lead ID")
    classification: str = Field(..., description="Call classification")
    message: str = Field(..., description="Processing message")
