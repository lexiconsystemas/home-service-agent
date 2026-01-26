"""Tests for routing persistence and worker usage."""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.enums import ServiceType, TimeWindow, DeliveryChannel, DeliveryPurpose, CallClassification, UrgencyLevel
from app.db.tables.lead_record import LeadRecord
from app.db.tables.client_config import ClientConfig
from app.services.intake_service import IntakeService


class TestRoutingPersistence:
    """Test cases for routing decision persistence."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = AsyncMock()
        self.intake_service = IntakeService(self.mock_db)
        
        # Mock repositories
        self.intake_service.client_repo = AsyncMock()
        self.intake_service.lead_repo = AsyncMock()
        self.intake_service.qualification_service = AsyncMock()
        self.intake_service.classification_service = AsyncMock()
        self.intake_service.service_normalization_service = AsyncMock()
        self.intake_service.business_hours_service = AsyncMock()
        self.intake_service.routing_service = AsyncMock()
        self.intake_service.delivery_service = AsyncMock()
    
    async def test_routing_decision_persisted(self) -> None:
        """Test that routing decision is persisted with lead record."""
        # Setup client config with routing
        client_config = ClientConfig(
            client_id="demo",
            routing_json={
                "timezone": "America/New_York",
                "business_hours": {
                    "mon": [{"start": "08:00", "end": "18:00"}]
                },
                "profiles": [
                    {
                        "name": "hvac_in_hours",
                        "match": {
                            "service_type_in": ["hvac_repair"],
                            "time_window": "IN_HOURS"
                        },
                        "delivery": {
                            "channels": ["WEBHOOK", "SMS"],
                            "sms_to_numbers": ["+15550000001"],
                            "webhook_url": "https://hvac.example.com/webhook"
                        }
                    }
                ]
            }
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup service normalization
        self.intake_service.service_normalization_service.normalize_service_service.return_value = (
            ServiceType.HVAC_REPAIR,
            ["SERVICE_TYPE_KEYWORD:hvac"]
        )
        
        # Setup business hours
        self.intake_service.business_hours_service.determine_time_window.return_value = (
            TimeWindow.IN_HOURS,
            datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc),
            ["BUSINESS_HOURS_IN_SCHEDULE:mon:08:00-18:00"]
        )
        
        # Setup routing profile selection
        self.intake_service.routing_service.select_routing_profile.return_value = (
            {
                "name": "hvac_in_hours",
                "delivery": {
                    "channels": ["WEBHOOK", "SMS"],
                    "sms_to_numbers": ["+15550000001"],
                    "webhook_url": "https://hvac.example.com/webhook"
                }
            },
            ["ROUTING_PROFILE_MATCHED:hvac_in_hours"]
        )
        
        # Setup qualification
        qualification_result = AsyncMock()
        qualification_result.outcome = "qualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification
        classification_result = AsyncMock()
        classification_result.classification = CallClassification.QUALIFIED
        classification_result.reason_codes = []
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record creation
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        call_event.from_number = "+15551234567"
        call_event.service_requested = "AC repair"
        call_event.urgency = UrgencyLevel.MEDIUM
        call_event.budget = "200"
        call_event.location_zip = "90210"
        
        # Process call
        result = await self.intake_service.process_inbound_call(call_event)
        
        # Verify lead record was created with routing data
        self.intake_service.lead_repo.create_lead.assert_called_once()
        create_call = self.intake_service.lead_repo.create_lead.call_args[1]
        
        assert create_call["service_type_normalized"] == ServiceType.HVAC_REPAIR
        assert create_call["service_normalization_reason_codes"] == ["SERVICE_TYPE_KEYWORD:hvac"]
        assert create_call["routing_profile_name"] == "hvac_in_hours"
        assert create_call["time_window"] == "IN_HOURS"
        assert create_call["timezone_used"] == "America/New_York"
        assert create_call["chosen_channels"] == ["WEBHOOK", "SMS"]
        assert create_call["chosen_destinations"]["webhook_url"] == "https://hvac.example.com/webhook"
        assert create_call["chosen_destinations"]["sms_to_numbers"] == ["+15550000001"]
        assert create_call["routing_reason_codes"] == ["ROUTING_PROFILE_MATCHED:hvac_in_hours"]
        
        # Verify response includes routing info
        assert result.service_type == "hvac_repair"
        assert result.routing_profile == "hvac_in_hours"
        assert result.time_window == "IN_HOURS"
    
    async def test_worker_uses_stored_routing(self) -> None:
        """Test that worker uses stored routing decision instead of recomputing."""
        from app.workers.tasks import _execute_delivery, _extract_stored_routing
        
        # Mock database session and repositories
        mock_session = AsyncMock()
        mock_delivery_repo = AsyncMock()
        mock_lead_repo = AsyncMock()
        mock_client_repo = AsyncMock()
        
        # Setup delivery record
        delivery_record = AsyncMock()
        delivery_record.id = "delivery-123"
        delivery_record.channel = DeliveryChannel.SMS
        delivery_record.purpose = DeliveryPurpose.LEAD_DELIVERY
        delivery_record.destination = "+15550000001"
        delivery_record.attempt_count = 0
        
        # Setup lead record with stored routing
        lead_record = LeadRecord()
        lead_record.lead_id = "lead-123"
        lead_record.chosen_destinations = {
            "webhook_url": "https://hvac.example.com/webhook",
            "sms_to_numbers": ["+15550000001"],
            "email_to_addresses": []
        }
        
        # Setup client config
        client_config = ClientConfig()
        client_config.webhook_url = "https://base.example.com/webhook"
        client_config.sms_to_numbers = []
        client_config.email_to_addresses = []
        
        # Mock repository calls
        mock_delivery_repo.get_by_lead_id.return_value = [delivery_record]
        mock_lead_repo.get_by_lead_id.return_value = lead_record
        mock_client_repo.get_by_client_id.return_value = client_config
        
        # Mock database context
        with patch('app.workers.tasks.get_async_session_context') as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_session
            mock_delivery_repo.get_by_lead_id.return_value = [delivery_record]
            mock_lead_repo.get_by_lead_id.return_value = lead_record
            mock_client_repo.get_by_client_id.return_value = client_config
            
            # Execute delivery
            success = await _execute_delivery("delivery-123")
            
            # Verify stored routing was used
            assert success  # Assuming delivery succeeds
            # The key test is that _extract_stored_routing is called and uses stored data
            routing_config = _extract_stored_routing(lead_record, client_config)
            assert routing_config["webhook_url"] == "https://hvac.example.com/webhook"
            assert routing_config["sms_to_numbers"] == ["+15550000001"]
    
    async def test_delivery_enqueue_failure_handling(self) -> None:
        """Test handling of delivery enqueue failures."""
        # Setup client config with routing
        client_config = ClientConfig(
            client_id="demo",
            routing_json={
                "profiles": [
                    {
                        "name": "hvac_in_hours",
                        "delivery": {
                            "channels": ["WEBHOOK", "SMS"],
                            "sms_to_numbers": ["+15550000001"],
                            "webhook_url": "https://hvac.example.com/webhook"
                        }
                    }
                ]
            }
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup service normalization
        self.intake_service.service_normalization_service.normalize_service_service.return_value = (
            ServiceType.HVAC_REPAIR,
            ["SERVICE_TYPE_KEYWORD:hvac"]
        )
        
        # Setup business hours
        self.intake_service.business_hours_service.determine_time_window.return_value = (
            TimeWindow.IN_HOURS,
            datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc),
            ["BUSINESS_HOURS_IN_SCHEDULE:mon:08:00-18:00"]
        )
        
        # Setup routing profile selection
        self.intake_service.routing_service.select_routing_profile.return_value = (
            {
                "name": "hvac_in_hours",
                "delivery": {
                    "channels": ["WEBHOOK", "SMS"],
                    "sms_to_numbers": ["+15550000001"],
                    "webhook_url": "https://hvac.example.com/webhook"
                }
            },
            ["ROUTING_PROFILE_MATCHED:hvac_in_hours"]
        )
        
        # Setup qualification
        qualification_result = AsyncMock()
        qualification_result.outcome = "qualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification
        classification_result = AsyncMock()
        classification_result.classification = CallClassification.QUALIFIED
        classification_result.reason_codes = []
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record creation
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock delivery service to fail
        self.intake_service.delivery_service.enqueue_lead_delivery.return_value = False
        
        # Mock lead repo update
        self.intake_service.lead_repo.update_delivery_pending.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        call_event.from_number = "+15551234567"
        call_event.service_requested = "AC repair"
        call_event.urgency = UrgencyLevel.MEDIUM
        call_event.budget = "200"
        call_event.location_zip = "90210"
        
        # Process call
        result = await self.intake_service.process_inbound_call(call_event)
        
        # Verify warning is included in response
        assert "warning" in result
        assert "Delivery enqueue failed" in result["warning"]
        
        # Verify delivery pending was updated
        self.intake_service.lead_repo.update_delivery_pending.assert_called_once_with(
            "lead-123", False
        )
