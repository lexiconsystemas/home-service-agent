"""Rule definitions and configurations."""

from typing import Any

from pydantic import BaseModel, Field


class QualificationRules(BaseModel):
    """Qualification rule configuration."""
    
    service_types_allowed: list[str] = Field(
        default_factory=lambda: ["plumbing", "electrical", "hvac"],
        description="Allowed service types",
    )
    service_area_zip_prefixes: list[str] = Field(
        default_factory=lambda: ["90210", "90211", "90212"],
        description="Allowed service area ZIP prefixes",
    )
    min_budget: int = Field(default=100, description="Minimum budget requirement")
    urgency_allowed: list[str] = Field(
        default_factory=lambda: ["low", "medium", "high"],
        description="Allowed urgency levels",
    )
    
    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow additional fields for future expansion


# Default rules for demo client
DEFAULT_RULES = QualificationRules()
