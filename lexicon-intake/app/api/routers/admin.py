"""Admin endpoints for client configuration management."""

import re
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.security import sanitize_phone_number
from app.db.session import get_async_session
from app.db.repos.client_repo import ClientRepository
from app.db.repos.audit_repo import AuditRepository
from app.db.repos.config_snapshot_repo import ConfigSnapshotRepository
from app.services.routing_service import RoutingService
from app.settings import settings

logger = structlog.get_logger()

router = APIRouter()


# Pydantic models for configuration updates
class DeliveryConfigUpdate(BaseModel):
    """Model for updating delivery configuration."""
    
    delivery_channels: list[str]
    webhook_url: str | None = None
    sms_to_numbers: list[str] = []
    email_to_addresses: list[EmailStr] = []
    
    @validator("delivery_channels")
    def validate_delivery_channels(cls, v):
        """Validate delivery channels."""
        allowed = ["WEBHOOK", "SMS", "EMAIL"]
        for channel in v:
            if channel not in allowed:
                raise ValueError(f"Invalid delivery channel: {channel}. Allowed: {allowed}")
        return v
    
    @validator("sms_to_numbers")
    def validate_phone_numbers(cls, v):
        """Validate phone numbers."""
        for phone in v:
            # Basic E.164 validation
            if not re.match(r"^\+\d{10,15}$", phone):
                raise ValueError(f"Invalid phone number format: {phone}. Must be E.164 format (+country_number)")
        return v


class FollowupConfigUpdate(BaseModel):
    """Model for updating follow-up configuration."""
    
    send_confirmation_to_caller: bool = False
    send_reminder_to_caller: bool = False
    reminder_delay_minutes: int = 30
    urgent_escalation: bool = False
    
    @validator("reminder_delay_minutes")
    def validate_delay_minutes(cls, v):
        """Validate reminder delay."""
        if v < 5 or v > 1440:  # 5 minutes to 24 hours
            raise ValueError("reminder_delay_minutes must be between 5 and 1440")
        return v


class MessageTemplatesUpdate(BaseModel):
    """Model for updating message templates."""
    
    sms_summary_template: str | None = None
    sms_confirmation_template: str | None = None
    sms_reminder_template: str | None = None
    sms_escalation_template: str | None = None
    email_subject_template: str | None = None
    email_body_template: str | None = None


class RoutingConfigUpdate(BaseModel):
    """Model for updating routing configuration."""

    timezone: str
    business_hours: dict[str, Any]
    profiles: list[dict[str, Any]]

    @validator("profiles")
    def validate_profiles(cls, v):
        """Validate routing profiles."""
        if not v:
            raise ValueError("At least one routing profile is required")
        return v


class CreateClientRequest(BaseModel):
    """Model for creating a new client."""

    client_id: str
    to_number: str
    business_name: str
    greeting_message: str = "Thank you for calling. How can we help you today?"
    delivery_channels: list[str] = ["WEBHOOK"]
    webhook_url: str | None = None

    @validator("client_id")
    def validate_client_id(cls, v):
        """Validate client ID format."""
        if not v or len(v) < 3:
            raise ValueError("client_id must be at least 3 characters")
        return v

    @validator("to_number")
    def validate_to_number(cls, v):
        """Validate phone number format."""
        if not re.match(r"^\+\d{10,15}$", v):
            raise ValueError("to_number must be E.164 format (+country_number)")
        return v


async def verify_admin_api_key(x_admin_api_key: str = Header(...)) -> None:
    """Verify admin API key."""
    if not settings.admin_api_key:
        raise HTTPException(status_code=500, detail="Admin API key not configured")
    
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")


