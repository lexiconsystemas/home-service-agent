"""Audit log repository."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.tables.audit_log import AuditLog


class AuditRepository:
    """Repository for audit log operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def create_audit_log(
        self,
        actor_type: str,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create a new audit log entry."""
        audit_log = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_state=before_state,
            after_state=after_state,
            details=details,
        )
        
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log
    
    async def get_audit_logs(
        self,
        target_type: str | None = None,
        target_id: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs with optional filters."""
        query = select(AuditLog).order_by(desc(AuditLog.ts))
        
        if target_type:
            query = query.where(AuditLog.target_type == target_type)
        if target_id:
            query = query.where(AuditLog.target_id == target_id)
        if actor_type:
            query = query.where(AuditLog.actor_type == actor_type)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        if action:
            query = query.where(AuditLog.action == action)
        
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
