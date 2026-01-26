"""Lead record table model."""

from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM

from app.core.enums import CallClassification, UrgencyLevel
from app.db.base import Base, TimestampMixin, UUIDMixin


class LeadRecord(Base, UUIDMixin, TimestampMixin):
    """Lead record table."""
    
    __tablename__ = "lead_records"
    
    lead_id = Column(String(255), unique=True, nullable=False, index=True)
    call_id = Column(String(255), nullable=False, index=True)
    client_id = Column(String(100), nullable=False, index=True)
    caller_name = Column(String(255), nullable=True)
    caller_phone = Column(String(20), nullable=False)
    service_requested = Column(String(100), nullable=True)
    urgency = Column(ENUM(UrgencyLevel), nullable=False)
    budget = Column(String(20), nullable=True)  # Store as string to handle various formats
    location_zip = Column(String(10), nullable=True)
    classification = Column(ENUM(CallClassification), nullable=False, index=True)
    reason_codes = Column(JSON, nullable=False, default=list)
    qualification_outcome = Column(String(20), nullable=False)  # qualified/unqualified
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_lead_records_lead_id', 'lead_id'),
        Index('idx_lead_records_call_id', 'call_id'),
        Index('idx_lead_records_client_id', 'client_id'),
        Index('idx_lead_records_classification', 'classification'),
        Index('idx_lead_records_created_at', 'created_at'),
    )
