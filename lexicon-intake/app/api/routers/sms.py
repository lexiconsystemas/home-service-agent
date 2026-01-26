"""SMS inbound webhook for scheduling responses."""

from datetime import datetime
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session
from app.core.errors import LexiconError
from app.db.repos.audit_repo import AuditRepository
from app.db.repos.lead_repo import LeadRepository
from app.services.scheduling_service import SchedulingService
from app.settings import settings
import structlog

logger = structlog.get_logger()

router = APIRouter()


async def verify_twilio_signature(request: Request) -> bool:
    """Verify Twilio webhook signature."""
    try:
        from twilio.request_validator import RequestValidator
        
        # Get the signature from headers
        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            logger.warning("Missing Twilio signature header")
            return False
        
        # Get the URL and request body
        url = str(request.url)
        body = await request.body()
        
        # Create validator with Twilio auth token
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        
        # Verify the signature
        is_valid = validator.validate(
            url,
            body,
            signature
        )
        
        if not is_valid:
            logger.warning("Invalid Twilio signature", signature=signature[:20])
        
        return is_valid
        
    except ImportError:
        logger.error("Twilio library not installed - signature verification disabled")
        return False
    except Exception as e:
        logger.error("Error verifying Twilio signature", error=str(e))
        return False


@router.post("/v1/sms/inbound")
async def handle_inbound_sms(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """
    Handle inbound SMS responses for scheduling.
    
    Expected Twilio webhook format:
    - From: Caller phone number
    - To: Our Twilio number
    - Body: SMS response (e.g., "1", "2", "3")
    """
    # Verify Twilio signature
    if not await verify_twilio_signature(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )
    
    # Parse form data
    form_data = await request.form()
    
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    body = form_data.get("Body", "").strip()
    
    if not from_number or not body:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields",
        )
    
    lead_repo = LeadRepository(session)
    audit_repo = AuditRepository(session)
    scheduling_service = SchedulingService(lead_repo)
    
    # Find lead by caller phone
    # Note: This is a simplified approach. In production, you might want
    # to track the SMS conversation more robustly
    leads = await lead_repo.get_leads_by_client("demo", limit=10)  # TODO: Get client_id from to_number
    
    target_lead = None
    for lead in leads:
        if lead.caller_phone == from_number and lead.classification.value == "QUALIFIED":
            if not lead.scheduled_window_label:  # Only consider leads without scheduling
                target_lead = lead
                break
    
    if not target_lead:
        logger.warning(
            "No qualified lead found for SMS response",
            from_number=from_number,
            body=body,
        )
        return {"status": "ignored", "reason": "no_matching_lead"}
    
    # Get routing config to check if scheduling is enabled
    # TODO: This should be stored with the lead or retrieved from client config
    routing_config = {
        "scheduling": {
            "enabled": True,
            "windows": [
                {"label": "Today 2–4pm", "start_offset_min": 0, "end_offset_min": 120},
                {"label": "Today 4–6pm", "start_offset_min": 120, "end_offset_min": 240},
                {"label": "Tomorrow Morning", "start_offset_min": 1440, "end_offset_min": 1800}
            ]
        }
    }
    
    # Check if scheduling should be offered
    if not scheduling_service.should_offer_scheduling(target_lead.classification, routing_config):
        return {"status": "ignored", "reason": "scheduling_not_enabled"}
    
    # Generate available windows
    available_windows = scheduling_service.generate_scheduling_windows(
        base_time=datetime.utcnow(),
        timezone_str="America/New_York",  # TODO: Get from lead record
        windows_config=routing_config["scheduling"]["windows"],
    )
    
    # Process the response
    success, error_message, selected_window = await scheduling_service.process_scheduling_response(
        lead_id=target_lead.lead_id,
        response=body,
        available_windows=available_windows,
    )
    
    # Log audit event
    await audit_repo.create_audit_log(
        actor_type="SYSTEM",
        actor_id="sms_webhook",
        action="SCHEDULING_RESPONSE",
        target_type="lead",
        target_id=target_lead.lead_id,
        before_state={
            "scheduled_window_label": target_lead.scheduled_window_label,
            "sms_response": body,
        },
        after_state={
            "scheduled_window_label": selected_window["label"] if selected_window else None,
            "success": success,
        },
        details={
            "from_number": from_number,
            "to_number": to_number,
            "error_message": error_message,
        },
    )
    
    if success and selected_window:
        # Generate confirmation message
        confirmation = scheduling_service.generate_confirmation_message(selected_window)
        
        logger.info(
            "Scheduling response processed successfully",
            lead_id=target_lead.lead_id,
            selected_window=selected_window["label"],
            from_number=from_number,
        )
        
        return {
            "status": "success",
            "lead_id": target_lead.lead_id,
            "selected_window": selected_window["label"],
            "confirmation_message": confirmation,
        }
    
    else:
        # Generate error response message
        error_response = error_message or "Invalid response. Please reply with a number from the list."
        
        logger.warning(
            "Scheduling response failed",
            lead_id=target_lead.lead_id,
            from_number=from_number,
            body=body,
            error_message=error_message,
        )
        
        return {
            "status": "error",
            "lead_id": target_lead.lead_id,
            "error_message": error_response,
        }
