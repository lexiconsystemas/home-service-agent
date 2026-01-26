"""Background task definitions."""

import asyncio
from typing import Any

import structlog

from app.adapters.messaging.twilio_sms import TwilioSMSAdapter
from app.adapters.messaging.sendgrid_email import SendGridEmailAdapter
from app.adapters.webhooks.webhook_sender import WebhookSender
from app.core.enums import DeliveryChannel, DeliveryPurpose, DeliveryStatus
from app.core.time import utc_now, format_timestamp
from app.db.repos.delivery_repo import DeliveryRepository
from app.db.repos.lead_repo import LeadRepository
from app.db.repos.client_repo import ClientRepository
from app.db.session import get_async_session_context

logger = structlog.get_logger()


def deliver_multi_channel_task(delivery_id: str) -> bool:
    """
    Background task to deliver lead via multiple channels.
    
    Args:
        delivery_id: Delivery record ID
        
    Returns:
        True if delivery succeeded, False otherwise
    """
    logger.info("Starting multi-channel delivery task", delivery_id=delivery_id)
    
    try:
        # Run async delivery in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _execute_delivery(delivery_id)
            )
            logger.info(
                "Multi-channel delivery task completed",
                delivery_id=delivery_id,
                success=result,
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(
            "Multi-channel delivery task failed",
            delivery_id=delivery_id,
            error=str(e),
            exc_info=True,
        )
        return False


def deliver_followup_task(delivery_id: str) -> bool:
    """
    Background task to deliver follow-up message.
    
    Args:
        delivery_id: Delivery record ID
        
    Returns:
        True if delivery succeeded, False otherwise
    """
    logger.info("Starting follow-up delivery task", delivery_id=delivery_id)
    
    try:
        # Run async delivery in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _execute_delivery(delivery_id)
            )
            logger.info(
                "Follow-up delivery task completed",
                delivery_id=delivery_id,
                success=result,
            )
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(
            "Follow-up delivery task failed",
            delivery_id=delivery_id,
            error=str(e),
            exc_info=True,
        )
        return False


async def _execute_delivery(delivery_id: str) -> bool:
    """
    Execute delivery based on stored routing decision.
    
    Args:
        delivery_id: Delivery record ID
        
    Returns:
        True if delivery succeeded, False otherwise
    """
    async with get_async_session_context() as db:
        delivery_repo = DeliveryRepository(db)
        lead_repo = LeadRepository(db)
        client_repo = ClientRepository(db)
        
        # Get delivery record
        delivery_records = await delivery_repo.get_by_lead_id(delivery_id)
        delivery_record = None
        
        for record in delivery_records:
            if str(record.id) == delivery_id:
                delivery_record = record
                break
        
        if not delivery_record:
            logger.error("Delivery record not found", delivery_id=delivery_id)
            return False
        
        # Get lead record to access stored routing decision
        lead_record = await lead_repo.get_by_lead_id(delivery_record.lead_id)
        if not lead_record:
            logger.error("Lead record not found", lead_id=delivery_record.lead_id)
            return False
        
        # Get client configuration
        client_config = await client_repo.get_by_client_id(lead_record.client_id)
        if not client_config:
            logger.error("Client config not found", client_id=lead_record.client_id)
            return False
        
        # Use stored routing decision instead of recomputing
        routing_config = _extract_stored_routing(lead_record, client_config)
        
        # Execute delivery based on channel
        success = False
        error_message = None
        status_code = None
        
        try:
            if delivery_record.channel == DeliveryChannel.WEBHOOK:
                success, error_message, status_code = await _deliver_webhook(
                    delivery_record, lead_record, routing_config
                )
            elif delivery_record.channel == DeliveryChannel.SMS:
                success, error_message, status_code = await _deliver_sms(
                    delivery_record, lead_record, routing_config
                )
            elif delivery_record.channel == DeliveryChannel.EMAIL:
                success, error_message, status_code = await _deliver_email(
                    delivery_record, lead_record, routing_config
                )
            else:
                error_message = f"Unsupported channel: {delivery_record.channel}"
                logger.error("Unsupported delivery channel", channel=delivery_record.channel)
            
            # Update delivery record
            status = DeliveryStatus.SENT if success else DeliveryStatus.FAILED
            
            # Check if this is the final failure (max retries exceeded)
            if not success and delivery_record.attempt_count >= 3:
                status = DeliveryStatus.FAILED_FINAL
                logger.warning(
                    "Delivery marked as final failure",
                    delivery_id=delivery_id,
                    attempts=delivery_record.attempt_count,
                )
            
            await delivery_repo.update_delivery_attempt(
                delivery_id=str(delivery_record.id),
                status=status,
                response_status_code=status_code,
                error_message=error_message,
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Delivery execution failed",
                delivery_id=delivery_id,
                channel=delivery_record.channel.value,
                error=str(e),
                exc_info=True,
            )
            
            # Update delivery record with error
            await delivery_repo.update_delivery_attempt(
                delivery_id=str(delivery_record.id),
                status=DeliveryStatus.FAILED,
                error_message=str(e),
            )
            
            return False


