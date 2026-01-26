"""Delivery record table for tracking delivery attempts."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DeliveryChannel, DeliveryPurpose, DeliveryStatus
from app.db.base import Base


class DeliveryRecord(Base):
    """Delivery record table for tracking delivery attempts."""
    
    __tablename__ = "delivery_records"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    lead_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    channel: Mapped[DeliveryChannel] = mapped_column(
        String(20),
        nullable=False,
    )
    
    purpose: Mapped[DeliveryPurpose] = mapped_column(
        String(30),
        nullable=False,
    )
    
    destination: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    status: Mapped[DeliveryStatus] = mapped_column(
        String(30),
        nullable=False,
        default=DeliveryStatus.PENDING,
    )
    
    attempt_count: Mapped[int] = mapped_column(
        String(20),
        nullable=False,
        default=0,
    )
    
    max_attempts: Mapped[int] = mapped_column(
        String(20),
        nullable=False,
        default=5,
    )
    
    failed_final: Mapped[bool] = mapped_column(
        String(20),
        nullable=False,
        default=False,
        comment="True when max retries exhausted and no further attempts will be made",
    )
    
    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed reason for final failure",
    )
    
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp of the last delivery attempt",
    )
    
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    
    response_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Indexes for common queries
    __table_args__ = (
        {"schema": "lexicon_intake"},
    )
