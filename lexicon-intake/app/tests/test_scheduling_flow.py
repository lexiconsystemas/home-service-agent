"""Tests for scheduling-lite functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from app.core.enums import CallClassification
from app.services.scheduling_service import SchedulingService


class TestSchedulingFlow:
    """Test cases for scheduling-lite functionality."""
    
    @pytest.mark.asyncio
    async def test_qualified_lead_receives_scheduling_sms(self):
        """Test that qualified leads receive scheduling SMS when enabled."""
        # Create mock lead
        lead = AsyncMock()
        lead.lead_id = "test-lead-id"
        lead.classification = CallClassification.QUALIFIED
        lead.scheduled_window_label = None
        
        # Mock lead repository
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = lead
        lead_repo.update_scheduling_selection.return_value = lead
        
        # Create scheduling service
        scheduling_service = SchedulingService(lead_repo)
        
        # Routing config with scheduling enabled
        routing_config = {
            "scheduling": {
                "enabled": True,
                "windows": [
                    {"label": "Today 2-4pm", "start_offset_min": 0, "end_offset_min": 120},
                    {"label": "Today 4-6pm", "start_offset_min": 120, "end_offset_min": 240},
                ]
            }
        }
        
        # Test scheduling should be offered
        should_offer = scheduling_service.should_offer_scheduling(
            lead.classification,
            routing_config
        )
        assert should_offer == True
        
        # Generate available windows
        base_time = datetime(2024, 1, 15, 10, 0, 0)  # 10 AM
        available_windows = scheduling_service.generate_scheduling_windows(
            base_time=base_time,
            timezone_str="America/New_York",
            windows_config=routing_config["scheduling"]["windows"]
        )
        
        # Verify windows are generated correctly
        assert len(available_windows) == 2
        assert available_windows[0]["label"] == "Today 2-4pm"
        assert available_windows[1]["label"] == "Today 4-6pm"
        
        # Generate SMS message
        sms_message = scheduling_service.generate_scheduling_sms(available_windows)
        
        # Verify SMS contains options
        assert "We can help" in sms_message
        assert "1" in sms_message
        assert "2" in sms_message
        assert "Today 2-4pm" in sms_message
        assert "Today 4-6pm" in sms_message
    
    @pytest.mark.asyncio
    async def test_unqualified_lead_no_scheduling(self):
        """Test that unqualified leads do not receive scheduling."""
        # Create mock lead
        lead = AsyncMock()
        lead.classification = CallClassification.UNQUALIFIED
        
        # Create scheduling service
        scheduling_service = SchedulingService(AsyncMock())
        
        # Routing config with scheduling enabled
        routing_config = {
            "scheduling": {
                "enabled": True,
                "windows": []
            }
        }
        
        # Test scheduling should NOT be offered
        should_offer = scheduling_service.should_offer_scheduling(
            lead.classification,
            routing_config
        )
        assert should_offer == False
    
    @pytest.mark.asyncio
    async def test_scheduling_disabled_no_sms(self):
        """Test that leads don't receive scheduling SMS when disabled."""
        # Create mock lead
        lead = AsyncMock()
        lead.classification = CallClassification.QUALIFIED
        
        # Create scheduling service
        scheduling_service = SchedulingService(AsyncMock())
        
        # Routing config with scheduling disabled
        routing_config = {
            "scheduling": {
                "enabled": False,
                "windows": []
            }
        }
        
        # Test scheduling should NOT be offered
        should_offer = scheduling_service.should_offer_scheduling(
            lead.classification,
            routing_config
        )
        assert should_offer == False
    
    @pytest.mark.asyncio
    async def test_valid_scheduling_response_processed(self):
        """Test that valid scheduling responses are processed correctly."""
        # Create mock lead
        lead = AsyncMock()
        lead.lead_id = "test-lead-id"
        lead.classification = CallClassification.QUALIFIED
        lead.scheduled_window_label = None
        
        # Mock lead repository
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = lead
        lead_repo.update_scheduling_selection.return_value = lead
        
        # Create scheduling service
        scheduling_service = SchedulingService(lead_repo)
        
        # Create available windows
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        available_windows = [
            {
                "label": "Today 2-4pm",
                "start_time": base_time + timedelta(hours=4),
                "end_time": base_time + timedelta(hours=6),
                "start_offset_min": 240,
                "end_offset_min": 360,
            },
            {
                "label": "Today 4-6pm",
                "start_time": base_time + timedelta(hours=6),
                "end_time": base_time + timedelta(hours=8),
                "start_offset_min": 360,
                "end_offset_min": 480,
            }
        ]
        
        # Process valid response "1"
        success, error_message, selected_window = await scheduling_service.process_scheduling_response(
            lead_id="test-lead-id",
            response="1",
            available_windows=available_windows
        )
        
        # Verify success
        assert success == True
        assert error_message is None
        assert selected_window["label"] == "Today 2-4pm"
        
        # Verify lead was updated
        lead_repo.update_scheduling_selection.assert_called_once_with(
            lead_id="test-lead-id",
            window_label="Today 2-4pm",
            start_estimate=available_windows[0]["start_time"],
            end_estimate=available_windows[0]["end_time"]
        )
    
    @pytest.mark.asyncio
    async def test_invalid_scheduling_response_handled(self):
        """Test that invalid scheduling responses are handled correctly."""
        # Create mock lead
        lead = AsyncMock()
        lead.lead_id = "test-lead-id"
        lead.classification = CallClassification.QUALIFIED
        lead.scheduled_window_label = None
        
        # Mock lead repository
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = lead
        
        # Create scheduling service
        scheduling_service = SchedulingService(lead_repo)
        
        # Create available windows
        available_windows = [
            {"label": "Today 2-4pm", "start_time": datetime.now(), "end_time": datetime.now()},
            {"label": "Today 4-6pm", "start_time": datetime.now(), "end_time": datetime.now()},
        ]
        
        # Test invalid responses
        invalid_responses = ["3", "0", "abc", "", "x", "99"]
        
        for response in invalid_responses:
            success, error_message, selected_window = await scheduling_service.process_scheduling_response(
                lead_id="test-lead-id",
                response=response,
                available_windows=available_windows
            )
            
            # Verify failure
            assert success == False
            assert error_message is not None
            assert selected_window is None
            assert "Invalid response" in error_message or "System error" in error_message
    
    @pytest.mark.asyncio
    async def test_scheduling_window_generation_with_timezone(self):
        """Test scheduling window generation with timezone handling."""
        # Create scheduling service
        scheduling_service = SchedulingService(AsyncMock())
        
        # Test with different timezones
        base_time = datetime(2024, 1, 15, 10, 0, 0)  # 10 AM UTC
        windows_config = [
            {"label": "Today 2-4pm", "start_offset_min": 0, "end_offset_min": 120},
            {"label": "Tomorrow Morning", "start_offset_min": 1440, "end_offset_min": 1800}
        ]
        
        # Test Eastern Time
        et_windows = scheduling_service.generate_scheduling_windows(
            base_time=base_time,
            timezone_str="America/New_York",
            windows_config=windows_config
        )
        
        # Test Pacific Time
        pt_windows = scheduling_service.generate_scheduling_windows(
            base_time=base_time,
            timezone_str="America/Los_Angeles",
            windows_config=windows_config
        )
        
        # Verify windows are generated for both timezones
        assert len(et_windows) == 2
        assert len(pt_windows) == 2
        
        # Verify timezone info is preserved
        for window in et_windows:
            assert window["start_time"].tzinfo == ZoneInfo("America/New_York")
            assert window["end_time"].tzinfo == ZoneInfo("America/New_York")
        
        for window in pt_windows:
            assert window["start_time"].tzinfo == ZoneInfo("America/Los_Angeles")
            assert window["end_time"].tzinfo == ZoneInfo("America/Los_Angeles")
    
    @pytest.mark.asyncio
    async def test_scheduling_configuration_validation(self):
        """Test scheduling configuration validation."""
        # Create scheduling service
        scheduling_service = SchedulingService(AsyncMock())
        
        # Test valid configuration
        valid_config = {
            "enabled": True,
            "windows": [
                {"label": "Today 2-4pm", "start_offset_min": 0, "end_offset_min": 120},
                {"label": "Today 4-6pm", "start_offset_min": 120, "end_offset_min": 240}
            ]
        }
        
        is_valid, errors = scheduling_service.validate_scheduling_config(valid_config)
        assert is_valid == True
        assert len(errors) == 0
        
        # Test invalid configurations
        invalid_configs = [
            # Empty windows
            {"enabled": True, "windows": []},
            # Missing label
            {"enabled": True, "windows": [{"start_offset_min": 0, "end_offset_min": 120}]},
            # Negative offsets
            {"enabled": True, "windows": [{"label": "Test", "start_offset_min": -10, "end_offset_min": 120}]},
            # Start >= end
            {"enabled": True, "windows": [{"label": "Test", "start_offset_min": 120, "end_offset_min": 120}]},
        ]
        
        for config in invalid_configs:
            is_valid, errors = scheduling_service.validate_scheduling_config(config)
            assert is_valid == False
            assert len(errors) > 0
    
    @pytest.mark.asyncio
    async def test_confirmation_message_generation(self):
        """Test confirmation message generation after window selection."""
        # Create scheduling service
        scheduling_service = SchedulingService(AsyncMock())
        
        # Create selected window
        selected_window = {
            "label": "Today 2-4pm",
            "start_time": datetime.now(),
            "end_time": datetime.now(),
        }
        
        # Generate confirmation message
        confirmation = scheduling_service.generate_confirmation_message(selected_window)
        
        # Verify message content
        assert "Thank you" in confirmation
        assert "scheduled" in confirmation.lower()
        assert "Today 2-4pm" in confirmation
        assert "reminder" in confirmation.lower()
    
    @pytest.mark.asyncio
    async def test_scheduling_response_edge_cases(self):
        """Test edge cases in scheduling response processing."""
        # Create mock lead
        lead = AsyncMock()
        lead.lead_id = "test-lead-id"
        lead.classification = CallClassification.QUALIFIED
        lead.scheduled_window_label = None
        
        # Mock lead repository
        lead_repo = AsyncMock()
        lead_repo.get_by_lead_id.return_value = lead
        lead_repo.update_scheduling_selection.return_value = lead
        
        # Create scheduling service
        scheduling_service = SchedulingService(lead_repo)
        
        # Create available windows
        available_windows = [
            {"label": "Today 2-4pm", "start_time": datetime.now(), "end_time": datetime.now()},
        ]
        
        # Test response with extra whitespace
        success, error_message, selected_window = await scheduling_service.process_scheduling_response(
            lead_id="test-lead-id",
            response="  1  ",
            available_windows=available_windows
        )
        assert success == True
        assert selected_window["label"] == "Today 2-4pm"
        
        # Test response with text before number
        success, error_message, selected_window = await scheduling_service.process_scheduling_response(
            lead_id="test-lead-id",
            response="I choose 1",
            available_windows=available_windows
        )
        assert success == True
        assert selected_window["label"] == "Today 2-4pm"
    
    @pytest.mark.asyncio
    async def test_scheduling_with_no_windows_configured(self):
        """Test scheduling behavior when no windows are configured."""
        # Create mock lead
        lead = AsyncMock()
        lead.classification = CallClassification.QUALIFIED
        
        # Create scheduling service
        scheduling_service = SchedulingService(AsyncMock())
        
        # Routing config with scheduling enabled but no windows
        routing_config = {
            "scheduling": {
                "enabled": True,
                "windows": []
            }
        }
        
        # Test scheduling should be offered but no windows generated
        should_offer = scheduling_service.should_offer_scheduling(
            lead.classification,
            routing_config
        )
        assert should_offer == True
        
        # Generate windows (should return empty list)
        windows = scheduling_service.generate_scheduling_windows(
            base_time=datetime.now(),
            timezone_str="America/New_York",
            windows_config=[]
        )
        assert len(windows) == 0
        
        # Generate SMS message (should return fallback)
        sms_message = scheduling_service.generate_scheduling_sms(windows)
        assert "Please call us" in sms_message
