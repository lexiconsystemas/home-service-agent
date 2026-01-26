"""Client configuration table model."""

from sqlalchemy import Column, String, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampMixin, UUIDMixin


class ClientConfig(Base, UUIDMixin, TimestampMixin):
    """Client configuration table."""
    
    __tablename__ = "client_configs"
    
    client_id = Column(String(100), unique=True, nullable=False, index=True)
    to_number = Column(String(20), nullable=False)
    greeting = Column(Text, nullable=True)
    rules_json = Column(JSON, nullable=False)
    webhook_url = Column(Text, nullable=True)
    
    # Follow-up configuration
    followup_enabled = Column(Boolean, nullable=False, default=False)
    followup_confirmation_enabled = Column(Boolean, nullable=False, default=False)
    followup_reminder_enabled = Column(Boolean, nullable=False, default=False)
    followup_escalation_enabled = Column(Boolean, nullable=False, default=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_client_configs_client_id', 'client_id'),
        Index('idx_client_configs_to_number', 'to_number'),
    )
