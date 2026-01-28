"""Delivery record repository."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.db.tables.delivery_record import DeliveryRecord, DeliveryStatus


class DeliveryRepository:
    """Repository for delivery record operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def create_delivery_record(
        self,
        lead_id: str,
        channel: Any,
        purpose: Any,
        destination: str,
        payload: dict[str, Any],
        max_attempts: int = 5,
    ) -> DeliveryRecord:
        """Create a new delivery record."""
        delivery = DeliveryRecord(
            lead_id=lead_id,
            channel=channel,
            purpose=purpose,
            destination=destination,
            payload=payload,
            max_attempts=max_attempts,
        )
        
        self.session.add(delivery)
        await self.session.flush()
        return delivery
    
    async def get_by_id(self, delivery_id: str) -> DeliveryRecord | None:
        """Get delivery record by ID."""
        query = select(DeliveryRecord).where(DeliveryRecord.id == delivery_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_lead_id(self, lead_id: str) -> list[DeliveryRecord]:
        """Get all delivery records for a lead."""
        query = select(DeliveryRecord).where(
            DeliveryRecord.lead_id == lead_id
        ).order_by(desc(DeliveryRecord.created_at))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_delivery_status(
        self,
        delivery_id: str,
        status: DeliveryStatus,
        attempt_count: int | None = None,
        response_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        failed_final: bool | None = None,
        failure_reason: str | None = None,
        response_status_code: int | None = None,
        last_attempt_at: Any = None,
    ) -> DeliveryRecord | None:
        """Update delivery record with new status and attempt information."""
        query = select(DeliveryRecord).where(DeliveryRecord.id == delivery_id)
        result = await self.session.execute(query)
        delivery_record = result.scalar_one_or_none()
        
        if not delivery_record:
            return None
            
        if status is not None:
            delivery_record.status = status
        if attempt_count is not None:
            delivery_record.attempt_count = attempt_count
        else:
            delivery_record.attempt_count += 1
        if response_data is not None:
            delivery_record.response_data = response_data
        if error_message is not None:
            delivery_record.error_message = error_message
        if failed_final is not None:
            delivery_record.failed_final = failed_final
        if failure_reason is not None:
            delivery_record.failure_reason = failure_reason
        if response_status_code is not None:
            delivery_record.response_status_code = response_status_code
        if last_attempt_at is not None:
            delivery_record.last_attempt_at = last_attempt_at
        else:
            delivery_record.last_attempt_at = datetime.utcnow()
        
        await self.session.flush()
        return delivery_record
    
    async def update_delivery_attempt(
        self,
        delivery_id: str,
        status: DeliveryStatus,
        response_status_code: int | None = None,
        error_message: str | None = None,
    ) -> DeliveryRecord:
        """Update delivery record after attempt."""
        query = select(DeliveryRecord).where(DeliveryRecord.id == delivery_id)
        result = await self.session.execute(query)
        delivery_record = result.scalar_one()
        
        delivery_record.status = status
        delivery_record.attempt_count += 1
        delivery_record.last_attempt_at = datetime.utcnow()
        delivery_record.response_status_code = response_status_code
        delivery_record.error_message = error_message
        
        if status == DeliveryStatus.FAILED_FINAL:
            delivery_record.failed_final = True
        
        await self.session.flush()
        return delivery_record
    
    async def get_failed_final_deliveries(
        self,
        client_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DeliveryRecord]:
        """Get deliveries that have failed permanently."""
        query = select(DeliveryRecord).where(
            and_(
                DeliveryRecord.failed_final == True,
                DeliveryRecord.status == DeliveryStatus.FAILED_FINAL
            )
        )
        
        # Add client_id filter if provided
        if client_id:
            from app.db.tables.lead_record import LeadRecord
            query = query.join(LeadRecord).where(LeadRecord.client_id == client_id)
        
        query = query.order_by(desc(DeliveryRecord.last_attempt_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_deliveries(self, limit: int = 100) -> list[DeliveryRecord]:
        """Get pending deliveries for processing."""
        query = select(DeliveryRecord).where(
            and_(
                DeliveryRecord.status == DeliveryStatus.PENDING,
                DeliveryRecord.failed_final == False
            )
        ).order_by(DeliveryRecord.created_at).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_stuck_pending_deliveries(
        self,
        threshold_time: datetime,
    ) -> list[DeliveryRecord]:
        """Get deliveries stuck in PENDING status since threshold time."""
        query = select(DeliveryRecord).where(
            and_(
                DeliveryRecord.status == DeliveryStatus.PENDING,
                DeliveryRecord.failed_final == False,
                DeliveryRecord.created_at < threshold_time
            )
        ).order_by(DeliveryRecord.created_at)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
