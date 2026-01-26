"""Test webhook sender does not retry on 4xx errors."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.enums import DeliveryStatus
from app.adapters.webhooks.webhook_sender import WebhookSender


class TestWebhookSender4xxNoRetry:
    """Test that webhook sender does not retry on 4xx errors."""
    
    @pytest.mark.asyncio
    async def test_400_no_retry(self):
        """Test that 400 Bad Request does not trigger retry."""
        delivery_id = "test-delivery-id"
        webhook_url = "https://example.com/webhook"
        
        # Mock database session and repositories
        mock_session = AsyncMock()
        delivery_repo = AsyncMock()
        lead_repo = AsyncMock()
        
        # Mock delivery and lead records
        delivery_record = AsyncMock()
        delivery_record.id = "test-delivery-id"
        delivery_record.lead_id = "test-lead-id"
        
        lead_record = AsyncMock()
        
        delivery_repo.get_by_lead_id.return_value = [delivery_record]
        lead_repo.get_by_lead_id.return_value = lead_record
        
        with patch('app.adapters.webhooks.webhook_sender.get_async_session_context') as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # Mock HTTP client to return 400
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_client.post.return_value = mock_response
            
            webhook_sender = WebhookSender()
            webhook_sender.client = mock_client
            
            try:
                # Send webhook
                result = await webhook_sender.send_webhook(delivery_id, webhook_url)
                
                # Should return False for 4xx error
                assert result is False
                
                # Verify only one attempt was made (no retry)
                assert mock_client.post.call_count == 1
                
                # Verify delivery was marked as FAILED (not RETRYING)
                delivery_repo.update_delivery_attempt.assert_called_once()
                call_args = delivery_repo.update_delivery_attempt.call_args[1]
                assert call_args["status"] == DeliveryStatus.FAILED
                assert "HTTP 400" in call_args["error_message"]
                
            finally:
                await webhook_sender.close()
    
    @pytest.mark.asyncio
    async def test_401_no_retry(self):
        """Test that 401 Unauthorized does not trigger retry."""
        delivery_id = "test-delivery-id"
        webhook_url = "https://example.com/webhook"
        
        # Mock database session and repositories
        mock_session = AsyncMock()
        delivery_repo = AsyncMock()
        lead_repo = AsyncMock()
        
        delivery_record = AsyncMock()
        delivery_record.id = "test-delivery-id"
        delivery_record.lead_id = "test-lead-id"
        lead_record = AsyncMock()
        
        delivery_repo.get_by_lead_id.return_value = [delivery_record]
        lead_repo.get_by_lead_id.return_value = lead_record
        
        with patch('app.adapters.webhooks.webhook_sender.get_async_session_context') as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # Mock HTTP client to return 401
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_client.post.return_value = mock_response
            
            webhook_sender = WebhookSender()
            webhook_sender.client = mock_client
            
            try:
                # Send webhook
                result = await webhook_sender.send_webhook(delivery_id, webhook_url)
                
                # Should return False for 4xx error
                assert result is False
                
                # Verify only one attempt was made (no retry)
                assert mock_client.post.call_count == 1
                
                # Verify delivery was marked as FAILED
                delivery_repo.update_delivery_attempt.assert_called_once()
                call_args = delivery_repo.update_delivery_attempt.call_args[1]
                assert call_args["status"] == DeliveryStatus.FAILED
                assert "HTTP 401" in call_args["error_message"]
                
            finally:
                await webhook_sender.close()
    
    @pytest.mark.asyncio
    async def test_404_no_retry(self):
        """Test that 404 Not Found does not trigger retry."""
        delivery_id = "test-delivery-id"
        webhook_url = "https://example.com/webhook"
        
        # Mock database session and repositories
        mock_session = AsyncMock()
        delivery_repo = AsyncMock()
        lead_repo = AsyncMock()
        
        delivery_record = AsyncMock()
        delivery_record.id = "test-delivery-id"
        delivery_record.lead_id = "test-lead-id"
        lead_record = AsyncMock()
        
        delivery_repo.get_by_lead_id.return_value = [delivery_record]
        lead_repo.get_by_lead_id.return_value = lead_record
        
        with patch('app.adapters.webhooks.webhook_sender.get_async_session_context') as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # Mock HTTP client to return 404
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_client.post.return_value = mock_response
            
            webhook_sender = WebhookSender()
            webhook_sender.client = mock_client
            
            try:
                # Send webhook
                result = await webhook_sender.send_webhook(delivery_id, webhook_url)
                
                # Should return False for 4xx error
                assert result is False
                
                # Verify only one attempt was made (no retry)
                assert mock_client.post.call_count == 1
                
                # Verify delivery was marked as FAILED
                delivery_repo.update_delivery_attempt.assert_called_once()
                call_args = delivery_repo.update_delivery_attempt.call_args[1]
                assert call_args["status"] == DeliveryStatus.FAILED
                assert "HTTP 404" in call_args["error_message"]
                
            finally:
                await webhook_sender.close()
    
    @pytest.mark.asyncio
    async def test_5xx_retry_behavior(self):
        """Test that 5xx errors do trigger retry (RQ handles it)."""
        delivery_id = "test-delivery-id"
        webhook_url = "https://example.com/webhook"
        
        # Mock database session and repositories
        mock_session = AsyncMock()
        delivery_repo = AsyncMock()
        lead_repo = AsyncMock()
        
        delivery_record = AsyncMock()
        delivery_record.id = "test-delivery-id"
        delivery_record.lead_id = "test-lead-id"
        lead_record = AsyncMock()
        
        delivery_repo.get_by_lead_id.return_value = [delivery_record]
        lead_repo.get_by_lead_id.return_value = lead_record
        
        with patch('app.adapters.webhooks.webhook_sender.get_async_session_context') as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            
            # Mock HTTP client to return 500
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.post.return_value = mock_response
            
            webhook_sender = WebhookSender()
            webhook_sender.client = mock_client
            
            try:
                # Send webhook
                result = await webhook_sender.send_webhook(delivery_id, webhook_url)
                
                # Should return False for 5xx error
                assert result is False
                
                # Verify only one attempt was made (RQ handles retries)
                assert mock_client.post.call_count == 1
                
                # Verify delivery was marked as FAILED (RQ will retry)
                delivery_repo.update_delivery_attempt.assert_called_once()
                call_args = delivery_repo.update_delivery_attempt.call_args[1]
                assert call_args["status"] == DeliveryStatus.FAILED
                assert "HTTP 500" in call_args["error_message"]
                
            finally:
                await webhook_sender.close()
    
    @pytest.mark.asyncio
    async def test_4xx_range_no_retry(self):
        """Test that all 4xx status codes do not trigger retry."""
        # Test various 4xx status codes
        status_codes = [400, 401, 403, 404, 409, 422, 429]
        
        for status_code in status_codes:
            delivery_id = f"test-delivery-{status_code}"
            webhook_url = "https://example.com/webhook"
            
            # Mock database session and repositories
            mock_session = AsyncMock()
            delivery_repo = AsyncMock()
            lead_repo = AsyncMock()
            
            delivery_record = AsyncMock()
            delivery_record.id = delivery_id
            delivery_record.lead_id = "test-lead-id"
            lead_record = AsyncMock()
            
            delivery_repo.get_by_lead_id.return_value = [delivery_record]
            lead_repo.get_by_lead_id.return_value = lead_record
            
            with patch('app.adapters.webhooks.webhook_sender.get_async_session_context') as mock_session_ctx:
                mock_session_ctx.return_value.__aenter__.return_value = mock_session
                
                # Mock HTTP client to return 4xx
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = status_code
                mock_response.text = f"Error {status_code}"
                mock_client.post.return_value = mock_response
                
                webhook_sender = WebhookSender()
                webhook_sender.client = mock_client
                
                try:
                    # Send webhook
                    result = await webhook_sender.send_webhook(delivery_id, webhook_url)
                    
                    # Should return False for all 4xx errors
                    assert result is False
                    
                    # Verify only one attempt was made (no retry)
                    assert mock_client.post.call_count == 1
                    
                    # Verify delivery was marked as FAILED
                    delivery_repo.update_delivery_attempt.assert_called_once()
                    call_args = delivery_repo.update_delivery_attempt.call_args[1]
                    assert call_args["status"] == DeliveryStatus.FAILED
                    
                finally:
                    await webhook_sender.close()
