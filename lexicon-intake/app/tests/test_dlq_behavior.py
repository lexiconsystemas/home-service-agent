"""Tests for dead letter queue behavior."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.core.enums import DeliveryStatus
from app.db.repos.delivery_repo import DeliveryRepository
from app.workers.tasks import _execute_delivery


class TestDLQBehavior:
    """Test cases for dead letter queue behavior."""
    
    @pytest.mark.asyncio
    async def test_delivery_retries_exhausted_marked_failed_final(self):
        """Test that deliveries are marked as FAILED_FINAL after max retries."""
        # Create mock delivery record
        delivery = AsyncMock()
        delivery.id = "test-delivery-id"
        delivery.attempt_count = 4
        delivery.max_attempts = 5
        delivery.failed_final = False
        delivery.failure_reason = None
        delivery.last_attempt_at = None
        
        # Mock delivery repository
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        delivery_repo.update_delivery_status.return_value = delivery
        
        # Mock external service that always fails
        with patch('app.workers.tasks.httpx.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Server Error"
            
            # Execute delivery (should fail and increment attempt count)
            await _execute_delivery(str(delivery.id))
            
            # Verify attempt count was incremented
            assert delivery.attempt_count == 5
            
            # Verify delivery was marked as FAILED_FINAL
            delivery_repo.update_delivery_status.assert_called_with(
                delivery_id=str(delivery.id),
                status=DeliveryStatus.FAILED_FINAL,
                attempt_count=5,
                failed_final=True,
                failure_reason="Max retries (5) exceeded",
                last_attempt_at=pytest.approx(datetime.utcnow(), rel_seconds=60),
                error_message="HTTP 500: Server Error"
            )
    
    @pytest.mark.asyncio
    async def test_failed_final_delivery_not_retried(self):
        """Test that FAILED_FINAL deliveries are not retried."""
        # Create delivery already marked as FAILED_FINAL
        delivery = AsyncMock()
        delivery.id = "test-delivery-id"
        delivery.failed_final = True
        delivery.status = DeliveryStatus.FAILED_FINAL
        
        # Mock delivery repository
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        
        # Mock external service
        with patch('app.workers.tasks.httpx.post') as mock_post:
            # Execute delivery
            await _execute_delivery(str(delivery.id))
            
            # Verify external service was NOT called
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delivery_success_before_max_retries(self):
        """Test that successful deliveries before max retries are not marked as FAILED_FINAL."""
        # Create mock delivery record
        delivery = AsyncMock()
        delivery.id = "test-delivery-id"
        delivery.attempt_count = 2
        delivery.max_attempts = 5
        delivery.failed_final = False
        
        # Mock delivery repository
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        delivery_repo.update_delivery_status.return_value = delivery
        
        # Mock external service that succeeds
        with patch('app.workers.tasks.httpx.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = "Success"
            
            # Execute delivery
            await _execute_delivery(str(delivery.id))
            
            # Verify delivery was marked as success, not FAILED_FINAL
            delivery_repo.update_delivery_status.assert_called_with(
                delivery_id=str(delivery.id),
                status=DeliveryStatus.SENT,
                attempt_count=3,
                response_data={"status_code": 200, "text": "Success"},
                last_attempt_at=pytest.approx(datetime.utcnow(), rel_seconds=60)
            )
            
            # Verify failed_final was NOT set
            assert delivery.failed_final == False
    
    @pytest.mark.asyncio
    async def test_get_failed_final_deliveries(self):
        """Test retrieving FAILED_FINAL deliveries."""
        # Mock delivery records
        delivery1 = AsyncMock()
        delivery1.id = "delivery-1"
        delivery1.lead_id = "lead-1"
        delivery1.channel.value = "WEBHOOK"
        delivery1.purpose.value = "LEAD_DELIVERY"
        delivery1.status.value = "FAILED_FINAL"
        delivery1.attempt_count = 5
        delivery1.max_attempts = 5
        delivery1.failure_reason = "Max retries exceeded"
        delivery1.last_attempt_at = datetime.utcnow()
        delivery1.created_at = datetime.utcnow()
        
        delivery2 = AsyncMock()
        delivery2.id = "delivery-2"
        delivery2.lead_id = "lead-2"
        delivery2.channel.value = "SMS"
        delivery2.purpose.value = "LEAD_DELIVERY"
        delivery2.status.value = "FAILED_FINAL"
        delivery2.attempt_count = 5
        delivery2.max_attempts = 5
        delivery2.failure_reason = "Phone number invalid"
        delivery2.last_attempt_at = datetime.utcnow()
        delivery2.created_at = datetime.utcnow()
        
        # Mock delivery repository
        delivery_repo = DeliveryRepository(AsyncMock())
        delivery_repo.get_failed_final_deliveries = AsyncMock(return_value=[delivery1, delivery2])
        
        # Get failed final deliveries
        failed_deliveries = await delivery_repo.get_failed_final_deliveries(limit=10, offset=0)
        
        # Verify results
        assert len(failed_deliveries) == 2
        assert failed_deliveries[0].id == "delivery-1"
        assert failed_deliveries[1].id == "delivery-2"
        assert failed_deliveries[0].status.value == "FAILED_FINAL"
        assert failed_deliveries[1].status.value == "FAILED_FINAL"
    
    @pytest.mark.asyncio
    async def test_failure_reason_persistence(self):
        """Test that failure reasons are properly persisted."""
        # Create mock delivery record
        delivery = AsyncMock()
        delivery.id = "test-delivery-id"
        delivery.attempt_count = 4
        delivery.max_attempts = 5
        delivery.failed_final = False
        delivery.failure_reason = None
        
        # Mock delivery repository
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        delivery_repo.update_delivery_status.return_value = delivery
        
        # Test different failure scenarios
        failure_scenarios = [
            ("HTTP 500: Server Error", "HTTP 500: Server Error"),
            ("Connection timeout", "Connection timeout"),
            ("DNS resolution failed", "DNS resolution failed"),
        ]
        
        for error_message, expected_reason in failure_scenarios:
            # Reset delivery state
            delivery.failed_final = False
            delivery.failure_reason = None
            delivery.attempt_count = 4
            
            # Mock external service failure
            with patch('app.workers.tasks.httpx.post') as mock_post:
                mock_post.side_effect = Exception(error_message)
                
                # Execute delivery
                await _execute_delivery(str(delivery.id))
                
                # Verify failure reason was set correctly
                delivery_repo.update_delivery_status.assert_called_with(
                    delivery_id=str(delivery.id),
                    status=DeliveryStatus.FAILED_FINAL,
                    attempt_count=5,
                    failed_final=True,
                    failure_reason="Max retries (5) exceeded",
                    last_attempt_at=pytest.approx(datetime.utcnow(), rel_seconds=60),
                    error_message=error_message
                )
    
    @pytest.mark.asyncio
    async def test_partial_failure_before_final_failure(self):
        """Test that partial failures are tracked before final failure."""
        # Create mock delivery record
        delivery = AsyncMock()
        delivery.id = "test-delivery-id"
        delivery.attempt_count = 1
        delivery.max_attempts = 3
        delivery.failed_final = False
        delivery.failure_reason = None
        
        # Mock delivery repository
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        delivery_repo.update_delivery_status.return_value = delivery
        
        # Mock external service that fails twice then succeeds
        with patch('app.workers.tasks.httpx.post') as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.text = "Server Error"
            
            # First attempt - should fail but not be final
            await _execute_delivery(str(delivery.id))
            assert delivery.attempt_count == 2
            assert delivery.failed_final == False
            
            # Second attempt - should fail but not be final
            await _execute_delivery(str(delivery.id))
            assert delivery.attempt_count == 3
            assert delivery.failed_final == False
            
            # Third attempt - should fail and be final
            await _execute_delivery(str(delivery.id))
            assert delivery.attempt_count == 3  # Max reached
            assert delivery.failed_final == True
