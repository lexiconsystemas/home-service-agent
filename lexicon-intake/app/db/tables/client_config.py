"""Client configuration table."""

from sqlalchemy import Column, String, Boolean, JSON, ARRAY, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClientConfig(Base):
    """Client configuration model."""
    
    __tablename__ = "client_configs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Basic configuration
    client_id = Column(String(255), nullable=False, unique=True, index=True)
    to_number = Column(String(20), nullable=False, index=True)
    greeting = Column(String(255), nullable=True)
    
    # Qualification rules
    rules_json = Column(JSON, nullable=True)
    
    # Delivery channels configuration
    delivery_channels = Column(ARRAY(String), nullable=False, default=["WEBHOOK"])
    webhook_url = Column(String(2048), nullable=True)
    sms_to_numbers = Column(ARRAY(String), nullable=True)
    email_to_addresses = Column(ARRAY(String), nullable=True)
    
    # Message templates
    message_templates = Column(JSON, nullable=True)
    
    # Follow-up configuration
    followup_flags = Column(JSON, nullable=True)
    
    # Legacy fields for backward compatibility
    followup_enabled = Column(Boolean, nullable=False, default=False)
    followup_confirmation_enabled = Column(Boolean, nullable=False, default=False)
    followup_reminder_enabled = Column(Boolean, nullable=False, default=False)
    followup_escalation_enabled = Column(Boolean, nullable=False, default=False)
    
    # Phase 2.5: Routing configuration
    routing_json = Column(JSON, nullable=True)
    
    # Relationships
    call_records = relationship("CallRecord", back_populates="client_config")
    lead_records = relationship("LeadRecord", back_populates="client_config")
    delivery_records = relationship("DeliveryRecord", back_populates="client_config")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_client_configs_client_id', 'client_id'),
        Index('idx_client_configs_to_number', 'to_number'),
    )
