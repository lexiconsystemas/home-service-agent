"""Lead record repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ServiceType, CallClassification
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
        service_type_normalized: ServiceType | None,
        service_normalization_reason_codes: list[str] | None,
        urgency: str,
        budget: str | None,
        location_zip: str | None,
        classification: CallClassification,
        reason_codes: list[str] | None,
        qualification_outcome: str,
        routing_profile_name: str | None,
        time_window: str | None,
        timezone_used: str | None,
        computed_local_time: str,
        chosen_channels: list[str] | None,
        chosen_destinations: dict | None,
        routing_reason_codes: list[str] | None,
    ) -> LeadRecord:
        """Create a new lead record."""
        lead_record = LeadRecord(
            lead_id=lead_id,
            call_id=call_id,
            client_id=client_id,
            caller_name=caller_name,
            caller_phone=caller_phone,
            service_requested=service_requested,
            service_type_normalized=service_type_normalized,
            service_normalization_reason_codes=service_normalization_reason_codes,
            urgency=urgency,
            budget=budget,
            location_zip=location_zip,
            classification=classification,
            reason_codes=reason_codes,
            qualification_outcome=qualification_outcome,
            routing_profile_name=routing_profile_name,
            time_window=time_window,
            timezone_used=timezone_used,
            computed_local_time=computed_local_time,
            chosen_channels=chosen_channels,
            chosen_destinations=chosen_destinations,
            routing_reason_codes=routing_reason_codes,
        )
        
        self.session.add(lead_record)
        await self.session.flush()
        
        return lead_record
    
    async def update_delivery_pending(self, lead_id: str, delivery_pending: bool) -> LeadRecord:
        """Update delivery pending status."""
        result = await self.session.execute(
            select(LeadRecord).where(LeadRecord.lead_id == lead_id)
        )
        lead_record = result.scalar_one()
        
        lead_record.delivery_pending = "true" if delivery_pending else "false"
        
        await self.session.flush()
        
        return lead_record
