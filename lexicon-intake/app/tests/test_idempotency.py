"""Tests for idempotency functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.idempotency import IdempotencyManager


class TestIdempotencyManager:
    """Test cases for IdempotencyManager."""
    
    @patch('app.core.idempotency.CallRepository')
    @patch('app.core.idempotency.get_async_session')
    async def test_check_and_record_new_call_id(self, mock_session, mock_call_repo) -> None:
        """Test idempotency check with new call_id."""
        # Setup mocks
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_call_id.return_value = None  # No existing call
        mock_call_repo.return_value = mock_repo_instance
        
        # Test new call_id
        result = await IdempotencyManager.check_and_record_call_id("new-call-123")
        
        assert result is True
        mock_repo_instance.get_by_call_id.assert_called_once_with("new-call-123")
        mock_repo_instance.create_call_record.assert_called_once_with(call_id="new-call-123")
    
    @patch('app.core.idempotency.CallRepository')
    @patch('app.core.idempotency.get_async_session')
    async def test_check_and_record_duplicate_call_id(self, mock_session, mock_call_repo) -> None:
        """Test idempotency check with duplicate call_id."""
        # Setup mocks
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        mock_repo_instance = AsyncMock()
        mock_existing_call = AsyncMock()
        mock_repo_instance.get_by_call_id.return_value = mock_existing_call  # Existing call found
        mock_call_repo.return_value = mock_repo_instance
        
        # Test duplicate call_id
        result = await IdempotencyManager.check_and_record_call_id("existing-call-123")
        
        assert result is False
        mock_repo_instance.get_by_call_id.assert_called_once_with("existing-call-123")
        mock_repo_instance.create_call_record.assert_not_called()
    
    def test_generate_call_id(self) -> None:
        """Test call ID generation."""
        call_id1 = IdempotencyManager.generate_call_id()
        call_id2 = IdempotencyManager.generate_call_id()
        
        assert call_id1 != call_id2
        assert isinstance(call_id1, str)
        assert isinstance(call_id2, str)
        assert len(call_id1) > 0
        assert len(call_id2) > 0
