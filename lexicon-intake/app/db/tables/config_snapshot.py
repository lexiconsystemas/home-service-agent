"""Configuration snapshot table for versioning and rollback."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConfigSnapshot(Base):
    """Configuration snapshot table for versioning and rollback."""
    
    __tablename__ = "config_snapshots"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    version: Mapped[int] = mapped_column(
        String(20),
        nullable=False,
    )
    
    config_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="client_config | routing_config | delivery_config | followup_config",
    )
    
    config_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Complete configuration snapshot",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Actor who created this snapshot",
    )
    
    change_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for the configuration change",
    )
    
    # Table arguments (no schema - use public)
    __table_args__: tuple = ()
