"""Tests for follow-up automation."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.core.enums import CallClassification
from app.db.tables.client_config import ClientConfig
from app.db.tables.lead_record import LeadRecord
from app.services.intake_service import IntakeService


class TestFollowupAutomation:
    """Test cases for follow-up automation."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db = AsyncMock()
        self.intake_service = IntakeService(self.mock_db)
        
        # Mock repositories
        self.intake_service.client_repo = AsyncMock()
        self.intake_service.lead_repo = AsyncMock()
        self.intake_service.qualification_service = AsyncMock()
        self.intake_service.classification_service = AsyncMock()
        self.intake_service.delivery_service = AsyncMock()
    
    async def test_followup_for_qualified_lead(self) -> None:
        """Test follow-up automation for qualified leads."""
        # Setup client config with all follow-up enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": True,
                "send_reminder_to_caller": True,
                "reminder_delay_minutes": 30,
                "urgent_escalation": True,
            },
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup qualification result
        qualification_result = AsyncMock()
        qualification_result.outcome = "qualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification result
        classification_result = AsyncMock()
        classification_result.classification.value = "QUALIFIED"
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        
        # Execute intake process
        with patch('uuid.uuid4', return_value="lead-123"):
            await self.intake_service.process_inbound_call(call_event)
        
        # Verify all follow-up methods called for qualified lead
        self.intake_service.delivery_service.enqueue_followup_confirmation.assert_called_once()
        self.intake_service.delivery_service.enqueue_followup_reminder.assert_called_once()
        self.intake_service.delivery_service.enqueue_urgent_escalation.assert_called_once()
    
    async def test_followup_for_unqualified_lead(self) -> None:
        """Test follow-up automation for unqualified leads."""
        # Setup client config with all follow-up enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": True,
                "send_reminder_to_caller": True,
                "reminder_delay_minutes": 30,
                "urgent_escalation": True,
            },
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup qualification result
        qualification_result = AsyncMock()
        qualification_result.outcome = "unqualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification result
        classification_result = AsyncMock()
        classification_result.classification.value = "UNQUALIFIED"
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        
        # Execute intake process
        with patch('uuid.uuid4', return_value="lead-123"):
            await self.intake_service.process_inbound_call(call_event)
        
        # Verify only confirmation and escalation called for unqualified lead
        self.intake_service.delivery_service.enqueue_followup_confirmation.assert_called_once()
        self.intake_service.delivery_service.enqueue_followup_reminder.assert_not_called()  # No reminder for unqualified
        self.intake_service.delivery_service.enqueue_urgent_escalation.assert_called_once()
    
    async def test_no_followup_for_spam_lead(self) -> None:
        """Test no follow-up automation for spam leads."""
        # Setup client config with all follow-up enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": True,
                "send_reminder_to_caller": True,
                "reminder_delay_minutes": 30,
                "urgent_escalation": True,
            },
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup qualification result
        qualification_result = AsyncMock()
        qualification_result.outcome = "unqualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification result
        classification_result = AsyncMock()
        classification_result.classification.value = "SPAM"
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        
        # Execute intake process
        with patch('uuid.uuid4', return_value="lead-123"):
            await self.intake_service.process_inbound_call(call_event)
        
        # Verify no follow-up methods called for spam lead
        self.intake_service.delivery_service.enqueue_followup_confirmation.assert_not_called()
        self.intake_service.delivery_service.enqueue_followup_reminder.assert_not_called()
        self.intake_service.delivery_service.enqueue_urgent_escalation.assert_not_called()
    
    async def test_no_followup_for_dropped_lead(self) -> None:
        """Test no follow-up automation for dropped leads."""
        # Setup client config with all follow-up enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": True,
                "send_reminder_to_caller": True,
                "reminder_delay_minutes": 30,
                "urgent_escalation": True,
            },
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup qualification result
        qualification_result = AsyncMock()
        qualification_result.outcome = "unqualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification result
        classification_result = AsyncMock()
        classification_result.classification.value = "DROPPED"
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        
        # Execute intake process
        with patch('uuid.uuid4', return_value="lead-123"):
            await self.intake_service.process_inbound_call(call_event)
        
        # Verify no follow-up methods called for dropped lead
        self.intake_service.delivery_service.enqueue_followup_confirmation.assert_not_called()
        self.intake_service.delivery_service.enqueue_followup_reminder.assert_not_called()
        self.intake_service.delivery_service.enqueue_urgent_escalation.assert_not_called()
    
    async def test_followup_disabled_in_config(self) -> None:
        """Test no follow-up when disabled in client config."""
        # Setup client config with all follow-up disabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": False,
                "send_reminder_to_caller": False,
                "reminder_delay_minutes": 30,
                "urgent_escalation": False,
            },
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup qualification result
        qualification_result = AsyncMock()
        qualification_result.outcome = "qualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification result
        classification_result = AsyncMock()
        classification_result.classification.value = "QUALIFIED"
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        
        # Execute intake process
        with patch('uuid.uuid4', return_value="lead-123"):
            await self.intake_service.process_inbound_call(call_event)
        
        # Verify no follow-up methods called when disabled
        self.intake_service.delivery_service.enqueue_followup_confirmation.assert_not_called()
        self.intake_service.delivery_service.enqueue_followup_reminder.assert_not_called()
        self.intake_service.delivery_service.enqueue_urgent_escalation.assert_not_called()
    
    async def test_partial_followup_enabled(self) -> None:
        """Test partial follow-up configuration."""
        # Setup client config with only confirmation enabled
        client_config = ClientConfig(
            client_id="demo",
            followup_flags={
                "send_confirmation_to_caller": True,
                "send_reminder_to_caller": False,
                "reminder_delay_minutes": 30,
                "urgent_escalation": False,
            },
        )
        self.intake_service.client_repo.get_by_to_number.return_value = client_config
        
        # Setup qualification result
        qualification_result = AsyncMock()
        qualification_result.outcome = "qualified"
        self.intake_service.qualification_service.qualify_call.return_value = qualification_result
        
        # Setup classification result
        classification_result = AsyncMock()
        classification_result.classification.value = "QUALIFIED"
        self.intake_service.classification_service.classify_call.return_value = classification_result
        
        # Setup lead record
        lead_record = AsyncMock()
        lead_record.lead_id = "lead-123"
        self.intake_service.lead_repo.create_lead.return_value = lead_record
        
        # Mock call event
        call_event = AsyncMock()
        call_event.call_id = "call-123"
        call_event.to_number = "+15550001111"
        
        # Execute intake process
        with patch('uuid.uuid4', return_value="lead-123"):
            await self.intake_service.process_inbound_call(call_event)
        
        # Verify only confirmation called
        self.intake_service.delivery_service.enqueue_followup_confirmation.assert_called_once()
        self.intake_service.delivery_service.enqueue_followup_reminder.assert_not_called()
        self.intake_service.delivery_service.enqueue_urgent_escalation.assert_not_called()
