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
        """Update delivery record status and metadata."""
        query = select(DeliveryRecord).where(DeliveryRecord.id == delivery_id)
        result = await self.session.execute(query)
        delivery = result.scalar_one_or_none()
        
        if delivery:
            delivery.status = status
            
            if attempt_count is not None:
                delivery.attempt_count = attempt_count
            
            if response_data is not None:
                delivery.response_data = response_data
            
            if error_message is not None:
                delivery.error_message = error_message
            
            if failed_final is not None:
                delivery.failed_final = failed_final
            
            if failure_reason is not None:
                delivery.failure_reason = failure_reason
            
            if response_status_code is not None:
                delivery.response_status_code = response_status_code
            
            if last_attempt_at is not None:
                delivery.last_attempt_at = last_attempt_at
            
            await self.session.flush()
        
        return delivery
    
    async def update_delivery_attempt(
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
        """Alias for update_delivery_status to maintain compatibility."""
        return await self.update_delivery_status(
            delivery_id=delivery_id,
            status=status,
            attempt_count=attempt_count,
            response_data=response_data,
            error_message=error_message,
            failed_final=failed_final,
            failure_reason=failure_reason,
            response_status_code=response_status_code,
            last_attempt_at=last_attempt_at,
        )
    
    async def get_failed_final_deliveries(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DeliveryRecord]:
        """Get deliveries that have failed permanently."""
        query = select(DeliveryRecord).where(
            and_(
                DeliveryRecord.failed_final == True,
                DeliveryRecord.status == DeliveryStatus.FAILED_FINAL
            )
        ).order_by(desc(DeliveryRecord.last_attempt_at)).limit(limit).offset(offset)
        
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
