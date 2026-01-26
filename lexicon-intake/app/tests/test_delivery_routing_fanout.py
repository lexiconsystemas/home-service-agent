"""Tests for delivery routing fanout with stored routing decisions."""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.enums import ServiceType, TimeWindow, DeliveryChannel, DeliveryPurpose, CallClassification, UrgencyLevel
from app.db.tables.lead_record import LeadRecord
from app.db.tables.client_config import ClientConfig
from app.services.delivery_service import DeliveryService


class TestDeliveryRoutingFanout:
    """Test cases for delivery routing fanout using stored decisions."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = AsyncMock()
        self.delivery_service = DeliveryService(self.mock_db)
        
        # Mock repositories
        self.delivery_service.delivery_repo = AsyncMock()
        self.delivery_service.lead_repo = AsyncMock()
        self.delivery_service.client_repo = AsyncMock()
    
    async def test_routing_changes_channels_after_hours(self) -> None:
        """Test that routing changes channels from webhook-only to SMS-only after hours."""
        # Setup client config with routing
        client_config = ClientConfig(
            client_id="demo",
            delivery_channels=["WEBHOOK"],  # Base config
            webhook_url="https://base.example.com/webhook",
            sms_to_numbers=[],
            email_to_addresses=[],
            message_templates={},
            followup_flags={},
            routing_json={
                "profiles": [
                    {
                        "name": "default_in_hours",
                        "match": {"time_window": "IN_HOURS"},
                        "delivery": {
                            "channels": ["WEBHOOK"],
                            "webhook_url": "https://base.example.com/webhook"
                        }
                    },
                    {
                        "name": "default_after_hours",
                        "match": {"time_window": "AFTER_HOURS"},
                        "delivery": {
                            "channels": ["SMS"],
                            "sms_to_numbers": ["+15550000001"]
                        }
                    }
                ]
            }
        )
        
        # Setup lead record with stored routing decision
        lead_record = LeadRecord()
        lead_record.lead_id = "lead-123"
        lead_record.chosen_channels = ["SMS"]  # Stored decision for after-hours
        lead_record.chosen_destinations = {
            "webhook_url": None,
            "sms_to_numbers": ["+15550000001"],
            "email_to_addresses": []
        }
        
        # Mock repository calls
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        self.delivery_service.delivery_repo.create_delivery_record.return_value = AsyncMock(id="delivery-123")
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_lead_delivery("lead-123", client_config)
        
        # Verify delivery record was created for SMS channel
        self.delivery_service.delivery_repo.create_delivery_record.assert_called_once()
        create_call = self.delivery_service.delivery_repo.create_delivery_record.call_args[1]
        
        assert create_call["channel"] == DeliveryChannel.SMS
        assert create_call["purpose"] == DeliveryPurpose.LEAD_DELIVERY
        assert create_call["destination"] == "+15550000001"
        
        # Verify task was enqueued
        mock_enqueue.assert_called_once_with("delivery-123")
    
    async def test_multiple_channels_fanout(self) -> None:
        """Test multiple channels fanout based on stored routing."""
        # Setup client config with routing
        client_config = ClientConfig(
            client_id="demo",
            delivery_channels=["WEBHOOK"],  # Base config
            webhook_url="https://base.example.com/webhook",
            sms_to_numbers=[],
            email_to_addresses=[],
            message_templates={},
            followup_flags={},
            routing_json={
                "profiles": [
                    {
                        "name": "multi_channel",
                        "match": {"time_window": "IN_HOURS"},
                        "delivery": {
                            "channels": ["WEBHOOK", "SMS", "EMAIL"],
                            "webhook_url": "https://multi.example.com/webhook",
                            "sms_to_numbers": ["+15550000001", "+15550000002"],
                            "email_to_addresses": ["leads@example.com", "manager@example.com"]
                        }
                    }
                ]
            }
        )
        
        # Setup lead record with stored routing decision
        lead_record = LeadRecord()
        lead_record.lead_id = "lead-123"
        lead_record.chosen_channels = ["WEBHOOK", "SMS", "EMAIL"]  # Stored decision for multi-channel
        lead_record.chosen_destinations = {
            "webhook_url": "https://multi.example.com/webhook",
            "sms_to_numbers": ["+15550000001", "+15550000002"],
            "email_to_addresses": ["leads@example.com", "manager@example.com"]
        }
        
        # Mock repository calls
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        self.delivery_service.delivery_repo.create_delivery_record.return_value = AsyncMock(id="delivery-123")
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_lead_delivery("lead-123", client_config)
        
        # Verify three delivery records were created
        assert self.delivery_service.delivery_repo.create_delivery_record.call_count == 3
        
        # Check each channel was created with correct destination
        calls = self.delivery_service.delivery_repo.create_delivery_record.call_args_list
        
        # First call should be WEBHOOK
        assert calls[0][1]["channel"] == DeliveryChannel.WEBHOOK
        assert calls[0][1]["destination"] == "https://multi.example.com/webhook"
        
        # Second call should be SMS (first number)
        assert calls[1][1]["channel"] == DeliveryChannel.SMS
        assert calls[1][1]["destination"] == "+15550000001"
        
        # Third call should be EMAIL (first address)
        assert calls[2][1]["channel"] == DeliveryChannel.EMAIL
        assert calls[2][1]["destination"] == "leads@example.com"
        
        # Verify all tasks were enqueued
        assert mock_enqueue.call_count == 3
    
    async def test_fallback_to_base_config(self) -> None:
        """Test fallback to base config when no routing decision stored."""
        # Setup client config with base config only
        client_config = ClientConfig(
            client_id="demo",
            delivery_channels=["WEBHOOK"],
            webhook_url="https://base.example.com/webhook",
            sms_to_numbers=["+15550000001"],
            email_to_addresses=["leads@example.com"],
            message_templates={},
            followup_flags={},
            routing_json=None  # No routing config
        )
        
        # Setup lead record with no stored routing decision
        lead_record = LeadRecord()
        lead_record.lead_id = "lead-123"
        lead_record.chosen_destinations = None  # No stored decision
        
        # Mock repository calls
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        self.delivery_service.delivery_repo.create_delivery_record.return_value = AsyncMock(id="delivery-123")
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_lead_delivery("lead-123", client_config)
        
        # Verify delivery record was created using base config
        self.delivery_service.delivery_repo.create_delivery_record.assert_called_once()
        create_call = self.delivery_service.delivery_repo.create_delivery_record.call_args[1]
        
        assert create_call["channel"] == DeliveryChannel.WEBHOOK
        assert create_call["destination"] == "https://base.example.com/webhook"
        
        # Verify task was enqueued
        mock_enqueue.assert_called_once_with("delivery-123")
    
    async def test_urgent_override_uses_stored_routing(self) -> None:
        """Test urgent override uses stored routing decisions."""
        # Setup client config with urgent override
        client_config = ClientConfig(
            client_id="demo",
            delivery_channels=["WEBHOOK"],
            webhook_url="https://base.example.com/webhook",
            sms_to_numbers=["+15550000001"],
            email_to_addresses=[],
            message_templates={},
            followup_flags={},
            routing_json={
                "profiles": [
                    {
                        "name": "urgent_escalation",
                        "match": {
                            "service_type_in": ["hvac_repair"],
                            "time_window": "AFTER_HOURS"
                        },
                        "delivery": {
                            "channels": ["SMS"],
                            "sms_to_numbers": ["+15550000001"]
                        },
                        "escalation": {
                            "urgent_escalation": True,
                            "urgent_override_channels": ["SMS"],
                            "urgent_override_recipients": ["+15550009999"]
                        }
                    }
                ]
            }
        )
        
        # Setup lead record with stored routing decision
        lead_record = LeadRecord()
        lead_record.lead_id = "lead-123"
        lead_record.chosen_channels = ["SMS"]
        lead_record.chosen_destinations = {
            "webhook_url": None,
            "sms_to_numbers": ["+15550000001"],
            "email_to_addresses": []
        }
        lead_record.urgency = UrgencyLevel.SAME_DAY
        lead_record.classification = CallClassification.QUALIFIED
        
        # Mock repository calls
        self.delivery_service.lead_repo.get_by_lead_id.return_value = lead_record
        self.delivery_service.delivery_repo.create_delivery_record.return_value = AsyncMock(id="delivery-123")
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            await self.delivery_service.enqueue_urgent_override(
                lead_id="lead-123",
                escalation_config={
                    "urgent_escalation": True,
                    "urgent_override_channels": ["SMS"],
                    "urgent_override_recipients": ["+15550009999"]
                },
                client_config=client_config
            )
        
        # Verify override recipient was used
        self.delivery_service._enqueue_channel_delivery.assert_called_once()
        override_call = self.delivery_service._enqueue_channel_delivery.call_args[1]
        
        assert override_call[1] == "lead-123"  # lead_id
        assert override_call[2] == "SMS"  # channel
        assert override_call[3] == "URGENT_ESCALATION"  # purpose
        assert override_call[4]["destination_override"] == "+15550009999"  # override recipient
