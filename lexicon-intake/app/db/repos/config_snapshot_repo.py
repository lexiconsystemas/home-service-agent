"""Configuration snapshot repository for versioning and rollback."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.tables.config_snapshot import ConfigSnapshot


class ConfigSnapshotRepository:
    """Repository for configuration snapshot operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def create_snapshot(
        self,
        client_id: str,
        version: int,
        config_type: str,
        config_data: dict[str, Any],
        created_by: str,
        change_reason: str | None = None,
    ) -> ConfigSnapshot:
        """Create a new configuration snapshot."""
        snapshot = ConfigSnapshot(
            client_id=client_id,
            version=version,
            config_type=config_type,
            config_data=config_data,
            created_by=created_by,
            change_reason=change_reason,
        )
        
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot
    
    async def get_latest_snapshot(
        self,
        client_id: str,
        config_type: str,
    ) -> ConfigSnapshot | None:
        """Get the latest configuration snapshot for a client."""
        query = select(ConfigSnapshot).where(
            ConfigSnapshot.client_id == client_id,
            ConfigSnapshot.config_type == config_type,
        ).order_by(desc(ConfigSnapshot.version)).limit(1)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_snapshot_by_version(
        self,
        client_id: str,
        config_type: str,
        version: int,
    ) -> ConfigSnapshot | None:
        """Get a specific configuration snapshot by version."""
        query = select(ConfigSnapshot).where(
            ConfigSnapshot.client_id == client_id,
            ConfigSnapshot.config_type == config_type,
            ConfigSnapshot.version == version,
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_snapshots(
        self,
        client_id: str,
        config_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConfigSnapshot]:
        """Get all configuration snapshots for a client."""
        query = select(ConfigSnapshot).where(
            ConfigSnapshot.client_id == client_id
        )
        
        if config_type:
            query = query.where(ConfigSnapshot.config_type == config_type)
        
        query = query.order_by(desc(ConfigSnapshot.version)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_max_version(
        self,
        client_id: str,
        config_type: str,
    ) -> int:
        """Get the maximum version number for a client's configuration."""
        query = select(ConfigSnapshot.version).where(
            ConfigSnapshot.client_id == client_id,
            ConfigSnapshot.config_type == config_type,
        ).order_by(desc(ConfigSnapshot.version)).limit(1)
        
        result = await self.session.execute(query)
        max_version = result.scalar_one_or_none()
        return max_version if max_version is not None else 0
