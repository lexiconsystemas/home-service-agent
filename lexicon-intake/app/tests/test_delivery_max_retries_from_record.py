"""Test delivery max retries from record configuration."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.enums import DeliveryStatus
from app.workers.tasks import _execute_delivery


class TestDeliveryMaxRetriesFromRecord:
    """Test that delivery respects max_attempts from delivery record."""
    
    @pytest.mark.asyncio
    async def test_delivery_respects_record_max_attempts(self):
        """Test that delivery uses max_attempts from delivery record, not hardcoded."""
        # Create mock delivery record with custom max_attempts
        delivery_record = AsyncMock()
        delivery_record.id = "test-delivery-id"
        delivery_record.attempt_count = 2
        delivery_record.max_attempts = 7  # Custom max_attempts
        delivery_record.failed_final = False
        delivery_record.channel.value = "WEBHOOK"
        delivery_record.purpose.value = "LEAD_DELIVERY"
        
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery_record
        delivery_repo.update_delivery_attempt = AsyncMock()
        
        # Mock external service that always fails
        with patch('app.workers.tasks.httpx.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Server Error"
            
            # Execute delivery
            await _execute_delivery(str(delivery_record.id))
            
            # Verify delivery was NOT marked as final failure (2 < 7)
            delivery_repo.update_delivery_attempt.assert_called_once()
            call_args = delivery_repo.update_delivery_attempt.call_args[1]
            
            # Should be FAILED, not FAILED_FINAL since attempt_count < max_attempts
            assert call_args["status"] == DeliveryStatus.FAILED
            assert call_args["failed_final"] is None  # Not marked as final failure
    
    @pytest.mark.asyncio
    async def test_delivery_marks_final_at_max_attempts(self):
        """Test that delivery marks FAILED_FINAL when attempt_count >= max_attempts."""
        # Create mock delivery record at max attempts
        delivery_record = AsyncMock()
        delivery_record.id = "test-delivery-id"
        delivery_record.attempt_count = 5
        delivery_record.max_attempts = 5  # At max
        delivery_record.failed_final = False
        delivery_record.channel.value = "WEBHOOK"
        delivery_record.purpose.value = "LEAD_DELIVERY"
        
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery_record
        delivery_repo.update_delivery_attempt = AsyncMock()
        
        # Mock external service that fails
        with patch('app.workers.tasks.httpx.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Server Error"
            
            # Execute delivery
            await _execute_delivery(str(delivery_record.id))
            
            # Verify delivery was marked as final failure
            delivery_repo.update_delivery_attempt.assert_called_once()
            call_args = delivery_repo.update_delivery_attempt.call_args[1]
            
            # Should be FAILED_FINAL since attempt_count >= max_attempts
            assert call_args["status"] == DeliveryStatus.FAILED_FINAL
            assert call_args["failed_final"] is True
            assert "Max retries exceeded" in call_args["failure_reason"]
    
    @pytest.mark.asyncio
    async def test_delivery_different_max_attempts_values(self):
        """Test various max_attempts values work correctly."""
        test_cases = [
            {"max_attempts": 1, "attempt_count": 0, "should_be_final": False},
            {"max_attempts": 1, "attempt_count": 1, "should_be_final": True},
            {"max_attempts": 3, "attempt_count": 2, "should_be_final": False},
            {"max_attempts": 3, "attempt_count": 3, "should_be_final": True},
            {"max_attempts": 10, "attempt_count": 9, "should_be_final": False},
            {"max_attempts": 10, "attempt_count": 10, "should_be_final": True},
        ]
        
        for case in test_cases:
            # Create mock delivery record
            delivery_record = AsyncMock()
            delivery_record.id = "test-delivery-id"
            delivery_record.attempt_count = case["attempt_count"]
            delivery_record.max_attempts = case["max_attempts"]
            delivery_record.failed_final = False
            delivery_record.channel.value = "WEBHOOK"
            delivery_record.purpose.value = "LEAD_DELIVERY"
            
            # Mock repositories
            delivery_repo = AsyncMock()
            delivery_repo.get_by_id.return_value = delivery_record
            delivery_repo.update_delivery_attempt = AsyncMock()
            
            # Mock external service that fails
            with patch('app.workers.tasks.httpx.post') as mock_post:
                mock_post.return_value.status_code = 500
                mock_post.return_value.text = "Server Error"
                
                # Execute delivery
                await _execute_delivery(str(delivery_record.id))
                
                # Verify final failure status
                delivery_repo.update_delivery_attempt.assert_called_once()
                call_args = delivery_repo.update_delivery_attempt.call_args[1]
                
                if case["should_be_final"]:
                    assert call_args["status"] == DeliveryStatus.FAILED_FINAL
                    assert call_args["failed_final"] is True
                else:
                    assert call_args["status"] == DeliveryStatus.FAILED
                    assert call_args["failed_final"] is None