def _extract_stored_routing(lead_record, client_config) -> dict:
    """
    Extract routing configuration from stored lead record.
    
    Args:
        lead_record: Lead record with stored routing decision
        client_config: Client configuration for fallback
        
    Returns:
        Routing configuration dictionary
    """
    if lead_record.chosen_destinations:
        # Use stored routing decision
        return {
            "webhook_url": lead_record.chosen_destinations.get("webhook_url"),
            "sms_to_numbers": lead_record.chosen_destinations.get("sms_to_numbers", []),
            "email_to_addresses": lead_record.chosen_destinations.get("email_to_addresses", []),
        }
    else:
        # Fallback to base client configuration
        return {
            "webhook_url": client_config.webhook_url,
            "sms_to_numbers": client_config.sms_to_numbers or [],
            "email_to_addresses": client_config.email_to_addresses or [],
        }


async def _deliver_webhook(delivery_record, lead_record, routing_config: dict) -> tuple[bool, str | None, int | None]:
    """Deliver webhook payload."""
    webhook_sender = WebhookSender()
    
    try:
        # Use routing config webhook URL or fallback
        webhook_url = routing_config.get("webhook_url")
        if not webhook_url:
            return False, "No webhook URL configured", None
        
        # Use existing webhook sender logic with the correct URL
        success = await webhook_sender.send_webhook(str(delivery_record.id), webhook_url)
        return success, None, 200 if success else None
    finally:
        await webhook_sender.close()


async def _deliver_sms(delivery_record, lead_record, routing_config: dict) -> tuple[bool, str | None, int | None]:
    """Deliver SMS message."""
    sms_adapter = TwilioSMSAdapter()
    
    try:
        message = _generate_sms_message(delivery_record, lead_record, None)
        success, error_message, status_code = await sms_adapter.send_sms(
            to_number=delivery_record.destination,
            message=message,
        )
        return success, error_message, status_code
    finally:
        await sms_adapter.close()


async def _deliver_email(delivery_record, lead_record, routing_config: dict) -> tuple[bool, str | None, int | None]:
    """Deliver email message."""
    email_adapter = SendGridEmailAdapter()
    
    try:
        subject, body = _generate_email_content(delivery_record, lead_record, None)
        success, error_message, status_code = await email_adapter.send_email(
            to_address=delivery_record.destination,
            subject=subject,
            body=body,
        )
        return success, error_message, status_code
    finally:
        await email_adapter.close()


def _generate_sms_message(delivery_record, lead_record, client_config) -> str:
    """Generate SMS message based on purpose."""
    # Use stored message templates from client config or defaults
    if delivery_record.purpose.value == "LEAD_DELIVERY":
        # Lead summary to internal recipients
        return f"New lead: {lead_record.service_requested or 'Unknown'} from {lead_record.caller_phone}. Urgency: {lead_record.urgency.value}. Status: {lead_record.classification.value}."
    
    elif delivery_record.purpose.value == "FOLLOWUP_CONFIRMATION":
        # Confirmation to caller
        return f"Thanks — we received your request for {lead_record.service_requested or 'service'}. We'll follow up soon."
    
    elif delivery_record.purpose.value == "FOLLOWUP_REMINDER":
        # Reminder to caller
        return "Quick check-in: we're reviewing your request. Reply YES if you still need help today."
    
    elif delivery_record.purpose.value == "URGENT_ESCALATION":
        # Urgent escalation to internal team
        return f"URGENT lead: {lead_record.service_requested or 'Unknown'} from {lead_record.caller_phone} needs same-day service."
    
    else:
        return f"Notification about lead {lead_record.lead_id}"


def _generate_email_content(delivery_record, lead_record, client_config) -> tuple[str, str]:
    """Generate email subject and body."""
    if delivery_record.purpose.value == "LEAD_DELIVERY":
        # Lead summary email
        subject = f"New Lead: {lead_record.service_requested or 'Unknown'} ({lead_record.classification.value})"
        
        body = f"""Lead Summary:

Lead ID: {lead_record.lead_id}
Call ID: {lead_record.call_id}
Caller: {lead_record.caller_name or 'Not provided'}
Phone: {lead_record.caller_phone}
Service: {lead_record.service_requested or 'Not provided'}
Service Type: {lead_record.service_type_normalized.value if lead_record.service_type_normalized else 'Unknown'}
Urgency: {lead_record.urgency.value}
Budget: {lead_record.budget or 'Not specified'}
Location: {lead_record.location_zip or 'Not provided'}
Classification: {lead_record.classification.value}
Qualification: {lead_record.qualification_outcome}
Reason Codes: {', '.join(lead_record.reason_codes) if lead_record.reason_codes else 'None'}
Routing Profile: {lead_record.routing_profile_name or 'None'}
Time Window: {lead_record.time_window or 'None'}
Timestamp: {format_timestamp(lead_record.created_at)}
"""
        
        return subject, body
    
    else:
        # For other purposes, use simple format
        subject = f"Notification: {delivery_record.purpose.value.replace('_', ' ').title()}"
        body = f"This is a notification about {delivery_record.purpose.value.replace('_', ' ').lower()} for lead {lead_record.lead_id}."
        return subject, body
