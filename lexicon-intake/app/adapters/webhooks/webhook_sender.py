"""Webhook sender for lead delivery."""

import asyncio
import json
from typing import Any

import httpx
import structlog

from app.core.enums import DeliveryStatus
from app.core.security import generate_webhook_signature
from app.core.time import utc_now, format_timestamp
from app.db.repos.delivery_repo import DeliveryRepository
from app.db.repos.lead_repo import LeadRepository
from app.db.session import get_async_session_context
from app.domain.models.lead import WebhookPayload
from app.settings import settings

logger = structlog.get_logger()


class WebhookSender:
    """Service for sending webhook deliveries with retries."""
    
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_webhook(
        self,
        delivery_id: str,
        webhook_url: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """
        Send webhook (single attempt - RQ handles retries).
        
        Args:
            delivery_id: Delivery record ID
            webhook_url: Webhook URL to send to
            max_retries: Maximum number of retry attempts (for compatibility)
            retry_delay: Initial delay between retries (for compatibility)
            
        Returns:
            True if delivery succeeded, False otherwise
        """
        async with get_async_session_context() as db:
            delivery_repo = DeliveryRepository(db)
            lead_repo = LeadRepository(db)
            
            # Get delivery record
            delivery_records = await delivery_repo.get_by_lead_id(delivery_id)
            if not delivery_records:
                logger.error("Delivery record not found", delivery_id=delivery_id)
                return False
            
            delivery_record = delivery_records[0]  # Get first record
            
            # Get lead record
            lead_record = await lead_repo.get_by_lead_id(delivery_record.lead_id)
            if not lead_record:
                logger.error("Lead record not found", lead_id=delivery_record.lead_id)
                return False
            
            # Create webhook payload
            payload = WebhookPayload(
                lead_id=lead_record.lead_id,
                caller_name=lead_record.caller_name,
                caller_phone=lead_record.caller_phone,
                service_requested=lead_record.service_requested,
                service_type_normalized=lead_record.service_type_normalized.value if lead_record.service_type_normalized else None,
                qualification_outcome=lead_record.qualification_outcome,
                classification=lead_record.classification.value,
                urgency=lead_record.urgency.value if lead_record.urgency else None,
                budget=lead_record.budget,
                location_zip=lead_record.location_zip,
                created_at=lead_record.created_at,
                routing_profile_name=lead_record.routing_profile_name,
                time_window=lead_record.time_window.value if lead_record.time_window else None,
                chosen_channels=lead_record.chosen_channels,
                scheduled_window_label=lead_record.scheduled_window_label,
            )
            
            payload_json = json.dumps(payload.dict(), default=str)
            
            # Generate webhook signature
            signature = generate_webhook_signature(
                payload_json.encode(),
                settings.webhook_signing_secret,
            )
            
            headers = {
                "Content-Type": "application/json",
                "X-Lexicon-Signature": signature,
                "User-Agent": "Lexicon-Intake/1.0",
            }
            
            # Single attempt - RQ handles retries
            try:
                logger.info(
                    "Sending webhook",
                    delivery_id=str(delivery_record.id),
                    lead_id=delivery_record.lead_id,
                    webhook_url=webhook_url,
                )
                
                response = await self.client.post(
                    webhook_url,
                    content=payload_json,
                    headers=headers,
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    # Success
                    await delivery_repo.update_delivery_attempt(
                        delivery_id=str(delivery_record.id),
                        status=DeliveryStatus.SENT,
                        response_status_code=response.status_code,
                        response_body=response.text[:1000],  # Limit response body size
                    )
                    
                    logger.info(
                        "Webhook delivered successfully",
                        delivery_id=str(delivery_record.id),
                        lead_id=delivery_record.lead_id,
                        status_code=response.status_code,
                    )
                    return True
                
                else:
                    # HTTP error
                    await delivery_repo.update_delivery_attempt(
                        delivery_id=str(delivery_record.id),
                        status=DeliveryStatus.FAILED,
                        response_status_code=response.status_code,
                        response_body=response.text[:1000],
                        error_message=f"HTTP {response.status_code}: {response.text[:200]}",
                    )
                    
                    logger.warning(
                        "Webhook delivery failed",
                        delivery_id=str(delivery_record.id),
                        lead_id=delivery_record.lead_id,
                        status_code=response.status_code,
                        response_text=response.text[:200],
                    )
                    
                    # Don't retry client errors (4xx)
                    if 400 <= response.status_code < 500:
                        logger.info("Client error - no retry", status_code=response.status_code)
                    
                    return False
            
            except httpx.RequestError as e:
                # Network error - let RQ retry
                await delivery_repo.update_delivery_attempt(
                    delivery_id=str(delivery_record.id),
                    status=DeliveryStatus.RETRYING,
                    error_message=str(e),
                )
                
                logger.warning(
                    "Webhook network error - RQ will retry",
                    delivery_id=str(delivery_record.id),
                    lead_id=delivery_record.lead_id,
                    error=str(e),
                )
                
                return False
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
