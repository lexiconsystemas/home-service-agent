"""Lead record repository."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.enums import ServiceType, CallClassification
from app.db.tables.lead_record import LeadRecord


class LeadRepository:
    """Repository for lead record operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def create_lead(
        self,
        call_id: str,
        client_id: str,
        caller_name: str | None,
        caller_phone: str,
        service_requested: str,
        service_type_normalized: Any | None,
        service_normalization_reason_codes: list[str] | None,
        location_zip: str | None,
        budget: str | None,
        urgency: Any,
        classification: Any,
        qualification_outcome: str | None,
        qualification_reason_codes: list[str] | None,
        routing_profile_name: str | None,
        time_window: Any | None,
        timezone_used: str | None,
        computed_local_time: datetime | None,
        chosen_channels: list[str] | None,
        chosen_destinations: dict[str, Any] | None,
        routing_reason_codes: list[str] | None,
        delivery_pending: bool = True,
    ) -> LeadRecord:
        """Create a new lead record."""
        lead = LeadRecord(
            call_id=call_id,
            client_id=client_id,
            caller_name=caller_name,
            caller_phone=caller_phone,
            service_requested=service_requested,
            service_type_normalized=service_type_normalized,
            service_normalization_reason_codes=service_normalization_reason_codes,
            location_zip=location_zip,
            budget=budget,
            urgency=urgency,
            classification=classification,
            qualification_outcome=qualification_outcome,
            qualification_reason_codes=qualification_reason_codes,
            routing_profile_name=routing_profile_name,
            time_window=time_window,
            timezone_used=timezone_used,
            computed_local_time=computed_local_time,
            chosen_channels=chosen_channels,
            chosen_destinations=chosen_destinations,
            routing_reason_codes=routing_reason_codes,
            delivery_pending=delivery_pending,
        )
        
        self.session.add(lead)
        await self.session.flush()
        return lead
    
    async def get_by_lead_id(self, lead_id: str) -> LeadRecord | None:
        """Get lead record by lead ID."""
        query = select(LeadRecord).where(LeadRecord.lead_id == lead_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_call_id(self, call_id: str) -> LeadRecord | None:
        """Get lead record by call ID."""
        query = select(LeadRecord).where(LeadRecord.call_id == call_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_delivery_pending(
        self,
        lead_id: str,
        delivery_pending: bool,
    ) -> LeadRecord | None:
        """Update delivery pending status."""
        query = select(LeadRecord).where(LeadRecord.lead_id == lead_id)
        result = await self.session.execute(query)
        lead = result.scalar_one_or_none()
        
        if lead:
            lead.delivery_pending = delivery_pending
            await self.session.flush()
        
        return lead
    
    async def update_scheduling_selection(
        self,
        lead_id: str,
        window_label: str,
        start_estimate: datetime,
        end_estimate: datetime,
    ) -> LeadRecord | None:
        """Update scheduling selection on lead record."""
        query = select(LeadRecord).where(LeadRecord.lead_id == lead_id)
        result = await self.session.execute(query)
        lead = result.scalar_one_or_none()
        
        if lead:
            lead.scheduled_window_label = window_label
            lead.scheduled_start_estimate = start_estimate
            lead.scheduled_end_estimate = end_estimate
            await self.session.flush()
        
        return lead
    
    async def get_leads_by_client(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LeadRecord]:
        """Get leads for a client."""
        query = select(LeadRecord).where(
            LeadRecord.client_id == client_id
        ).order_by(desc(LeadRecord.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_leads_with_scheduling_pending(
        self,
        limit: int = 50,
    ) -> list[LeadRecord]:
        """Get leads that have scheduling pending (qualified but no window selected)."""
        query = select(LeadRecord).where(
            LeadRecord.classification == "QUALIFIED",
            LeadRecord.scheduled_window_label.is_(None),
        ).order_by(LeadRecord.created_at).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
