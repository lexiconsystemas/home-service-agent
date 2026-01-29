"""Client configuration table."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClientConfig(Base):
    """Client configuration table."""

    __tablename__ = "client_configs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    client_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    to_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    # Note: Database column is nullable=True from migration 001
    greeting_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="Thank you for calling. How can we help you today?",
    )

    rules_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    routing_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    delivery_channels: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default="ARRAY['WEBHOOK']::varchar[]",
    )

    webhook_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sms_to_numbers: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )

    email_to_addresses: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )

    # Note: Database column is nullable=True from migration 002
    message_templates: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    # Note: Database column is nullable=True from migration 002
    followup_flags: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    # Legacy followup boolean columns from migration 001
    followup_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    followup_confirmation_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    followup_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    followup_escalation_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    client_api_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Per-client API key for webhook verification",
    )

    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        comment="Configuration version for rollback support",
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Table arguments (no schema - use public)
    __table_args__: tuple = ()
