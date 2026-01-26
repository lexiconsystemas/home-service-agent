"""System enums."""

from enum import Enum


class CallClassification(str, Enum):
    """Call classification states."""
    
    QUALIFIED = "QUALIFIED"
    UNQUALIFIED = "UNQUALIFIED"
    SPAM = "SPAM"
    DROPPED = "DROPPED"


class DeliveryStatus(str, Enum):
    """Delivery status states."""
    
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class UrgencyLevel(str, Enum):
    """Urgency levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ServiceType(str, Enum):
    """Service types."""
    
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    OTHER = "other"
