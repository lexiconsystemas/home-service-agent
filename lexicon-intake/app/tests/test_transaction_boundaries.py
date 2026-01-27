"""Tests for transaction boundaries in services."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intake_service import IntakeService
from app.services.delivery_service import DeliveryService
from app.domain.models.call_event import CallEvent
from app.core.enums import DeliveryChannel, DeliveryPurpose


class TestIntakeServiceTransactions:
    """Test transaction boundaries in IntakeService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        # Mock the context manager for begin()
        session.begin = MagicMock()
        session.begin.return_value.__aenter__ = AsyncMock()
        session.begin.return_value.__aexit__ = AsyncMock()
        return session
    
    @pytest.fixture
    def intake_service(self, mock_db):
        """Create intake service with mocked dependencies."""
        service = IntakeService(mock_db)
        # Mock all repositories
        service.client_repo = AsyncMock()
        service.lead_repo = AsyncMock()
        service.qualification_service = AsyncMock()
        service.classification_service = AsyncMock()
        service.service_normalization_service = AsyncMock()
        service.business_hours_service = AsyncMock()
        service.routing_service = AsyncMock()
        service.delivery_service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_process_inbound_call_uses_transaction(self, intake_service, mock_db):
        """Test that process_inbound_call uses proper transaction boundaries."""
        
        # Setup mocks - simplify to focus on transaction
        mock_client_config = MagicMock()
        mock_client_config.client_id = "test-client"
        mock_client_config.routing_json = None  # No routing to simplify
        mock_client_config.delivery_channels = ["WEBHOOK"]
        intake_service.client_repo.get_by_to_number.return_value = mock_client_config
        intake_service.client_repo.get_by_client_id.return_value = None
        
        # Mock all service methods to return simple values
        mock_service_type = MagicMock()
        mock_service_type.value = "hvac_repair"
        intake_service.service_normalization_service.normalize_service_type = AsyncMock(
            return_value=(mock_service_type, [])
        )
        
        mock_qualification = MagicMock()
        mock_qualification.outcome = "PASS"
        intake_service.qualification_service.qualify_call = AsyncMock(return_value=mock_qualification)
        
        mock_classification = MagicMock()
        mock_classification.classification.value = "QUALIFIED"
        mock_classification.reason_codes = []
        intake_service.classification_service.classify_call = AsyncMock(return_value=mock_classification)
        
        # Mock business hours and routing to return None/empty
        intake_service.business_hours_service.determine_time_window = AsyncMock(
            return_value=(None, None, [])
        )
        intake_service.routing_service.select_routing_profile = AsyncMock(
            return_value=(None, [])
        )
        
        mock_lead_record = MagicMock()
        intake_service.lead_repo.create_lead.return_value = mock_lead_record
        intake_service.lead_repo.update_delivery_pending = AsyncMock()
        
        intake_service.delivery_service._enqueue_delivery_with_routing.return_value = True
        intake_service.delivery_service._enqueue_followup_with_routing = AsyncMock()
        
        # Create test call event
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="+1234567890",
            to_number="+0987654321",
            timestamp=datetime.now(),
            caller_name="Test Caller",
            service_requested="HVAC Repair",
            urgency="medium",
            budget=500,
            location_zip="12345"
        )
        
        # Execute
        await intake_service.process_inbound_call(call_event)
        
        # Verify transaction was used
        mock_db.begin.assert_called_once()
        
        # Verify lead creation happened within transaction
        intake_service.lead_repo.create_lead.assert_called_once()
        
        # Verify delivery tasks were enqueued AFTER transaction
        intake_service.delivery_service._enqueue_delivery_with_routing.assert_called_once()
        intake_service.delivery_service._enqueue_followup_with_routing.assert_called_once()


