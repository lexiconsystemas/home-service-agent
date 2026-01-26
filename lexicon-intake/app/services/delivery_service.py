"""Delivery service for webhook lead delivery."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.repos.delivery_repo import DeliveryRepository
from app.workers.queue import enqueue_delivery_task

logger = structlog.get_logger()


class DeliveryService:
    """Service for delivering leads via webhooks."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.delivery_repo = DeliveryRepository(db)
    
    async def enqueue_delivery(
        self,
        lead_id: str,
        webhook_url: str,
    ) -> None:
        """
        Enqueue a lead for webhook delivery.
        
        Args:
            lead_id: Lead identifier
            webhook_url: Webhook URL for delivery
        """
        logger.info("Enqueuing delivery", lead_id=lead_id, webhook_url=webhook_url)
        
        # Create delivery record
        delivery_record = await self.delivery_repo.create_delivery_record(
            lead_id=lead_id,
            webhook_url=webhook_url,
        )
        
        # Enqueue delivery task
        await enqueue_delivery_task(str(delivery_record.id))
        
        logger.info("Delivery enqueued successfully", lead_id=lead_id, delivery_id=str(delivery_record.id))
