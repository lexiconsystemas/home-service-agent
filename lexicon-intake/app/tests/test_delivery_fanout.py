"""Tests for multi-channel delivery fanout."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.core.enums import DeliveryChannel, DeliveryPurpose, CallClassification
from app.db.tables.client_config import ClientConfig
from app.db.tables.lead_record import LeadRecord
from app.services.delivery_service import DeliveryService


class TestDeliveryFanout:
    """Test cases for multi-channel delivery fanout."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = AsyncMock()
        self.delivery_service = DeliveryService(self.mock_db)
        
        # Mock repositories
        self.delivery_service.delivery_repo = AsyncMock()
        self.delivery_service.lead_repo = AsyncMock()
        self.delivery_service.client_repo = AsyncMock()
    
    async def test_multi_channel_delivery_fanout(self) -> None:
        """Test delivery fanout to multiple channels."""
        # Setup client config with multiple channels
        client_config = ClientConfig(
            client_id="demo",
            delivery_channels=["WEBHOOK", "SMS", "EMAIL"],
            webhook_url="https://example.com/webhook",
            sms_to_numbers=["+15550000001"],
            email_to_addresses=["leads@example.com"],
        )
        
        # Mock delivery record creation
        mock_delivery_record = AsyncMock()
        mock_delivery_record.id = "delivery-123"
        self.delivery_service.delivery_repo.create_delivery_record.return_value = mock_delivery_record
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_lead_delivery("lead-123", client_config)
        
        # Verify delivery records created for each channel
        assert self.delivery_service.delivery_repo.create_delivery_record.call_count == 3
        
        # Verify correct channels and purposes
        calls = self.delivery_service.delivery_repo.create_delivery_record.call_args_list
        channels = [call[1]['channel'] for call in calls]
        purposes = [call[1]['purpose'] for call in calls]
        
        assert DeliveryChannel.WEBHOOK in channels
        assert DeliveryChannel.SMS in channels
        assert DeliveryChannel.EMAIL in channels
        assert all(purpose == DeliveryPurpose.LEAD_DELIVERY for purpose in purposes)
        
        # Verify tasks enqueued
        assert mock_enqueue.call_count == 3
    
    async def test_followup_confirmation_enabled(self) -> None:
        """Test follow-up confirmation when enabled."""
        # Setup client config with follow-up enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": True,
            },
        )
        
        # Setup lead record
        lead_record = LeadRecord(
            lead_id="lead-123",
            call_id="call-123",
            client_id="demo",
            caller_phone="+15551234567",
            classification=CallClassification.QUALIFIED,
        )
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        
        # Mock delivery record creation
        mock_delivery_record = AsyncMock()
        mock_delivery_record.id = "delivery-123"
        self.delivery_service.delivery_repo.create_delivery_record.return_value = mock_delivery_record
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_followup_confirmation("lead-123", client_config)
        
        # Verify SMS delivery record created
        self.delivery_service.delivery_repo.create_delivery_record.assert_called_once_with(
            lead_id="lead-123",
            channel=DeliveryChannel.SMS,
            purpose=DeliveryPurpose.FOLLOWUP_CONFIRMATION,
            destination="+15551234567",
        )
        
        # Verify task enqueued
        mock_enqueue.assert_called_once_with("delivery-123")
    
    async def test_followup_confirmation_disabled(self) -> None:
        """Test follow-up confirmation when disabled."""
        # Setup client config with follow-up disabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": False,
            },
        )
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_followup_confirmation("lead-123", client_config)
        
        # Verify no delivery record created
        self.delivery_service.delivery_repo.create_delivery_record.assert_not_called()
        mock_enqueue.assert_not_called()
    
    async def test_followup_reminder_qualified_only(self) -> None:
        """Test follow-up reminder only for qualified leads."""
        # Setup client config with reminder enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_reminder_to_caller": True,
                "reminder_delay_minutes": 30,
            },
        )
        
        # Setup qualified lead record
        lead_record = LeadRecord(
            lead_id="lead-123",
            call_id="call-123",
            client_id="demo",
            caller_phone="+15551234567",
            classification=CallClassification.QUALIFIED,
        )
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        
        # Mock delivery record creation
        mock_delivery_record = AsyncMock()
        mock_delivery_record.id = "delivery-123"
        self.delivery_service.delivery_repo.create_delivery_record.return_value = mock_delivery_record
        
        # Mock enqueue followup task
        with patch('app.services.delivery_service.enqueue_followup_task') as mock_enqueue:
            await self.delivery_service.enqueue_followup_reminder("lead-123", client_config)
        
        # Verify SMS delivery record created
        self.delivery_service.delivery_repo.create_delivery_record.assert_called_once_with(
            lead_id="lead-123",
            channel=DeliveryChannel.SMS,
            purpose=DeliveryPurpose.FOLLOWUP_REMINDER,
            destination="+15551234567",
        )
        
        # Verify delayed task enqueued
        mock_enqueue.assert_called_once_with("delivery-123", 30)
    
    async def test_followup_reminder_unqualified_skipped(self) -> None:
        """Test follow-up reminder skipped for unqualified leads."""
        # Setup client config with reminder enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_reminder_to_caller": True,
                "reminder_delay_minutes": 30,
            },
        )
        
        # Setup unqualified lead record
        lead_record = LeadRecord(
            lead_id="lead-123",
            call_id="call-123",
            client_id="demo",
            caller_phone="+15551234567",
            classification=CallClassification.UNQUALIFIED,
        )
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        
        # Mock enqueue followup task
        with patch('app.services.delivery_service.enqueue_followup_task') as mock_enqueue:
            await self.delivery_service.enqueue_followup_reminder("lead-123", client_config)
        
        # Verify no delivery record created
        self.delivery_service.delivery_repo.create_delivery_record.assert_not_called()
        mock_enqueue.assert_not_called()
    
    async def test_urgent_escalation_qualified_same_day(self) -> None:
        """Test urgent escalation for qualified same-day leads."""
        # Setup client config with escalation enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "urgent_escalation": True,
            },
            sms_to_numbers=["+15550000001", "+15550000002"],
        )
        
        # Setup urgent qualified lead record
        lead_record = LeadRecord(
            lead_id="lead-123",
            call_id="call-123",
            client_id="demo",
            caller_phone="+15551234567",
            classification=CallClassification.QUALIFIED,
        )
        # Set urgency to same_day by accessing the enum value
        from app.core.enums import UrgencyLevel
        lead_record.urgency = UrgencyLevel.SAME_DAY
        
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        
        # Mock delivery record creation
        mock_delivery_record = AsyncMock()
        mock_delivery_record.id = "delivery-123"
        self.delivery_service.delivery_repo.create_delivery_record.return_value = mock_delivery_record
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_urgent_escalation("lead-123", client_config)
        
        # Verify escalation SMS sent to all recipients
        assert self.delivery_service.delivery_repo.create_delivery_record.call_count == 2
        
        calls = self.delivery_service.delivery_repo.create_delivery_record.call_args_list
        destinations = [call[1]['destination_override'] for call in calls]
        
        assert "+15550000001" in destinations
        assert "+15550000002" in destinations
        
        # Verify all are SMS escalation messages
        for call in calls:
            assert call[1]['channel'] == DeliveryChannel.SMS
            assert call[1]['purpose'] == DeliveryPurpose.URGENT_ESCALATION
        
        # Verify tasks enqueued
        assert mock_enqueue.call_count == 2
    
    async def test_urgent_escalation_not_urgent_skipped(self) -> None:
        """Test urgent escalation skipped for non-urgent leads."""
        # Setup client config with escalation enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "urgent_escalation": True,
            },
        )
        
        # Setup non-urgent qualified lead record
        lead_record = LeadRecord(
            lead_id="lead-123",
            call_id="call-123",
            client_id="demo",
            caller_phone="+15551234567",
            classification=CallClassification.QUALIFIED,
        )
        # Set urgency to medium (not same_day)
        from app.core.enums import UrgencyLevel
        lead_record.urgency = UrgencyLevel.MEDIUM
        
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_urgent_escalation("lead-123", client_config)
        
        # Verify no escalation sent
        self.delivery_service.delivery_repo.create_delivery_record.assert_not_called()
        mock_enqueue.assert_not_called()
