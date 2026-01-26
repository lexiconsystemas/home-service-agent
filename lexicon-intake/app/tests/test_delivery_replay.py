"""Tests for delivery replay functionality."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.api.routers.ops import replay_delivery
from app.core.enums import DeliveryStatus, DeliveryChannel, DeliveryPurpose
from app.db.repos.audit_repo import AuditRepository
from app.db.repos.delivery_repo import DeliveryRepository
from app.db.repos.lead_repo import LeadRepository


class TestDeliveryReplay:
    """Test cases for delivery replay functionality."""
    
    @pytest.mark.asyncio
    async def test_replay_delivery_success(self):
        """Test successful delivery replay creates new delivery attempt."""
        # Mock original delivery
        original_delivery = AsyncMock()
        original_delivery.id = "original-delivery-id"
        original_delivery.lead_id = "test-lead-id"
        original_delivery.channel = DeliveryChannel.WEBHOOK
        original_delivery.purpose = DeliveryPurpose.LEAD_DELIVERY
        original_delivery.destination = "https://example.com/webhook"
        original_delivery.payload = {"test": "data"}
        original_delivery.max_attempts = 5
        original_delivery.failed_final = True
        original_delivery.status = DeliveryStatus.FAILED_FINAL
        
        # Mock lead
        lead = AsyncMock()
        lead.client_id = "test-client"
        
        # Mock new delivery
        new_delivery = AsyncMock()
        new_delivery.id = "new-delivery-id"
        new_delivery.status = DeliveryStatus.PENDING
        
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = original_delivery
        delivery_repo.create_delivery_record.return_value = new_delivery
        
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = lead
        
        audit_repo = AsyncMock()
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Mock enqueue task
        with patch('app.api.routers.ops.enqueue_delivery_task') as mock_enqueue:
            # Execute replay
            result = await replay_delivery(
                delivery_id="original-delivery-id",
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            
            # Verify new delivery was created
            delivery_repo.create_delivery_record.assert_called_once_with(
                lead_id="test-lead-id",
                channel=DeliveryChannel.WEBHOOK,
                purpose=DeliveryPurpose.LEAD_DELIVERY,
                destination="https://example.com/webhook",
                payload={"test": "data"},
                max_attempts=5,
            )
            
            # Verify task was enqueued
            mock_enqueue.assert_called_once_with("new-delivery-id")
            
            # Verify audit log was created
            audit_repo.create_audit_log.assert_called_once()
            audit_call = audit_repo.create_audit_log.call_args[1]
            assert audit_call["action"] == "REPLAY_DELIVERY"
            assert audit_call["target_type"] == "delivery"
            assert audit_call["target_id"] == "new-delivery-id"
            
            # Verify response
            assert result["original_delivery_id"] == "original-delivery-id"
            assert result["new_delivery_id"] == "new-delivery-id"
            assert result["lead_id"] == "test-lead-id"
            assert result["channel"] == "WEBHOOK"
            assert result["purpose"] == "LEAD_DELIVERY"
    
    @pytest.mark.asyncio
    async def test_replay_delivery_not_found(self):
        """Test replay of non-existent delivery returns 404."""
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = None
        
        lead_repo = AsyncMock()
        audit_repo = AsyncMock()
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Execute replay and expect 404
        with pytest.raises(Exception) as exc_info:
            await replay_delivery(
                delivery_id="non-existent-id",
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
        
        assert "404" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_replay_delivery_not_failed_final(self):
        """Test replay of non-failed-final delivery returns 400."""
        # Mock delivery that's not in final failed state
        delivery = AsyncMock()
        delivery.id = "delivery-id"
        delivery.failed_final = False
        delivery.status = DeliveryStatus.PENDING
        
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        
        lead_repo = AsyncMock()
        audit_repo = AsyncMock()
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Execute replay and expect 400
        with pytest.raises(Exception) as exc_info:
            await replay_delivery(
                delivery_id="delivery-id",
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
        
        assert "400" in str(exc_info.value)
        assert "not in final failed state" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_replay_delivery_lead_not_found(self):
        """Test replay when lead is not found returns 404."""
        # Mock delivery
        delivery = AsyncMock()
        delivery.id = "delivery-id"
        delivery.lead_id = "lead-id"
        delivery.failed_final = True
        delivery.status = DeliveryStatus.FAILED_FINAL
        
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = None
        
        audit_repo = AsyncMock()
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Execute replay and expect 404
        with pytest.raises(Exception) as exc_info:
            await replay_delivery(
                delivery_id="delivery-id",
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
        
        assert "404" in str(exc_info.value)
        assert "lead" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_replay_delivery_invalid_api_key(self):
        """Test replay with invalid API key returns 401."""
        # Mock request with invalid API key
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "invalid-key"}
        
        # Execute replay and expect 401
        with pytest.raises(Exception) as exc_info:
            await replay_delivery(
                delivery_id="delivery-id",
                request=mock_request,
                session=AsyncMock(),
                api_key="invalid-key"
            )
        
        assert "401" in str(exc_info.value)
        assert "invalid admin api key" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_replay_delivery_audit_log_content(self):
        """Test that audit log contains correct replay information."""
        # Mock original delivery
        original_delivery = AsyncMock()
        original_delivery.id = "original-delivery-id"
        original_delivery.lead_id = "test-lead-id"
        original_delivery.channel = DeliveryChannel.SMS
        original_delivery.purpose = DeliveryPurpose.LEAD_DELIVERY
        original_delivery.destination = "+15550000000"
        original_delivery.payload = {"caller": "John Doe"}
        original_delivery.max_attempts = 3
        original_delivery.failed_final = True
        original_delivery.status = DeliveryStatus.FAILED_FINAL
        original_delivery.attempt_count = 3
        
        # Mock lead
        lead = AsyncMock()
        lead.client_id = "test-client"
        
        # Mock new delivery
        new_delivery = AsyncMock()
        new_delivery.id = "new-delivery-id"
        new_delivery.status = DeliveryStatus.PENDING
        
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = original_delivery
        delivery_repo.create_delivery_record.return_value = new_delivery
        
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = lead
        
        audit_repo = AsyncMock()
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Mock enqueue task
        with patch('app.api.routers.ops.enqueue_delivery_task'):
            # Execute replay
            await replay_delivery(
                delivery_id="original-delivery-id",
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            
            # Verify audit log content
            audit_repo.create_audit_log.assert_called_once()
            audit_call = audit_repo.create_audit_log.call_args[1]
            
            # Verify before state
            before_state = audit_call["before_state"]
            assert before_state["original_delivery_id"] == "original-delivery-id"
            assert before_state["original_status"] == "FAILED_FINAL"
            assert before_state["original_attempt_count"] == 3
            
            # Verify after state
            after_state = audit_call["after_state"]
            assert after_state["new_delivery_id"] == "new-delivery-id"
            assert after_state["new_status"] == "PENDING"
            assert "replay_timestamp" in after_state
            
            # Verify details
            details = audit_call["details"]
            assert details["lead_id"] == "test-lead-id"
            assert details["client_id"] == "test-client"
            assert details["channel"] == "SMS"
            assert details["purpose"] == "LEAD_DELIVERY"
    
    @pytest.mark.asyncio
    async def test_replay_delivery_preserves_original(self):
        """Test that original delivery is not modified during replay."""
        # Mock original delivery
        original_delivery = AsyncMock()
        original_delivery.id = "original-delivery-id"
        original_delivery.lead_id = "test-lead-id"
        original_delivery.channel = DeliveryChannel.EMAIL
        original_delivery.purpose = DeliveryPurpose.LEAD_DELIVERY
        original_delivery.destination = "test@example.com"
        original_delivery.payload = {"subject": "Test"}
        original_delivery.max_attempts = 5
        original_delivery.failed_final = True
        original_delivery.status = DeliveryStatus.FAILED_FINAL
        original_delivery.attempt_count = 5
        
        # Mock lead
        lead = AsyncMock()
        lead.client_id = "test-client"
        
        # Mock new delivery
        new_delivery = AsyncMock()
        new_delivery.id = "new-delivery-id"
        new_delivery.status = DeliveryStatus.PENDING
        
        # Mock repositories
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = original_delivery
        delivery_repo.create_delivery_record.return_value = new_delivery
        
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = lead
        
        audit_repo = AsyncMock()
        
        # Mock request
        mock_request = AsyncMock()
        mock_request.headers = {"X-Admin-API-Key": "valid-key"}
        
        # Mock enqueue task
        with patch('app.api.routers.ops.enqueue_delivery_task'):
            # Execute replay
            await replay_delivery(
                delivery_id="original-delivery-id",
                request=mock_request,
                session=AsyncMock(),
                api_key="valid-key"
            )
            
            # Verify original delivery was not updated
            # (update_delivery_status should not be called on original)
            delivery_repo.update_delivery_status.assert_not_called()
            
            # Verify new delivery was created with same payload
            delivery_repo.create_delivery_record.assert_called_once_with(
                lead_id="test-lead-id",
                channel=DeliveryChannel.EMAIL,
                purpose=DeliveryPurpose.LEAD_DELIVERY,
                destination="test@example.com",
                payload={"subject": "Test"},
                max_attempts=5,
            )
