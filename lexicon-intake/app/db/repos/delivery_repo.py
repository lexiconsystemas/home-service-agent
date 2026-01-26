"""Delivery record repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DeliveryStatus, DeliveryChannel, DeliveryPurpose
from app.db.tables.delivery_record import DeliveryRecord


class DeliveryRepository:
    """Repository for delivery records."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def get_by_lead_id(self, lead_id: str) -> list[DeliveryRecord]:
        """Get delivery records by lead_id."""
        result = await self.session.execute(
            select(DeliveryRecord).where(DeliveryRecord.lead_id == lead_id)
        )
        return result.scalars().all()
    
    async def create_delivery_record(
        self,
        lead_id: str,
        channel: DeliveryChannel,
        purpose: DeliveryPurpose,
        destination: str,
    ) -> DeliveryRecord:
        """Create a new delivery record."""
        delivery_record = DeliveryRecord(
            lead_id=lead_id,
            channel=channel,
            purpose=purpose,
            destination=destination,
            status=DeliveryStatus.PENDING,
            attempt_count=0,
        )
        
        self.session.add(delivery_record)
        await self.session.flush()
        
        return delivery_record
    
    async def update_delivery_attempt(
        self,
        delivery_id: str,
        status: DeliveryStatus,
        response_status_code: int | None = None,
        response_body: str | None = None,
        error_message: str | None = None,
    ) -> DeliveryRecord:
        """Update delivery record with attempt details."""
        result = await self.session.execute(
            select(DeliveryRecord).where(DeliveryRecord.id == delivery_id)
        )
        delivery_record = result.scalar_one()
        
        delivery_record.status = status
        delivery_record.attempt_count += 1
        delivery_record.response_status_code = response_status_code
        delivery_record.response_body = response_body
        delivery_record.error_message = error_message
        
        await self.session.flush()
        
        return delivery_record
