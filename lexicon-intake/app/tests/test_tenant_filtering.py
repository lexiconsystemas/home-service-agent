"""Tests for tenant filtering in DLQ and audit endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.ops import verify_api_key, get_dlq_deliveries, get_audit_logs
from app.services.auth_service import AuthService


class TestTenantFiltering:
    """Test tenant filtering functionality."""
    
    @pytest.mark.asyncio
    async def test_verify_api_key_admin(self):
        """Test admin API key verification."""
        with patch('app.api.routers.ops.settings.admin_api_key', 'admin-key-123'):
            request = MagicMock()
            request.headers = {"X-Admin-API-Key": "admin-key-123"}
            
            result = await verify_api_key(request)
            
            assert result == ("admin-key-123", True, None)
    
    @pytest.mark.asyncio
    async def test_verify_api_key_client(self):
        """Test client API key verification."""
        client_id = "test-client-123"
        client_api_key = AuthService.generate_client_api_key(client_id)
        
        request = MagicMock()
        request.headers = {"X-Admin-API-Key": client_api_key}
        
        result = await verify_api_key(request)
        
        assert result == (client_api_key, False, client_id)
    
    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self):
        """Test invalid API key verification."""
        request = MagicMock()
        request.headers = {"X-Admin-API-Key": "invalid-key"}
        
        with patch('app.api.routers.ops.settings.admin_api_key', 'admin-key-123'):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(request)
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_api_key_missing(self):
        """Test missing API key verification."""
        request = MagicMock()
        request.headers = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(request)
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_dlq_admin_access(self):
        """Test admin can access all DLQ items."""
        # Setup mocks
        mock_session = AsyncMock(spec=AsyncSession)
        mock_delivery_repo = AsyncMock()
        mock_deliveries = [MagicMock(id="delivery-1", lead_id="lead-1")]
        mock_delivery_repo.get_failed_final_deliveries.return_value = mock_deliveries
        
        request = MagicMock()
        auth_info = ("admin-key", True, None)
        
        with patch('app.api.routers.ops.DeliveryRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_delivery_repo
            
            # Execute
            result = await get_dlq_deliveries(
                request=request,
                session=mock_session,
                auth_info=auth_info,
                client_id=None,
                limit=50,
                offset=0,
            )
            
            # Verify admin can access all (no client_id filter)
            mock_delivery_repo.get_failed_final_deliveries.assert_called_once_with(
                client_id=None,
                limit=50,
                offset=0,
            )
            
            assert result["count"] == 1
            assert result["deliveries"][0]["id"] == "delivery-1"
    
    @pytest.mark.asyncio
    async def test_dlq_admin_filter_by_client(self):
        """Test admin can filter DLQ items by client_id."""
        # Setup mocks
        mock_session = AsyncMock(spec=AsyncSession)
        mock_delivery_repo = AsyncMock()
        mock_deliveries = [MagicMock(id="delivery-1", lead_id="lead-1")]
        mock_delivery_repo.get_failed_final_deliveries.return_value = mock_deliveries
        
        request = MagicMock()
        auth_info = ("admin-key", True, None)
        
        with patch('app.api.routers.ops.DeliveryRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_delivery_repo
            
            # Execute
            result = await get_dlq_deliveries(
                request=request,
                session=mock_session,
                auth_info=auth_info,
                client_id="specific-client",
                limit=50,
                offset=0,
            )
            
            # Verify admin can filter by client_id
            mock_delivery_repo.get_failed_final_deliveries.assert_called_once_with(
                client_id="specific-client",
                limit=50,
                offset=0,
            )
            
            assert result["count"] == 1
    
    @pytest.mark.asyncio
    async def test_dlq_client_own_access(self):
        """Test client can access their own DLQ items."""
        # Setup mocks
        mock_session = AsyncMock(spec=AsyncSession)
        mock_delivery_repo = AsyncMock()
        mock_deliveries = [MagicMock(id="delivery-1", lead_id="lead-1")]
        mock_delivery_repo.get_failed_final_deliveries.return_value = mock_deliveries
        
        request = MagicMock()
        auth_info = ("client-key", False, "client-123")
        
        with patch('app.api.routers.ops.DeliveryRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_delivery_repo
            
            # Execute
            result = await get_dlq_deliveries(
                request=request,
                session=mock_session,
                auth_info=auth_info,
                client_id=None,
                limit=50,
                offset=0,
            )
            
            # Verify client can only access their own data
            mock_delivery_repo.get_failed_final_deliveries.assert_called_once_with(
                client_id="client-123",
                limit=50,
                offset=0,
            )
            
            assert result["count"] == 1
    
    @pytest.mark.asyncio
    async def test_dlq_client_cross_access_denied(self):
        """Test client cannot access other client's DLQ items."""
        # Setup mocks
        mock_session = AsyncMock(spec=AsyncSession)
        request = MagicMock()
        auth_info = ("client-key", False, "client-123")
        
        # Execute and expect access denied
        with pytest.raises(HTTPException) as exc_info:
            await get_dlq_deliveries(
                request=request,
                session=mock_session,
                auth_info=auth_info,
                client_id="other-client",  # Trying to access other client's data
                limit=50,
                offset=0,
            )
        
        assert exc_info.value.status_code == 403
        assert "cannot access other client's data" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_audit_logs_admin_access(self):
        """Test admin can access all audit logs."""
        # Setup mocks
        mock_session = AsyncMock(spec=AsyncSession)
        mock_audit_repo = AsyncMock()
        mock_logs = [MagicMock(id="log-1", actor_type="ADMIN")]
        mock_audit_repo.get_audit_logs.return_value = mock_logs
        
        request = MagicMock()
        auth_info = ("admin-key", True, None)
        
        with patch('app.api.routers.ops.AuditRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_audit_repo
            
            # Execute
            result = await get_audit_logs(
                request=request,
                session=mock_session,
                auth_info=auth_info,
                client_id=None,
                limit=100,
                offset=0,
            )
            
            # Verify admin can access all (no client_id filter)
            mock_audit_repo.get_audit_logs.assert_called_once_with(
                target_type=None,
                target_id=None,
                actor_type=None,
                actor_id=None,
                action=None,
                client_id=None,
                limit=100,
                offset=0,
            )
            
            assert result["count"] == 1
            assert result["logs"][0]["id"] == "log-1"
    
    @pytest.mark.asyncio
    async def test_audit_logs_client_own_access(self):
        """Test client can access their own audit logs."""
        # Setup mocks
        mock_session = AsyncMock(spec=AsyncSession)
        mock_audit_repo = AsyncMock()
        mock_logs = [MagicMock(id="log-1", actor_type="CLIENT")]
        mock_audit_repo.get_audit_logs.return_value = mock_logs
        
        request = MagicMock()
        auth_info = ("client-key", False, "client-123")
        
        with patch('app.api.routers.ops.AuditRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_audit_repo
            
            # Execute
            result = await get_audit_logs(
                request=request,
                session=mock_session,
                auth_info=auth_info,
                client_id=None,
                limit=100,
                offset=0,
            )
            
            # Verify client can only access their own data
            mock_audit_repo.get_audit_logs.assert_called_once_with(
                target_type=None,
                target_id=None,
                actor_type=None,
                actor_id=None,
                action=None,
                client_id="client-123",
                limit=100,
                offset=0,
            )
            
            assert result["count"] == 1
    
    @pytest.mark.asyncio
    async def test_audit_logs_client_cross_access_denied(self):
        """Test client cannot access other client's audit logs."""
        # Setup mocks
        mock_session = AsyncMock(spec=AsyncSession)
        request = MagicMock()
        auth_info = ("client-key", False, "client-123")
        
        # Execute and expect access denied
        with pytest.raises(HTTPException) as exc_info:
            await get_audit_logs(
                request=request,
                session=mock_session,
                auth_info=auth_info,
                client_id="other-client",  # Trying to access other client's data
                limit=100,
                offset=0,
            )
        
        assert exc_info.value.status_code == 403
        assert "cannot access other client's data" in str(exc_info.value.detail)
