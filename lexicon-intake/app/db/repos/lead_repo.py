"""Lead record repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CallClassification
from app.db.tables.lead_record import LeadRecord


class LeadRepository:
    """Repository for lead records."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def get_by_lead_id(self, lead_id: str) -> LeadRecord | None:
        """Get lead record by lead_id."""
        result = await self.session.execute(
            select(LeadRecord).where(LeadRecord.lead_id == lead_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_call_id(self, call_id: str) -> LeadRecord | None:
        """Get lead record by call_id."""
        result = await self.session.execute(
            select(LeadRecord).where(LeadRecord.call_id == call_id)
        )
        return result.scalar_one_or_none()
    
    async def create_lead(
        self,
        lead_id: str,
        call_id: str,
        client_id: str,
        caller_name: str | None,
        caller_phone: str,
        service_requested: str | None,
        urgency: str,
        budget: int | None,
        location_zip: str | None,
        classification: CallClassification,
        reason_codes: list[str],
        qualification_outcome: str,
    ) -> LeadRecord:
        """Create a new lead record."""
        lead_record = LeadRecord(
            lead_id=lead_id,
            call_id=call_id,
            client_id=client_id,
            caller_name=caller_name,
            caller_phone=caller_phone,
            service_requested=service_requested,
            urgency=urgency,
            budget=str(budget) if budget is not None else None,
            location_zip=location_zip,
            classification=classification,
            reason_codes=reason_codes,
            qualification_outcome=qualification_outcome,
        )
        
        self.session.add(lead_record)
        await self.session.flush()
        
        return lead_record
