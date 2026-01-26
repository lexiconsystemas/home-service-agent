"""Lead domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import CallClassification, UrgencyLevel


class Lead(BaseModel):
    """Lead model."""
    
    lead_id: str = Field(..., description="Unique lead identifier")
    call_id: str = Field(..., description="Associated call ID")
    client_id: str = Field(..., description="Client identifier")
    caller_name: str | None = Field(None, description="Caller's name")
    caller_phone: str = Field(..., description="Caller's phone number")
    service_requested: str | None = Field(None, description="Service type requested")
    urgency: UrgencyLevel = Field(..., description="Urgency level")
    budget: int | None = Field(None, description="Budget in dollars")
    location_zip: str | None = Field(None, description="Service location ZIP code")
    classification: CallClassification = Field(..., description="Lead classification")
    reason_codes: list[str] = Field(default_factory=list, description="Classification reason codes")
    created_at: datetime = Field(..., description="Lead creation timestamp")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebhookPayload(BaseModel):
    """Webhook payload model."""
    
    lead_id: str = Field(..., description="Lead ID")
    call_id: str = Field(..., description="Call ID")
    caller_name: str | None = Field(None, description="Caller's name")
    caller_phone: str = Field(..., description="Caller's phone number")
    service_requested: str | None = Field(None, description="Service type requested")
    qualification_outcome: str = Field(..., description="Qualification outcome")
    urgency: str = Field(..., description="Urgency level")
    timestamp: str = Field(..., description="Lead timestamp")
    classification: str = Field(..., description="Call classification")
    reason_codes: list[str] = Field(default_factory=list, description="Reason codes")
