"""Client configuration repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables.client_config import ClientConfig


class ClientRepository:
    """Repository for client configurations."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def get_by_client_id(self, client_id: str) -> ClientConfig | None:
        """Get client configuration by client_id."""
        result = await self.session.execute(
            select(ClientConfig).where(ClientConfig.client_id == client_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_to_number(self, to_number: str) -> ClientConfig | None:
        """Get client configuration by to_number."""
        result = await self.session.execute(
            select(ClientConfig).where(ClientConfig.to_number == to_number)
        )
        return result.scalar_one_or_none()
    
    async def create_client(
        self,
        client_id: str,
        to_number: str,
        greeting: str | None,
        rules_json: dict[str, Any],
        webhook_url: str | None,
        followup_enabled: bool = False,
        followup_confirmation_enabled: bool = False,
        followup_reminder_enabled: bool = False,
        followup_escalation_enabled: bool = False,
    ) -> ClientConfig:
        """Create a new client configuration."""
        client_config = ClientConfig(
            client_id=client_id,
            to_number=to_number,
            greeting=greeting,
            rules_json=rules_json,
            webhook_url=webhook_url,
            followup_enabled=followup_enabled,
            followup_confirmation_enabled=followup_confirmation_enabled,
            followup_reminder_enabled=followup_reminder_enabled,
            followup_escalation_enabled=followup_escalation_enabled,
        )
        
        self.session.add(client_config)
        await self.session.flush()
        
        return client_config
