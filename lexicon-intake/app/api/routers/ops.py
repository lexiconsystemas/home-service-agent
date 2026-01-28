"""Operations endpoints for delivery replay and admin functions."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.core.errors import LexiconError
from app.db.repos.audit_repo import AuditRepository
from app.db.repos.delivery_repo import DeliveryRepository
from app.db.repos.lead_repo import LeadRepository
from app.db.tables.delivery_record import DeliveryRecord, DeliveryStatus
from app.services.delivery_service import DeliveryService
from app.services.auth_service import AuthService
from app.settings import settings
from app.workers.queue import enqueue_delivery_task
import structlog

logger = structlog.get_logger()

router = APIRouter()


async def verify_admin_api_key(request: Request) -> tuple[str, bool]:
    """Verify admin API key from header. Returns (api_key, is_admin)."""
    api_key = request.headers.get("X-Admin-API-Key")
    if not api_key or api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin API key",
        )
    return api_key, True


async def verify_api_key(request: Request) -> tuple[str, bool, str | None]:
    """Verify API key from header. Returns (api_key, is_admin, client_id)."""
    api_key = request.headers.get("X-Admin-API-Key")
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
        )
    
    # Check if it's an admin API key
    if api_key == settings.admin_api_key:
        return api_key, True, None
    
    # Check if it's a client API key
    client_id = AuthService.extract_client_id_from_api_key(api_key)
    if client_id:
        return api_key, False, client_id
    
    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
    )


@router.post("/v1/delivery/{delivery_id}/replay")
async def replay_delivery(
    delivery_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth_info: tuple[str, bool] = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """
    Replay a failed delivery.
    
    Creates a new delivery attempt using the same payload.
    Enforces idempotency per delivery_id + replay_count.
    """
    delivery_repo = DeliveryRepository(session)
    lead_repo = LeadRepository(session)
    audit_repo = AuditRepository(session)
    
    # Get original delivery record
    delivery = await delivery_repo.get_by_id(delivery_id)
    if not delivery:
        raise HTTPException(
            status_code=404,
            detail=f"Delivery {delivery_id} not found",
        )
    
    # Check if delivery is in final failed state
    if not delivery.failed_final:
        raise HTTPException(
            status_code=400,
            detail=f"Delivery {delivery_id} is not in final failed state",
        )
    
    # Get lead record for context
    lead = await lead_repo.get_by_lead_id(delivery.lead_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail=f"Lead {delivery.lead_id} not found",
        )
    
    # Create new delivery record for replay
    new_delivery = await delivery_repo.create_delivery_record(
        lead_id=delivery.lead_id,
        channel=delivery.channel,
        purpose=delivery.purpose,
        destination=delivery.destination,
        payload=delivery.payload,
        max_attempts=delivery.max_attempts,
    )
    
    # Enqueue new delivery
    await enqueue_delivery_task(str(new_delivery.id))
    
    # Log audit event
    await audit_repo.create_audit_log(
        actor_type="ADMIN",
        actor_id="admin",  # TODO: Get from API key or request
        action="REPLAY_DELIVERY",
        target_type="delivery",
        target_id=str(new_delivery.id),
        before_state={
            "original_delivery_id": delivery_id,
            "original_status": delivery.status,
            "original_attempt_count": delivery.attempt_count,
        },
        after_state={
            "new_delivery_id": str(new_delivery.id),
            "new_status": new_delivery.status,
            "replay_timestamp": datetime.utcnow().isoformat(),
        },
        details={
            "lead_id": delivery.lead_id,
            "client_id": lead.client_id,
            "channel": delivery.channel.value,
            "purpose": delivery.purpose.value,
        },
    )
    
    logger.info(
        "Delivery replay created",
        original_delivery_id=delivery_id,
        new_delivery_id=str(new_delivery.id),
        lead_id=delivery.lead_id,
        channel=delivery.channel.value,
    )
    
    return {
        "original_delivery_id": delivery_id,
        "new_delivery_id": str(new_delivery.id),
        "lead_id": delivery.lead_id,
        "channel": delivery.channel.value,
        "purpose": delivery.purpose.value,
        "destination": delivery.destination,
        "status": new_delivery.status.value,
    }


@router.get("/v1/dlq")
async def get_dlq_deliveries(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth_info: tuple[str, bool, str | None] = Depends(verify_api_key),
    client_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get dead letter queue deliveries (final failed deliveries)."""
    api_key, is_admin, request_client_id = auth_info
    
    # Enforce tenant filtering
    if not is_admin:
        # Clients can only see their own DLQ items
        if client_id and client_id != request_client_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: cannot access other client's data",
            )
        client_id = request_client_id
    elif client_id is None:
        # Admins can see all, but if they specify a client_id, use it
        client_id = client_id
    
    delivery_repo = DeliveryRepository(session)
    
    # Get failed final deliveries
    deliveries = await delivery_repo.get_failed_final_deliveries(
        client_id=client_id,
        limit=limit,
        offset=offset,
    )
    
    return {
        "deliveries": [
            {
                "id": str(delivery.id),
                "lead_id": delivery.lead_id,
                "channel": delivery.channel.value,
                "purpose": delivery.purpose.value,
                "destination": delivery.destination,
                "status": delivery.status.value,
                "attempt_count": delivery.attempt_count,
                "max_attempts": delivery.max_attempts,
                "failure_reason": delivery.failure_reason,
                "last_attempt_at": delivery.last_attempt_at.isoformat() if delivery.last_attempt_at else None,
                "created_at": delivery.created_at.isoformat(),
            }
            for delivery in deliveries
        ],
        "count": len(deliveries),
        "limit": limit,
        "offset": offset,
    }


@router.get("/v1/audit-logs")
async def get_audit_logs(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth_info: tuple[str, bool, str | None] = Depends(verify_api_key),
    target_type: str | None = None,
    target_id: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    client_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Get audit logs with optional filters."""
    api_key, is_admin, request_client_id = auth_info
    
    # Enforce tenant filtering
    if not is_admin:
        # Clients can only see their own audit logs
        if client_id and client_id != request_client_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: cannot access other client's data",
            )
        client_id = request_client_id
    elif client_id is None:
        # Admins can see all, but if they specify a client_id, use it
        client_id = client_id
    
    audit_repo = AuditRepository(session)
    
    logs = await audit_repo.get_audit_logs(
        target_type=target_type,
        target_id=target_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        client_id=client_id,
        limit=limit,
        offset=offset,
    )
    
    return {
        "logs": [
            {
                "id": str(log.id),
                "ts": log.ts.isoformat(),
                "actor_type": log.actor_type,
                "actor_id": log.actor_id,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "before_state": log.before_state,
                "after_state": log.after_state,
                "details": log.details,
            }
            for log in logs
        ],
        "count": len(logs),
        "limit": limit,
        "offset": offset,
    }
