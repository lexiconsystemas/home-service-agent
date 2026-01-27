"""Client API endpoints for limited client access to their own configuration."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.core.errors import LexiconError
from app.db.repos.client_repo import ClientRepository
from app.services.auth_service import AuthService
import structlog

logger = structlog.get_logger()

router = APIRouter()


async def verify_client_api_key(request: Request) -> str:
    """Verify client API key from header and extract client ID."""
    api_key = request.headers.get("X-Client-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Client API key required",
        )
    
    client_id = AuthService.extract_client_id_from_api_key(api_key)
    if not client_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid client API key format",
        )
    
    return client_id


@router.get("/v1/clients/me")
async def get_my_config(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
) -> dict[str, Any]:
    """Get current client's configuration (read-only access)."""
    client_repo = ClientRepository(session)
    
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    # Verify API key matches stored hash
    if not client_config.client_api_key:
        raise HTTPException(
            status_code=401,
            detail="Client API key not configured",
        )
    
    if not AuthService.verify_api_key(
        request.headers.get("X-Client-API-Key"),
        client_config.client_api_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid client API key",
        )
    
    # Return sanitized client data
    client_data = {
        "client_id": client_config.client_id,
        "to_number": client_config.to_number,
        "greeting_message": client_config.greeting_message,
        "delivery_channels": client_config.delivery_channels,
        "message_templates": client_config.message_templates,
        "followup_flags": client_config.followup_flags,
        "version": client_config.version,
        "updated_at": client_config.updated_at.isoformat() if client_config.updated_at else None,
    }
    
    logger.info(
        "Client configuration accessed",
        client_id=client_id,
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    
    return client_data


@router.get("/v1/clients/me/delivery-status")
async def get_my_delivery_status(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get delivery status for current client's leads."""
    from app.db.repos.lead_repo import LeadRepository
    from app.db.repos.delivery_repo import DeliveryRepository
    
    # Verify client exists and API key is valid
    client_repo = ClientRepository(session)
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    if not AuthService.verify_api_key(
        request.headers.get("X-Client-API-Key"),
        client_config.client_api_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid client API key",
        )
    
    # Get leads and delivery status
    lead_repo = LeadRepository(session)
    delivery_repo = DeliveryRepository(session)
    
    leads = await lead_repo.get_leads_by_client(client_id, limit=limit, offset=offset)
    
    delivery_status = []
    for lead in leads:
        deliveries = await delivery_repo.get_by_lead_id(lead.lead_id)
        
        delivery_status.append({
            "lead_id": lead.lead_id,
            "caller_phone": lead.caller_phone,
            "service_requested": lead.service_requested,
            "classification": lead.classification.value,
            "created_at": lead.created_at.isoformat(),
            "scheduled_window_label": lead.scheduled_window_label,
            "deliveries": [
                {
                    "id": str(delivery.id),
                    "channel": delivery.channel.value,
                    "purpose": delivery.purpose.value,
                    "status": delivery.status.value,
                    "attempt_count": delivery.attempt_count,
                    "failed_final": delivery.failed_final,
                    "created_at": delivery.created_at.isoformat(),
                }
                for delivery in deliveries
            ],
        })
    
    return {
        "client_id": client_id,
        "delivery_status": delivery_status,
        "count": len(delivery_status),
        "limit": limit,
        "offset": offset,
    }
