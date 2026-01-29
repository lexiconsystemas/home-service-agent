"""Lead record table."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Create PostgreSQL ENUM types that match the migration definitions
urgency_enum = ENUM('LOW', 'MEDIUM', 'HIGH', 'SAME_DAY', name='urgencylevel', create_type=False)
classification_enum = ENUM('QUALIFIED', 'UNQUALIFIED', 'SPAM', 'DROPPED', name='callclassification', create_type=False)


class LeadRecord(Base):
    """Lead record table - matches migration 001 schema."""

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
        String(100),
        nullable=False,
        index=True,
    )

    caller_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    caller_phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    service_requested: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    urgency: Mapped[str] = mapped_column(
        urgency_enum,
        nullable=False,
    )

    budget: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    location_zip: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    classification: Mapped[str] = mapped_column(
        classification_enum,
        nullable=False,
    )

    reason_codes: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    qualification_outcome: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
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
