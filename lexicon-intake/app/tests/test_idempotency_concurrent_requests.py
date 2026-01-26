"""Test idempotency with concurrent requests."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.core.idempotency import IdempotencyManager
from app.db.repos.call_repo import CallRepository


class TestIdempotencyConcurrentRequests:
    """Test idempotency under concurrent conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_duplicate_call_ids(self):
        """Test that concurrent requests with same call_id produce only one lead."""
        call_id = "test-call-123"
        
        # Mock database session
        mock_session = AsyncMock()
        
        with patch('app.core.idempotency.get_async_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock call repository with atomic insert
            call_repo = CallRepository(mock_session)
            
            # Simulate atomic insert returning True for first call, False for others
            insert_results = [True, False, False]  # First succeeds, others fail
            
            async def mock_atomic_insert(*args, **kwargs):
                return insert_results.pop(0) if insert_results else False
            
            call_repo.create_call_record_atomic = mock_atomic_insert
            
            # Create concurrent tasks
            async def process_call():
                return await IdempotencyManager.check_and_record_call_id(call_id)
            
            # Run multiple concurrent requests
            tasks = [process_call() for _ in range(3)]
            results = await asyncio.gather(*tasks)
            
            # Verify only one succeeded
            assert sum(results) == 1
            assert results.count(True) == 1
            assert results.count(False) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_unique_call_ids(self):
        """Test that concurrent requests with different call_ids all succeed."""
        mock_session = AsyncMock()
        
        with patch('app.core.idempotency.get_async_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            call_repo = CallRepository(mock_session)
            
            # Mock atomic insert always succeeding
            call_repo.create_call_record_atomic = AsyncMock(return_value=True)
            
            # Create concurrent tasks with different call_ids
            async def process_call(call_id):
                return await IdempotencyManager.check_and_record_call_id(call_id)
            
            call_ids = ["test-call-1", "test-call-2", "test-call-3"]
            tasks = [process_call(call_id) for call_id in call_ids]
            results = await asyncio.gather(*tasks)
            
            # Verify all succeeded
            assert all(results)
            assert sum(results) == 3
    
    @pytest.mark.asyncio
    async def test_no_database_errors_on_duplicate(self):
        """Test that no 500 errors occur on unique constraint violations."""
        call_id = "test-call-456"
        
        mock_session = AsyncMock()
        
        with patch('app.core.idempotency.get_async_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            call_repo = CallRepository(mock_session)
            
            # Mock atomic insert returning False (duplicate)
            call_repo.create_call_record_atomic = AsyncMock(return_value=False)
            
            # Multiple concurrent requests with same call_id
            async def process_call():
                try:
                    return await IdempotencyManager.check_and_record_call_id(call_id)
                except Exception as e:
                    return f"error: {e}"
            
            tasks = [process_call() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Verify no errors occurred, all returned False
            assert all(result == False for result in results)
            assert "error:" not in str(results)
