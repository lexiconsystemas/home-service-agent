"""Admin endpoints for client configuration management."""

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.security import sanitize_phone_number
from app.db.session import get_async_session
from app.db.repos.client_repo import ClientRepository
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


async def verify_admin_api_key(x_admin_api_key: str = Header(...)) -> None:
    """Verify admin API key."""
    if not settings.admin_api_key:
        raise HTTPException(status_code=500, detail="Admin API key not configured")
    
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")


@router.put("/clients/{client_id}/delivery")
async def update_delivery_config(
    client_id: str,
    config: DeliveryConfigUpdate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """
    Update client delivery configuration.
    
    Args:
        client_id: Client identifier
        config: Delivery configuration update
        db: Database session
        
    Returns:
        Updated configuration
    """
    client_repo = ClientRepository(db)
    
    # Get existing client config
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    
    # Update delivery configuration
    client_config.delivery_channels = config.delivery_channels
    client_config.webhook_url = config.webhook_url
    client_config.sms_to_numbers = config.sms_to_numbers
    client_config.email_to_addresses = config.email_to_addresses
    
    await db.commit()
    
    logger.info(
        "Client delivery configuration updated",
        client_id=client_id,
        delivery_channels=config.delivery_channels,
        sms_count=len(config.sms_to_numbers),
        email_count=len(config.email_to_addresses),
    )
    
    return {
        "client_id": client_id,
        "delivery_channels": client_config.delivery_channels,
        "webhook_url": client_config.webhook_url,
        "sms_to_numbers": client_config.sms_to_numbers,
        "email_to_addresses": client_config.email_to_addresses,
    }


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
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    
    # Update message templates
    templates_dict = {
        "sms_summary_template": templates.sms_summary_template,
        "sms_confirmation_template": templates.sms_confirmation_template,
        "sms_reminder_template": templates.sms_reminder_template,
        "sms_escalation_template": templates.sms_escalation_template,
        "email_subject_template": templates.email_subject_template,
        "email_body_template": templates.email_body_template,
    }
    
    # Remove None values to keep existing templates
    templates_dict = {k: v for k, v in templates_dict.items() if v is not None}
    
    # Merge with existing templates
    existing_templates = client_config.message_templates or {}
    existing_templates.update(templates_dict)
    client_config.message_templates = existing_templates
    
    await db.commit()
    
    logger.info(
        "Client message templates updated",
        client_id=client_id,
        template_count=len(templates_dict),
    )
    
    return {
        "client_id": client_id,
        "message_templates": client_config.message_templates,
    }


@router.put("/clients/{client_id}/routing")
async def update_routing_config(
    client_id: str,
    config: RoutingConfigUpdate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """
    Update client routing configuration.
    
    Args:
        client_id: Client identifier
        config: Routing configuration update
        db: Database session
        
    Returns:
        Updated configuration
    """
    client_repo = ClientRepository(db)
    routing_service = RoutingService()
    
    # Get existing client config
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    
    # Validate routing configuration
    routing_dict = config.dict()
    is_valid, errors = routing_service.validate_routing_config(routing_dict)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid routing configuration: {'; '.join(errors)}"
        )
    
    # Update routing configuration
    client_config.routing_json = routing_dict
    
    await db.commit()
    
    logger.info(
        "Client routing configuration updated",
        client_id=client_id,
        timezone=config.timezone,
        profile_count=len(config.profiles),
    )
    
    return {
        "client_id": client_id,
        "routing_json": client_config.routing_json,
    }


@router.get("/clients/{client_id}/routing")
async def get_routing_config(
    client_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """
    Get client routing configuration.
    
    Args:
        client_id: Client identifier
        db: Database session
        
    Returns:
        Routing configuration
    """
    client_repo = ClientRepository(db)
    
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    
    return {
        "client_id": client_id,
        "routing_json": client_config.routing_json,
    }


@router.get("/clients/{client_id}")
async def get_client_config(
    client_id: str,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(verify_admin_api_key),
) -> dict[str, Any]:
    """
    Get complete client configuration.
    
    Args:
        client_id: Client identifier
        db: Database session
        
    Returns:
        Client configuration
    """
    client_repo = ClientRepository(db)
    
    client_config = await client_repo.get_by_client_id(client_id)
    if not client_config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    
    return {
        "client_id": client_config.client_id,
        "to_number": client_config.to_number,
        "greeting": client_config.greeting,
        "delivery_channels": client_config.delivery_channels,
        "webhook_url": client_config.webhook_url,
        "sms_to_numbers": client_config.sms_to_numbers,
        "email_to_addresses": client_config.email_to_addresses,
        "message_templates": client_config.message_templates,
        "followup_flags": client_config.followup_flags,
        "routing_json": client_config.routing_json,
        "rules_json": client_config.rules_json,
    }
