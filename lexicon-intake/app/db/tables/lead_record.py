"""Lead record table."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    CallClassification,
    UrgencyLevel,
    ServiceType,
    TimeWindow,
)
from app.db.base import Base


class LeadRecord(Base):
    """Lead record table."""
    
    __tablename__ = "lead_records"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    lead_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    
    call_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    caller_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )
    
    caller_phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    service_requested: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    service_type_normalized: Mapped[ServiceType] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    
    service_normalization_reason_codes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    location_zip: Mapped[str] = mapped_column(
        String(10),
        nullable=True,
    )
    
    budget: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    
    urgency: Mapped[UrgencyLevel] = mapped_column(
        String(20),
        nullable=False,
    )
    
    classification: Mapped[CallClassification] = mapped_column(
        String(30),
        nullable=False,
    )
    
    qualification_outcome: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    
    qualification_reason_codes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    routing_profile_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    
    time_window: Mapped[TimeWindow] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    
    timezone_used: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    
    computed_local_time: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    
    chosen_channels: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    chosen_destinations: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    routing_reason_codes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Scheduling fields
    scheduled_window_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Label of selected scheduling window",
    )
    
    scheduled_start_estimate: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Estimated start time for scheduled window",
    )
    
    scheduled_end_estimate: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Estimated end time for scheduled window",
    )
    
    delivery_pending: Mapped[bool] = mapped_column(
        String(20),
        nullable=False,
        default=True,
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
    
    # Table arguments (no schema - use public)
    __table_args__: tuple = ()
