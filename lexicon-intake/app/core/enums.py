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


class DeliveryChannel(str, Enum):
    """Delivery channel types."""
    
    WEBHOOK = "WEBHOOK"
    SMS = "SMS"
    EMAIL = "EMAIL"


class DeliveryPurpose(str, Enum):
    """Delivery purpose types."""
    
    LEAD_DELIVERY = "LEAD_DELIVERY"
    FOLLOWUP_CONFIRMATION = "FOLLOWUP_CONFIRMATION"
    FOLLOWUP_REMINDER = "FOLLOWUP_REMINDER"
    URGENT_ESCALATION = "URGENT_ESCALATION"


class UrgencyLevel(str, Enum):
    """Urgency levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SAME_DAY = "same_day"


class ServiceType(str, Enum):
    """Service types."""
    
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    OTHER = "other"
