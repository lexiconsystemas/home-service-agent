"""Call record table model."""

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampMixin, UUIDMixin


class CallRecord(Base, UUIDMixin, TimestampMixin):
    """Call record table for idempotency."""
    
    __tablename__ = "call_records"
    
    call_id = Column(String(255), unique=True, nullable=False, index=True)
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_call_records_call_id', 'call_id'),
        Index('idx_call_records_processed_at', 'processed_at'),
    )
