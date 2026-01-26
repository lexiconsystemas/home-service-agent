"""Delivery record table model."""

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM

from app.core.enums import DeliveryStatus, DeliveryChannel, DeliveryPurpose
from app.db.base import Base, TimestampMixin, UUIDMixin


class DeliveryRecord(Base, UUIDMixin, TimestampMixin):
    """Delivery record table for webhook deliveries."""
    
    __tablename__ = "delivery_records"
    
    lead_id = Column(String(255), nullable=False, index=True)
    channel = Column(ENUM(DeliveryChannel), nullable=False, index=True)
    purpose = Column(ENUM(DeliveryPurpose), nullable=False, index=True)
    destination = Column(Text, nullable=False)  # URL, phone, or email
    status = Column(ENUM(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_delivery_records_lead_id', 'lead_id'),
        Index('idx_delivery_records_channel', 'channel'),
        Index('idx_delivery_records_purpose', 'purpose'),
        Index('idx_delivery_records_status', 'status'),
        Index('idx_delivery_records_created_at', 'created_at'),
    )
