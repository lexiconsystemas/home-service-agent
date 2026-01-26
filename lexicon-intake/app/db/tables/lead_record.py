"""Lead record table."""

from sqlalchemy import Column, String, DateTime, Text, JSON, ARRAY, Index
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.enums import CallClassification, UrgencyLevel, ServiceType, TimeWindow


class LeadRecord(Base):
    """Lead record model."""
    
    __tablename__ = "lead_records"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Basic information
    lead_id = Column(String(255), nullable=False, unique=True, index=True)
    call_id = Column(String(255), nullable=False, index=True)
    client_id = Column(String(255), nullable=False, index=True)
    
    # Caller information
    caller_name = Column(String(255), nullable=True)
    caller_phone = Column(String(20), nullable=False)
    
    # Service information
    service_requested = Column(String(255), nullable=True)
    service_type_normalized = Column(ENUM(ServiceType), nullable=True, index=True)
    service_normalization_reason_codes = Column(ARRAY(String), nullable=True)
    
    # Qualification information
    urgency = Column(ENUM(UrgencyLevel), nullable=False, index=True)
    budget = Column(String(50), nullable=True)
    location_zip = Column(String(10), nullable=True)
    
    # Classification
    classification = Column(ENUM(CallClassification), nullable=False, index=True)
    qualification_outcome = Column(String(50), nullable=False, index=True)
    reason_codes = Column(ARRAY(String), nullable=True)
    
    # Phase 2.5: Routing decision
    routing_profile_name = Column(String(255), nullable=True, index=True)
    time_window = Column(ENUM(TimeWindow), nullable=True, index=True)
    timezone_used = Column(String(50), nullable=True)
    computed_local_time = Column(DateTime(timezone=True), nullable=True)
    chosen_channels = Column(ARRAY(String), nullable=True)
    chosen_destinations = Column(JSON, nullable=True)
    routing_reason_codes = Column(ARRAY(String), nullable=True)
    
    # Delivery status
    delivery_pending = Column(String(20), nullable=False, default="true", index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    client_config = relationship("ClientConfig", back_populates="lead_records")
    delivery_records = relationship("DeliveryRecord", back_populates="lead_record")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_lead_records_lead_id', 'lead_id'),
        Index('idx_lead_records_call_id', 'call_id'),
        Index('idx_lead_records_client_id', 'client_id'),
        Index('idx_lead_records_classification', 'classification'),
        Index('idx_lead_records_urgency', 'urgency'),
        Index('idx_lead_records_service_type', 'service_type_normalized'),
        Index('idx_lead_records_routing_profile', 'routing_profile_name'),
        Index('idx_lead_records_time_window', 'time_window'),
        Index('idx_lead_records_created_at', 'created_at'),
    )