@router.put("/clients/{client_id}/followup")
async def update_followup_config(
    client_id: str,
    config: FollowupConfigUpdate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """
    Update client follow-up configuration.
    
    Args:
        client_id: Client identifier
        config: Follow-up configuration update
        db: Database session
        
    Returns:
        Updated configuration
    """
    client_repo = ClientRepository(db)
    
    # Get existing client config
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    
    # Update follow-up configuration
    followup_flags = {
        "send_confirmation_to_caller": config.send_confirmation_to_caller,
        "send_reminder_to_caller": config.send_reminder_to_caller,
        "reminder_delay_minutes": config.reminder_delay_minutes,
        "urgent_escalation": config.urgent_escalation,
    }
    
    client_config.followup_flags = followup_flags
    
    # Update legacy fields for backward compatibility
    client_config.followup_enabled = any(followup_flags.values())
    client_config.followup_confirmation_enabled = config.send_confirmation_to_caller
    client_config.followup_reminder_enabled = config.send_reminder_to_caller
    client_config.followup_escalation_enabled = config.urgent_escalation
    
    await db.commit()
    
    logger.info(
        "Client follow-up configuration updated",
        client_id=client_id,
        followup_flags=followup_flags,
    )
    
    return {
        "client_id": client_id,
        "followup_flags": client_config.followup_flags,
    }


@router.put("/clients/{client_id}/templates")
async def update_message_templates(
    client_id: str,
    templates: MessageTemplatesUpdate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """
    Update client message templates.
    
    Args:
        client_id: Client identifier
        templates: Message templates update
        db: Database session
        
    Returns:
        Updated templates
    """
    client_repo = ClientRepository(db)
    
    # Get existing client config
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    # Store previous configuration
    old_config = client_config.message_templates.copy() if client_config.message_templates else {}
    
    # Initialize audit repository
    audit_repo = AuditRepository(db)
    
    # Update message templates
    client_config.message_templates = templates.dict()
    await db.flush()
    
    # Log audit event
    await audit_repo.create_audit_log(
        actor_type="ADMIN",
        actor_id="admin",
        action="CONFIG_UPDATE",
        target_type="message_templates",
        target_id=client_id,
        before_state=old_config,
        after_state=templates.dict(),
    )
    
    return {
        "client_id": client_id,
        "message_templates": templates.dict(),
    }


@router.put("/v1/admin/clients/{client_id}/routing")
async def update_routing_config(
    client_id: str,
    config: RoutingConfigUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_key: str = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """Update routing configuration for a client."""
    client_repo = ClientRepository(session)
    audit_repo = AuditRepository(session)
    snapshot_repo = ConfigSnapshotRepository(session)
    routing_service = RoutingService()
    
    # Get client configuration
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    # Validate routing configuration
    is_valid, errors = routing_service.validate_routing_config(config.dict())
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid routing configuration",
                "details": errors,
            },
        )
    
    # Store previous configuration snapshot
    if client_config.routing_json:
        current_version = await snapshot_repo.get_max_version(client_id, "routing_config")
        await snapshot_repo.create_snapshot(
            client_id=client_id,
            version=current_version + 1,
            config_type="routing_config",
            config_data=client_config.routing_json,
            created_by="admin",
            change_reason="Configuration update",
        )
    
    # Update routing configuration
    old_config = client_config.routing_json.copy() if client_config.routing_json else {}
    client_config.routing_json = config.dict()
    client_config.version = (client_config.version or 1) + 1
    client_config.updated_at = datetime.utcnow()
    
    await session.flush()
    
    # Log audit event
    await audit_repo.create_audit_log(
        actor_type="ADMIN",
        actor_id="admin",
        action="CONFIG_UPDATE",
        target_type="routing_config",
        target_id=client_id,
        before_state=old_config,
        after_state=config.dict(),
        details={
            "version": client_config.version,
            "config_type": "routing_config",
        },
    )
    
    logger.info(
        "Routing configuration updated",
        client_id=client_id,
        version=client_config.version,
        profiles_count=len(config.profiles),
    )
    
    return {
        "client_id": client_id,
        "routing_json": config.dict(),
        "version": client_config.version,
    }


@router.get("/v1/admin/clients/{client_id}/routing")
async def get_routing_config(
    client_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_key: str = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """Get routing configuration for a client."""
    client_repo = ClientRepository(session)
    
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    return {
        "client_id": client_id,
        "routing_json": client_config.routing_json,
        "version": client_config.version,
    }


@router.post("/v1/admin/clients/{client_id}/rollback/{version}")
async def rollback_config(
    client_id: str,
    version: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_key: str = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """Rollback client configuration to a specific version."""
    client_repo = ClientRepository(session)
    audit_repo = AuditRepository(session)
    snapshot_repo = ConfigSnapshotRepository(session)
    
    # Get client configuration
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    # Get snapshot to rollback to
    snapshot = await snapshot_repo.get_snapshot_by_version(
        client_id=client_id,
        config_type="routing_config",
        version=version,
    )
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Configuration version {version} not found",
        )
    
    # Store current configuration as new snapshot
    if client_config.routing_json:
        current_version = await snapshot_repo.get_max_version(client_id, "routing_config")
        await snapshot_repo.create_snapshot(
            client_id=client_id,
            version=current_version + 1,
            config_type="routing_config",
            config_data=client_config.routing_json,
            created_by="admin",
            change_reason=f"Rollback to version {version}",
        )
    
    # Rollback configuration
    old_config = client_config.routing_json.copy() if client_config.routing_json else {}
    client_config.routing_json = snapshot.config_data
    client_config.version = (client_config.version or 1) + 1
    client_config.updated_at = datetime.utcnow()
    
    await session.flush()
    
    # Log audit event
    await audit_repo.create_audit_log(
        actor_type="ADMIN",
        actor_id="admin",
        action="CONFIG_ROLLBACK",
        target_type="routing_config",
        target_id=client_id,
        before_state=old_config,
        after_state=snapshot.config_data,
        details={
            "rollback_to_version": version,
            "new_version": client_config.version,
            "config_type": "routing_config",
        },
    )
    
    logger.info(
        "Configuration rolled back",
        client_id=client_id,
        rollback_to_version=version,
        new_version=client_config.version,
    )
    
    return {
        "client_id": client_id,
        "routing_json": snapshot.config_data,
        "rollback_to_version": version,
        "current_version": client_config.version,
    }


@router.get("/v1/admin/clients/{client_id}/config-history")
async def get_config_history(
    client_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_key: str = Depends(verify_admin_api_key),
    config_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get configuration history for a client."""
    snapshot_repo = ConfigSnapshotRepository(session)
    
    snapshots = await snapshot_repo.get_all_snapshots(
        client_id=client_id,
        config_type=config_type,
        limit=limit,
        offset=offset,
    )
    
    return {
        "client_id": client_id,
        "snapshots": [
            {
                "id": str(snapshot.id),
                "version": snapshot.version,
                "config_type": snapshot.config_type,
                "created_at": snapshot.created_at.isoformat(),
                "created_by": snapshot.created_by,
                "change_reason": snapshot.change_reason,
            }
            for snapshot in snapshots
        ],
        "count": len(snapshots),
        "limit": limit,
        "offset": offset,
    }


@router.put("/v1/admin/clients/{client_id}/delivery")
async def update_delivery_config(
    client_id: str,
    config: DeliveryConfigUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_key: str = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """Update delivery configuration for a client."""
    client_repo = ClientRepository(session)
    audit_repo = AuditRepository(session)
    
    # Get client configuration
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    # Store previous configuration
    old_config = {
        "delivery_channels": client_config.delivery_channels,
        "webhook_url": client_config.webhook_url,
        "sms_to_numbers": client_config.sms_to_numbers,
        "email_to_addresses": client_config.email_to_addresses,
    }
    
    # Update delivery configuration
    client_config.delivery_channels = config.delivery_channels
    client_config.webhook_url = config.webhook_url
    client_config.sms_to_numbers = config.sms_to_numbers
    client_config.email_to_addresses = config.email_to_addresses
    client_config.version = (client_config.version or 1) + 1
    client_config.updated_at = datetime.utcnow()
    
    await session.flush()
    
    # Log audit event
    await audit_repo.create_audit_log(
        actor_type="ADMIN",
        actor_id="admin",
        action="CONFIG_UPDATE",
        target_type="delivery_config",
        target_id=client_id,
        before_state=old_config,
        after_state=config.dict(),
        details={
            "version": client_config.version,
            "config_type": "delivery_config",
        },
    )
    
    return {
        "client_id": client_id,
        "delivery_config": config.dict(),
        "version": client_config.version,
    }


@router.get("/v1/admin/clients/{client_id}")
async def get_client_config(
    client_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_key: str = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """Get complete client configuration."""
    client_repo = ClientRepository(session)
    
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(
            status_code=404,
            detail=f"Client {client_id} not found",
        )
    
    return {
        "client_id": client_id,
        "to_number": client_config.to_number,
        "greeting_message": client_config.greeting_message,
        "rules_json": client_config.rules_json,
        "routing_json": client_config.routing_json,
        "delivery_channels": client_config.delivery_channels,
        "webhook_url": client_config.webhook_url,
        "sms_to_numbers": client_config.sms_to_numbers,
        "email_to_addresses": client_config.email_to_addresses,
        "message_templates": client_config.message_templates,
        "followup_flags": client_config.followup_flags,
        "client_api_key": client_config.client_api_key,
        "version": client_config.version,
        "updated_at": client_config.updated_at.isoformat() if client_config.updated_at else None,
    }


@router.post("/clients")
async def create_client(
    client_data: CreateClientRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    api_key: str = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """Create a new client with API key."""
    from app.db.tables.client_config import ClientConfig

    client_repo = ClientRepository(session)

    # Check if client_id already exists
    existing = await client_repo.get_by_client_id(client_data.client_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Client {client_data.client_id} already exists",
        )

    # Check if to_number already exists
    existing_number = await client_repo.get_by_to_number(client_data.to_number)
    if existing_number:
        raise HTTPException(
            status_code=400,
            detail=f"Phone number {client_data.to_number} already in use",
        )

    # Generate API key for the client
    client_api_key = f"lexicon_client_{client_data.client_id}_{secrets.token_urlsafe(32)}"

    # Create client configuration
    client_config = ClientConfig(
        client_id=client_data.client_id,
        to_number=client_data.to_number,
        greeting_message=client_data.greeting_message,
        rules_json={"business_name": client_data.business_name},
        delivery_channels=client_data.delivery_channels,
        webhook_url=client_data.webhook_url,
        client_api_key=client_api_key,
        message_templates={},
        followup_flags={},
        sms_to_numbers=[],
        email_to_addresses=[],
    )

    session.add(client_config)
    await session.commit()

    logger.info(
        "Client created",
        client_id=client_data.client_id,
        to_number=client_data.to_number,
    )

    return {
        "success": True,
        "client_id": client_data.client_id,
        "to_number": client_data.to_number,
        "client_api_key": client_api_key,
        "message": "Client created successfully. Save the client_api_key - it won't be shown again.",
    }
