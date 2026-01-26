"""Audit log table for tracking all admin and system actions."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """Audit log table for tracking all configuration changes and system actions."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    ts: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    actor_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="SYSTEM | ADMIN | CLIENT",
    )
    
    actor_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="client_id or admin identifier",
    )
    
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CONFIG_UPDATE | REPLAY_DELIVERY | CREATE_CLIENT | ROTATE_KEY | SCHEDULING_RESPONSE",
    )
    
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="client_config | routing_config | lead | delivery | audit_log",
    )
    
    target_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ID of the target resource",
    )
    
    before_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Previous state of the resource",
    )
    
    after_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="New state of the resource",
    )
    
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional context or metadata",
    )
    
    # Indexes for common queries
    __table_args__ = (
        {"schema": "lexicon_intake"},
    )