class TestDeliveryServiceTransactions:
    """Test transaction boundaries in DeliveryService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        # Mock the context manager for begin()
        session.begin = MagicMock()
        session.begin.return_value.__aenter__ = AsyncMock()
        session.begin.return_value.__aexit__ = AsyncMock()
        return session
    
    @pytest.fixture
    def delivery_service(self, mock_db):
        """Create delivery service with mocked dependencies."""
        service = DeliveryService(mock_db)
        service.delivery_repo = AsyncMock()
        service.lead_repo = AsyncMock()
        service.client_repo = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_enqueue_channel_delivery_uses_transaction(self, delivery_service, mock_db):
        """Test that _enqueue_channel_delivery uses proper transaction boundaries."""
        
        # Setup mocks
        mock_delivery_record = MagicMock()
        mock_delivery_record.id = "test-delivery-id"
        delivery_service.delivery_repo.create_delivery_record.return_value = mock_delivery_record
        
        mock_client_config = MagicMock()
        mock_client_config.webhook_url = "https://example.com/webhook"
        mock_client_config.sms_to_numbers = ["+1234567890"]
        mock_client_config.email_to_addresses = ["test@example.com"]
        
        mock_lead_record = MagicMock()
        mock_lead_record.caller_phone = "+1234567890"
        delivery_service.lead_repo.get_by_lead_id.return_value = mock_lead_record
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_delivery_task') as mock_enqueue:
            mock_enqueue.return_value = None
            
            # Execute
            await delivery_service._enqueue_channel_delivery(
                lead_id="test-lead-123",
                channel=DeliveryChannel.WEBHOOK,
                purpose=DeliveryPurpose.LEAD_DELIVERY,
                client_config=mock_client_config,
            )
            
            # Verify transaction was used
            mock_db.begin.assert_called_once()
            
            # Verify delivery record was created within transaction
            delivery_service.delivery_repo.create_delivery_record.assert_called_once()
            
            # Verify task was enqueued AFTER transaction
            mock_enqueue.assert_called_once_with("test-delivery-id")
    
    @pytest.mark.asyncio
    async def test_enqueue_followup_reminder_uses_transaction(self, delivery_service, mock_db):
        """Test that enqueue_followup_reminder uses proper transaction boundaries."""
        
        # Setup mocks
        mock_delivery_record = MagicMock()
        mock_delivery_record.id = "test-delivery-id"
        delivery_service.delivery_repo.create_delivery_record.return_value = mock_delivery_record
        
        mock_client_config = MagicMock()
        mock_client_config.followup_flags = {
            "send_reminder_to_caller": True,
            "reminder_delay_minutes": 30
        }
        
        mock_lead_record = MagicMock()
        mock_lead_record.classification.value = "QUALIFIED"
        mock_lead_record.caller_phone = "+1234567890"
        delivery_service.lead_repo.get_by_lead_id.return_value = mock_lead_record
        
        # Mock enqueue task
        with patch('app.services.delivery_service.enqueue_followup_task') as mock_enqueue:
            mock_enqueue.return_value = None
            
            # Execute
            await delivery_service.enqueue_followup_reminder(
                lead_id="test-lead-123",
                client_config=mock_client_config,
            )
            
            # Verify transaction was used
            mock_db.begin.assert_called_once()
            
            # Verify delivery record was created within transaction
            delivery_service.delivery_repo.create_delivery_record.assert_called_once()
            
            # Verify task was enqueued AFTER transaction
            mock_enqueue.assert_called_once_with(
                delivery_id="test-delivery-id",
                delay_minutes=30
            )
    
    @pytest.mark.asyncio
    async def test_no_destination_skips_transaction(self, delivery_service, mock_db):
        """Test that missing destination skips transaction and task enqueue."""
        
        # Setup mocks
        mock_client_config = MagicMock()
        mock_client_config.webhook_url = None  # No destination
        mock_client_config.sms_to_numbers = []
        mock_client_config.email_to_addresses = []
        
        delivery_service.lead_repo.get_by_lead_id.return_value = None
        
        # Execute
        await delivery_service._enqueue_channel_delivery(
            lead_id="test-lead-123",
            channel=DeliveryChannel.WEBHOOK,
            purpose=DeliveryPurpose.LEAD_DELIVERY,
            client_config=mock_client_config,
        )
        
        # Verify transaction was NOT used
        mock_db.begin.assert_not_called()
        
        # Verify delivery record was NOT created
        delivery_service.delivery_repo.create_delivery_record.assert_not_called()


class TestTransactionAtomicity:
    """Test transaction atomicity and rollback behavior."""
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """Test that transactions are rolled back on errors."""
        
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.begin = MagicMock()
        
        # Mock transaction context that raises an error
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock(return_value=True)  # No exception
        
        mock_db.begin.return_value = mock_transaction
        
        # Create service
        intake_service = IntakeService(mock_db)
        intake_service.client_repo = AsyncMock()
        intake_service.lead_repo = AsyncMock()
        intake_service.qualification_service = AsyncMock()
        intake_service.classification_service = AsyncMock()
        intake_service.service_normalization_service = AsyncMock()
        intake_service.business_hours_service = AsyncMock()
        intake_service.routing_service = AsyncMock()
        intake_service.delivery_service = AsyncMock()
        
        # Setup mocks to raise an error during lead creation
        mock_client_config = MagicMock()
        mock_client_config.client_id = "test-client"
        mock_client_config.routing_json = None
        intake_service.client_repo.get_by_to_number.return_value = mock_client_config
        
        intake_service.service_normalization_service.normalize_service_type = AsyncMock(
            return_value=(MagicMock(), [])
        )
        intake_service.qualification_service.qualify_call = AsyncMock(return_value=MagicMock())
        intake_service.classification_service.classify_call = AsyncMock(return_value=MagicMock())
        
        # Make lead creation raise an error
        intake_service.lead_repo.create_lead.side_effect = Exception("Database error")
        
        # Create test call event
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="+1234567890",
            to_number="+0987654321",
            timestamp=datetime.now(),
            caller_name="Test Caller",
            service_requested="HVAC Repair",
            urgency="medium",
            budget=500,
            location_zip="12345"
        )
        
        # Execute and expect exception
        with pytest.raises(Exception, match="Database error"):
            await intake_service.process_inbound_call(call_event)
        
        # Verify transaction was used
        mock_db.begin.assert_called_once()
        
        # Verify transaction context was entered and exited
        mock_transaction.__aenter__.assert_called_once()
        mock_transaction.__aexit__.assert_called_once()
