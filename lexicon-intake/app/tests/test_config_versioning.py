"""Tests for configuration versioning and rollback functionality."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from app.api.routers.admin import update_routing_config, rollback_config, get_config_history
from app.db.repos.config_snapshot_repo import ConfigSnapshotRepository
from app.db.repos.client_repo import ClientRepository


class TestConfigVersioning:
    """Test cases for configuration versioning and rollback."""
    
    @pytest.mark.asyncio
    async def test_config_update_increments_version(self):
        """Test that configuration updates increment the version number."""
        # Mock client config
        client_config = AsyncMock()
        client_config.client_id = "test-client"
        client_config.routing_json = {"old": "config"}
        client_config.version = 2
        
        # Mock repositories
        client_repo = AsyncMock()
        client_repo.get_by_client_id.return_value = client_config
        
        snapshot_repo = AsyncMock()
        snapshot_repo.get_max_version.return_value = 2
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Mock routing service
        with patch('app.api.routers.admin.RoutingService') as mock_routing_service:
            mock_routing_service.return_value.validate_routing_config.return_value = (True, [])
            
            # Update configuration
            result = await update_routing_config(
                client_id="test-client",
                config={"new": "config"},
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            
            # Verify version was incremented
            assert result["version"] == 3
            assert client_config.version == 3
    
    @pytest.mark.asyncio
    async def test_config_update_creates_snapshot(self):
        """Test that configuration updates create snapshots."""
        # Mock client config
        client_config = AsyncMock()
        client_config.client_id = "test-client"
        client_config.routing_json = {"old": "config"}
        client_config.version = 1
        
        # Mock repositories
        client_repo = AsyncMock()
        client_repo.get_by_client_id.return_value = client_config
        
        snapshot_repo = AsyncMock()
        snapshot_repo.get_max_version.return_value = 1
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Mock routing service
        with patch('app.api.routers.admin.RoutingService') as mock_routing_service:
            mock_routing_service.return_value.validate_routing_config.return_value = (True, [])
            
            # Update configuration
            await update_routing_config(
                client_id="test-client",
                config={"new": "config"},
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            
            # Verify snapshot was created
            snapshot_repo.create_snapshot.assert_called_once()
            snapshot_call = snapshot_repo.create_snapshot.call_args[1]
            assert snapshot_call["client_id"] == "test-client"
            assert snapshot_call["version"] == 2
            assert snapshot_call["config_type"] == "routing_config"
            assert snapshot_call["config_data"] == {"old": "config"}
            assert snapshot_call["created_by"] == "admin"
            assert snapshot_call["change_reason"] == "Configuration update"
    
    @pytest.mark.asyncio
    async def test_rollback_to_previous_version(self):
        """Test rolling back to a previous configuration version."""
        # Mock snapshot
        snapshot = AsyncMock()
        snapshot.config_data = {"old": "config", "version": 2}
        
        # Mock client config
        client_config = AsyncMock()
        client_config.client_id = "test-client"
        client_config.routing_json = {"current": "config"}
        client_config.version = 3
        
        # Mock repositories
        client_repo = AsyncMock()
        client_repo.get_by_client_id.return_value = client_config
        
        snapshot_repo = AsyncMock()
        snapshot_repo.get_snapshot_by_version.return_value = snapshot
        snapshot_repo.get_max_version.return_value = 3
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Rollback configuration
        result = await rollback_config(
            client_id="test-client",
            version=2,
            request=mock_request,
            session=AsyncMock(),
            api_key="valid-key"
        )
        
        # Verify rollback result
        assert result["client_id"] == "test-client"
        assert result["rollback_to_version"] == 2
        assert result["current_version"] == 4  # New version after rollback
        assert result["routing_json"] == {"old": "config", "version": 2}
        
        # Verify client config was updated
        assert client_config.routing_json == {"old": "config", "version": 2}
        assert client_config.version == 4
    
    @pytest.mark.asyncio
    async def test_rollback_creates_snapshot_of_current_config(self):
        """Test that rollback creates snapshot of current configuration."""
        # Mock snapshot
        snapshot = AsyncMock()
        snapshot.config_data = {"old": "config"}
        
        # Mock client config
        client_config = AsyncMock()
        client_config.client_id = "test-client"
        client_config.routing_json = {"current": "config"}
        client_config.version = 3
        
        # Mock repositories
        client_repo = AsyncMock()
        client_repo.get_by_client_id.return_value = client_config
        
        snapshot_repo = AsyncMock()
        snapshot_repo.get_snapshot_by_version.return_value = snapshot
        snapshot_repo.get_max_version.return_value = 3
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Rollback configuration
        await rollback_config(
            client_id="test-client",
            version=2,
            request=mock_request,
            session=AsyncMock(),
            api_key="valid-key"
        )
        
        # Verify snapshot of current config was created
        assert snapshot_repo.create_snapshot.call_count == 1
        snapshot_call = snapshot_repo.create_snapshot.call_args[1]
        assert snapshot_call["client_id"] == "test-client"
        assert snapshot_call["version"] == 4
        assert snapshot_call["config_type"] == "routing_config"
        assert snapshot_call["config_data"] == {"current": "config"}
        assert snapshot_call["created_by"] == "admin"
        assert snapshot_call["change_reason"] == "Rollback to version 2"
    
    @pytest.mark.asyncio
    async def test_rollback_version_not_found(self):
        """Test rollback when specified version doesn't exist."""
        # Mock client config
        client_config = AsyncMock()
        client_config.client_id = "test-client"
        
        # Mock repositories
        client_repo = AsyncMock()
        client_repo.get_by_client_id.return_value = client_config
        
        snapshot_repo = AsyncMock()
        snapshot_repo.get_snapshot_by_version.return_value = None
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Rollback should raise 404
        with pytest.raises(Exception) as exc_info:
            await rollback_config(
                client_id="test-client",
                version=999,
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
        
        assert "404" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_config_history(self):
        """Test retrieving configuration history."""
        # Mock snapshots
        snapshots = [
            AsyncMock(
                id="snapshot-1",
                version=1,
                config_type="routing_config",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                created_by="admin",
                change_reason="Initial configuration"
            ),
            AsyncMock(
                id="snapshot-2",
                version=2,
                config_type="routing_config",
                created_at=datetime(2024, 1, 15, 11, 0, 0),
                created_by="admin",
                change_reason="Updated windows"
            ),
        ]
        
        # Mock snapshot repository
        snapshot_repo = AsyncMock()
        snapshot_repo.get_all_snapshots.return_value = snapshots
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Get config history
        result = await get_config_history(
            client_id="test-client",
            request=mock_request,
            session=AsyncMock(),
            api_key="valid-key"
        )
        
        # Verify result
        assert result["client_id"] == "test-client"
        assert result["count"] == 2
        assert len(result["snapshots"]) == 2
        
        # Verify snapshot data
        snapshot1 = result["snapshots"][0]
        assert snapshot1["id"] == "snapshot-1"
        assert snapshot1["version"] == 1
        assert snapshot1["config_type"] == "routing_config"
        assert snapshot1["created_by"] == "admin"
        assert snapshot1["change_reason"] == "Initial configuration"
        
        # Verify repository was called correctly
        snapshot_repo.get_all_snapshots.assert_called_once_with(
            client_id="test-client",
            config_type=None,
            limit=50,
            offset=0
        )
    
    @pytest.mark.asyncio
    async def test_get_config_history_filtered_by_type(self):
        """Test retrieving configuration history filtered by type."""
        # Mock snapshots
        snapshots = [
            AsyncMock(
                id="snapshot-1",
                version=1,
                config_type="delivery_config",
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                created_by="admin",
                change_reason="Initial delivery config"
            )
        ]
        
        # Mock snapshot repository
        snapshot_repo = AsyncMock()
        snapshot_repo.get_all_snapshots.return_value = snapshots
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Get config history filtered by type
        result = await get_config_history(
            client_id="test-client",
            request=mock_request,
            session=AsyncMock(),
            api_key="valid-key",
            config_type="delivery_config"
        )
        
        # Verify result
        assert result["count"] == 1
        assert result["snapshots"][0]["config_type"] == "delivery_config"
        
        # Verify repository was called with filter
        snapshot_repo.get_all_snapshots.assert_called_once_with(
            client_id="test-client",
            config_type="delivery_config",
            limit=50,
            offset=0
        )
    
    @pytest.mark.asyncio
    async def test_config_update_without_existing_routing(self):
        """Test configuration update when no existing routing config."""
        # Mock client config with no routing
        client_config = AsyncMock()
        client_config.client_id = "test-client"
        client_config.routing_json = None
        client_config.version = 1
        
        # Mock repositories
        client_repo = AsyncMock()
        client_repo.get_by_client_id.return_value = client_config
        
        snapshot_repo = AsyncMock()
        snapshot_repo.get_max_version.return_value = 0
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Mock routing service
        with patch('app.api.routers.admin.RoutingService') as mock_routing_service:
            mock_routing_service.return_value.validate_routing_config.return_value = (True, [])
            
            # Update configuration
            result = await update_routing_config(
                client_id="test-client",
                config={"new": "config"},
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            
            # Verify no snapshot was created (no existing config)
            snapshot_repo.create_snapshot.assert_not_called()
            
            # Verify version was still incremented
            assert result["version"] == 2
    
    @pytest.mark.asyncio
    async def test_multiple_config_updates_version_sequence(self):
        """Test version sequence across multiple configuration updates."""
        # Mock client config
        client_config = AsyncMock()
        client_config.client_id = "test-client"
        client_config.routing_json = {"initial": "config"}
        client_config.version = 1
        
        # Mock repositories
        client_repo = AsyncMock()
        client_repo.get_by_client_id.return_value = client_config
        
        snapshot_repo = AsyncMock()
        snapshot_repo.get_max_version.return_value = 1
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Mock routing service
        with patch('app.api.routers.admin.RoutingService') as mock_routing_service:
            mock_routing_service.return_value.validate_routing_config.return_value = (True, [])
            
            # First update
            result1 = await update_routing_config(
                client_id="test-client",
                config={"config": "v2"},
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            assert result1["version"] == 2
            
            # Update mock for second update
            snapshot_repo.get_max_version.return_value = 2
            client_config.routing_json = {"config": "v2"}
            client_config.version = 2
            
            # Second update
            result2 = await update_routing_config(
                client_id="test-client",
                config={"config": "v3"},
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            assert result2["version"] == 3
            
            # Verify snapshots were created for both updates
            assert snapshot_repo.create_snapshot.call_count == 2
            
            # Verify first snapshot
            first_call = snapshot_repo.create_snapshot.call_args_list[0][1]
            assert first_call["version"] == 2
            assert first_call["config_data"] == {"initial": "config"}
            
            # Verify second snapshot
            second_call = snapshot_repo.create_snapshot.call_args_list[1][1]
            assert second_call["version"] == 3
            assert second_call["config_data"] == {"config": "v2"}
