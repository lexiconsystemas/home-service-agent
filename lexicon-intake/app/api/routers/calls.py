"""Call event processing endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.errors import DuplicateCallError, RateLimitExceededError, ValidationError
from app.core.idempotency import IdempotencyManager
from app.core.rate_limit import check_rate_limit
from app.core.security import sanitize_input, sanitize_phone_number
from app.db.session import get_async_session
from app.db.repos.client_repo import ClientRepository
from app.db.repos.lead_repo import LeadRepository
from app.domain.models.call_event import CallEvent, CallEventResponse
from app.services.intake_service import IntakeService

logger = structlog.get_logger()

router = APIRouter()


@router.post("/inbound", response_model=CallEventResponse)
async def inbound_call(
    call_event: CallEvent,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> CallEventResponse:
    """
    Process inbound call event.
    
    Args:
        call_event: Call event data
        request: FastAPI request object
        db: Database session
        
    Returns:
        Call event processing response
        
    Raises:
        HTTPException: For various error conditions
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Rate limiting check
        if not await check_rate_limit(client_ip):
            raise RateLimitExceededError("Rate limit exceeded")
        
        # Idempotency check
        if not await IdempotencyManager.check_and_record_call_id(call_event.call_id):
            raise DuplicateCallError(f"Duplicate call_id: {call_event.call_id}")
        
        # Sanitize inputs
        sanitized_from_number = sanitize_phone_number(call_event.from_number)
        sanitized_to_number = sanitize_phone_number(call_event.to_number)
        sanitized_caller_name = sanitize_input(call_event.caller_name) if call_event.caller_name else None
        sanitized_service_requested = sanitize_input(call_event.service_requested) if call_event.service_requested else None
        
        # Update call event with sanitized data
        call_event.from_number = sanitized_from_number
        call_event.to_number = sanitized_to_number
        call_event.caller_name = sanitized_caller_name
        call_event.service_requested = sanitized_service_requested
        
        # Process the call through intake service
        intake_service = IntakeService(db)
        result = await intake_service.process_inbound_call(call_event)
        
        logger.info(
            "Call processed successfully",
            call_id=call_event.call_id,
            lead_id=result.lead_id,
            classification=result.classification,
            client_ip=client_ip,
        )
        
        return result
        
    except DuplicateCallError as e:
        logger.warning("Duplicate call rejected", call_id=call_event.call_id)
        raise HTTPException(status_code=409, detail={"error": "duplicate_call", "message": str(e)})
    
    except RateLimitExceededError as e:
        logger.warning("Rate limit exceeded", client_ip=client_ip)
        raise HTTPException(status_code=429, detail={"error": "rate_limit_exceeded", "message": str(e)})
    
    except ValidationError as e:
        logger.warning("Validation failed", call_id=call_event.call_id, error=str(e))
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": str(e)})
    
    except Exception as e:
        logger.error(
            "Unexpected error processing call",
            call_id=call_event.call_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail={"error": "internal_error", "message": "Internal server error"})
