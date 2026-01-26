"""Core enums for the intake system."""

from enum import Enum


class CallClassification(str, Enum):
    """Call classification types."""
    
    QUALIFIED = "QUALIFIED"
    UNQUALIFIED = "UNQUALIFIED"
    SPAM = "SPAM"
    DROPPED = "DROPPED"


class DeliveryStatus(str, Enum):
    """Delivery status types."""
    
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    FAILED_FINAL = "FAILED_FINAL"


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
    """Normalized service types."""
    
    HVAC_REPAIR = "hvac_repair"
    HVAC_INSTALL = "hvac_install"
    PLUMBING = "plumbing"
    PRESSURE_WASH = "pressure_wash"
    RESTORATION = "restoration"
    UNKNOWN = "unknown"


class TimeWindow(str, Enum):
    """Time window classification."""
    
    IN_HOURS = "IN_HOURS"
    AFTER_HOURS = "AFTER_HOURS"
