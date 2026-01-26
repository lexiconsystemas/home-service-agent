"""Call record repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.tables.call_record import CallRecord


class CallRepository:
    """Repository for call records."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def get_by_call_id(self, call_id: str) -> CallRecord | None:
        """Get call record by call_id."""
        result = await self.session.execute(
            select(CallRecord).where(CallRecord.call_id == call_id)
        )
        return result.scalar_one_or_none()
    
    async def create_call_record(
        self,
        call_id: str,
        from_number: str | None = None,
        to_number: str | None = None,
    ) -> CallRecord:
        """Create a new call record."""
        call_record = CallRecord(
            call_id=call_id,
            from_number=from_number or "",
            to_number=to_number or "",
            processed_at=utc_now(),
        )
        
        self.session.add(call_record)
        await self.session.flush()
        
        return call_record
