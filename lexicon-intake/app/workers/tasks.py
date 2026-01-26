"""Background task definitions."""

import asyncio
from typing import Any

import structlog

from app.adapters.webhooks.webhook_sender import WebhookSender

logger = structlog.get_logger()


def deliver_webhook_task(delivery_id: str) -> bool:
    """
    Background task to deliver webhook.
    
    Args:
        delivery_id: Delivery record ID
        
    Returns:
        True if delivery succeeded, False otherwise
    """
    logger.info("Starting webhook delivery task", delivery_id=delivery_id)
    
    try:
        # Run async webhook sender in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            webhook_sender = WebhookSender()
            result = loop.run_until_complete(
                webhook_sender.send_webhook(delivery_id)
            )
            logger.info(
                "Webhook delivery task completed",
                delivery_id=delivery_id,
                success=result,
            )
            return result
        finally:
            loop.run_until_complete(webhook_sender.close())
            loop.close()
            
    except Exception as e:
        logger.error(
            "Webhook delivery task failed",
            delivery_id=delivery_id,
            error=str(e),
            exc_info=True,
        )
        return False
