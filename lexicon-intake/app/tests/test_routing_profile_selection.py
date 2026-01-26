"""Tests for routing profile selection."""

import datetime

import pytest

from app.services.routing_service import RoutingService
from app.core.enums import ServiceType, TimeWindow


class TestRoutingProfileSelection:
    """Test cases for routing profile selection."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = RoutingService()
        
        # Sample routing configuration
        self.routing_config = {
            "timezone": "America/New_York",
            "business_hours": {
                "mon": [{"start": "08:00", "end": "18:00"}],
                "tue": [{"start": "08:00", "end": "18:00"}],
                "wed": [{"start": "08:00", "end": "18:00"}],
                "thu": [{"start": "08:00", "end": "18:00"}],
                "fri": [{"start": "08:00", "end": "18:00"}],
                "sat": [{"start": "10:00", "end": "14:00"}],
                "sun": []
            },
            "profiles": [
                {
                    "name": "hvac_in_hours",
                    "match": {
                        "service_type_in": ["hvac_repair", "hvac_install"],
                        "time_window": "IN_HOURS"
                    },
                    "delivery": {
                        "channels": ["WEBHOOK", "SMS"],
                        "sms_to_numbers": ["+15550000001"],
                        "webhook_url": "https://hvac.example.com/webhook"
                    },
                    "followup": {
                        "send_confirmation_to_caller": True,
                        "send_reminder_to_caller": False
                    }
                },
                {
                    "name": "hvac_after_hours",
                    "match": {
                        "service_type_in": ["hvac_repair", "hvac_install"],
                        "time_window": "AFTER_HOURS"
                    },
                    "delivery": {
                        "channels": ["SMS"],
                        "sms_to_numbers": ["+15550000002"]
                    },
                    "followup": {
                        "send_confirmation_to_caller": True,
                        "send_reminder_to_caller": True,
                        "reminder_delay_minutes": 30
                    }
                },
                {
                    "name": "default_in_hours",
                    "match": {
                        "time_window": "IN_HOURS"
                    },
                    "delivery": {
                        "channels": ["WEBHOOK"],
                        "webhook_url": "https://default.example.com/webhook"
                    },
                    "followup": {
                        "send_confirmation_to_caller": False
                    }
                },
                {
                    "name": "default_after_hours",
                    "match": {
                        "time_window": "AFTER_HOURS"
                    },
                    "delivery": {
                        "channels": ["SMS"],
                        "sms_to_numbers": ["+15550000003"]
                    },
                    "followup": {
                        "send_confirmation_to_caller": True
                    }
                }
            ]
        }
        
        self.base_config = {
            "delivery_channels": ["WEBHOOK"],
            "webhook_url": "https://base.example.com/webhook",
            "sms_to_numbers": [],
            "email_to_addresses": [],
            "followup_flags": {},
        }
    
    def test_hvac_in_hours_match(self) -> None:
        """Test HVAC service type match during business hours."""
        utc_timestamp = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        local_time = datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        profile, reason_codes = self.service.select_routing_profile(
            service_type=ServiceType.HVAC_REPAIR,
            time_window=TimeWindow.IN_HOURS,
            routing_json=self.routing_config,
            utc_timestamp=utc_timestamp,
            timezone="America/New_York",
            local_time=local_time,
        )
        
        assert profile is not None
        assert profile["name"] == "hvac_in_hours"
        assert "ROUTING_PROFILE_MATCHED:hvac_in_hours" in reason_codes
        assert "ROUTING_SERVICE_TYPE:hvac_repair" in reason_codes
        assert "ROUTING_TIME_WINDOW:IN_HOURS" in reason_codes
    
    def test_hvac_after_hours_match(self) -> None:
        """Test HVAC service type match after hours."""
        utc_timestamp = datetime.datetime(2024, 1, 8, 1, 0, 0, tzinfo=datetime.timezone.utc)
        local_time = datetime.datetime(2024, 1, 7, 20, 0, 0, tzinfo=datetime.timezone.utc)
        
        profile, reason_codes = self.service.select_routing_profile(
            service_type=ServiceType.HVAC_INSTALL,
            time_window=TimeWindow.AFTER_HOURS,
            routing_json=self.routing_config,
            utc_timestamp=utc_timestamp,
            timezone="America/New_York",
            local_time=local_time,
        )
        
        assert profile is not None
        assert profile["name"] == "hvac_after_hours"
        assert "ROUTING_PROFILE_MATCHED:hvac_after_hours" in reason_codes
        assert "ROUTING_SERVICE_TYPE:hvac_install" in reason_codes
        assert "ROUTING_TIME_WINDOW:AFTER_HOURS" in reason_codes
    
    def test_default_in_hours_match(self) -> None:
        """Test default profile match during business hours."""
        utc_timestamp = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        local_time = datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        profile, reason_codes = self.service.select_routing_profile(
            service_type=ServiceType.PLUMBING,  # Not in HVAC list
            time_window=TimeWindow.IN_HOURS,
            routing_json=self.routing_config,
            utc_timestamp=utc_timestamp,
            timezone="America/New_York",
            local_time=local_time,
        )
        
        assert profile is not None
        assert profile["name"] == "default_in_hours"
        assert "ROUTING_PROFILE_MATCHED:default_in_hours" in reason_codes
        assert "ROUTING_SERVICE_TYPE:plumbing" in reason_codes
        assert "ROUTING_TIME_WINDOW:IN_HOURS" in reason_codes
    
    def test_default_after_hours_match(self) -> None:
        """Test default profile match after hours."""
        utc_timestamp = datetime.datetime(2024, 1, 8, 1, 0, 0, tzinfo=datetime.timezone.utc)
        local_time = datetime.datetime(2024, 1, 7, 20, 0, 0, tzinfo=datetime.timezone.utc)
        
        profile, reason_codes = self.service.select_routing_profile(
            service_type=ServiceType.PRESSURE_WASH,  # Not in HVAC list
            time_window=TimeWindow.AFTER_HOURS,
            routing_json=self.routing_config,
            utc_timestamp=utc_timestamp,
            timezone="America/New_York",
            local_time=local_time,
        )
        
        assert profile is not None
        assert profile["name"] == "default_after_hours"
        assert "ROUTING_PROFILE_MATCHED:default_after_hours" in reason_codes
        assert "ROUTING_SERVICE_TYPE:pressure_wash" in reason_codes
        assert "ROUTING_TIME_WINDOW:AFTER_HOURS" in reason_codes
    
    def test_no_profile_match(self) -> None:
        """Test when no profile matches."""
        routing_config_no_match = {
            "profiles": [
                {
                    "name": "hvac_only",
                    "match": {
                        "service_type_in": ["hvac_repair"],
                        "time_window": "IN_HOURS"
                    }
                }
            ]
        }
        
        utc_timestamp = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        local_time = datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        profile, reason_codes = self.service.select_routing_profile(
            service_type=ServiceType.PLUMBING,  # Not in HVAC list
            time_window=TimeWindow.IN_HOURS,
            routing_json=routing_config_no_match,
            utc_timestamp=utc_timestamp,
            timezone="America/New_York",
            local_time=local_time,
        )
        
        assert profile is None
        assert "ROUTING_NO_PROFILE_MATCH" in reason_codes
    
    def test_first_match_wins(self) -> None:
        """Test that the first matching profile wins."""
        routing_config_multiple = {
            "profiles": [
                {
                    "name": "first_match",
                    "match": {
                        "time_window": "IN_HOURS"
                    }
                },
                {
                    "name": "second_match",
                    "match": {
                        "time_window": "IN_HOURS"
                    }
                }
            ]
        }
        
        utc_timestamp = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        local_time = datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        profile, reason_codes = self.service.select_routing_profile(
            service_type=ServiceType.PLUMBING,
            time_window=TimeWindow.IN_HOURS,
            routing_json=routing_config_multiple,
            utc_timestamp=utc_timestamp,
            timezone="America/New_York",
            local_time=local_time,
        )
        
        assert profile is not None
        assert profile["name"] == "first_match"
        assert "ROUTING_PROFILE_MATCHED:first_match" in reason_codes
    
    def test_extract_routing_config(self) -> None:
        """Test extracting routing configuration from profile."""
        profile = self.routing_config["profiles"][0]  # hvac_in_hours
        
        config = self.service.extract_routing_config(profile, self.base_config)
        
        assert config["channels"] == ["WEBHOOK", "SMS"]
        assert config["webhook_url"] == "https://hvac.example.com/webhook"
        assert config["sms_to_numbers"] == ["+15550000001"]
        assert config["email_to_addresses"] == []
        assert config["followup"]["send_confirmation_to_caller"] == True
        assert config["followup"]["send_reminder_to_caller"] == False
        assert config["followup"]["reminder_delay_minutes"] == 30  # Default from base config
    
    def test_extract_routing_config_fallback(self) -> None:
        """Test fallback to base config when no profile."""
        config = self.service.extract_routing_config(None, self.base_config)
        
        assert config["channels"] == ["WEBHOOK"]
        assert config["webhook_url"] == "https://base.example.com/webhook"
        assert config["sms_to_numbers"] == []
        assert config["email_to_addresses"] == []
        assert config["followup"] == {}
        assert config["escalation"]["urgent_escalation"] == False
    
    def test_validate_routing_config_valid(self) -> None:
        """Test validation of valid routing configuration."""
        is_valid, errors = self.service.validate_routing_config(self.routing_config)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_routing_config_invalid(self) -> None:
        """Test validation of invalid routing configuration."""
        invalid_config = {
            "timezone": "Invalid/Timezone",
            "business_hours": {
                "mon": [{"start": "25:00", "end": "26:00"}]  # Invalid time
            },
            "profiles": [
                {
                    "name": "test",
                    "match": {
                        "service_type_in": ["invalid_service"],  # Invalid service type
                        "time_window": "INVALID_WINDOW"  # Invalid time window
                    },
                    "delivery": {
                        "channels": ["INVALID_CHANNEL"]  # Invalid channel
                    },
                    "followup": {
                        "reminder_delay_minutes": 5000  # Invalid delay
                    }
                }
            ]
        }
        
        is_valid, errors = self.service.validate_routing_config(invalid_config)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("Invalid timezone" in error for error in errors)
        assert any("Invalid time format" in error for error in errors)
        assert any("Invalid service type" in error for error in errors)
        assert any("Invalid time window" in error for error in errors)
        assert any("Invalid channel" in error for error in errors)
        assert any("reminder_delay_minutes must be between" in error for error in errors)
    
    def test_profile_with_no_match_config(self) -> None:
        """Test profile with no match configuration (should match everything)."""
        routing_config_no_match = {
            "profiles": [
                {
                    "name": "catch_all",
                    "match": {},  # No filters, should match everything
                    "delivery": {
                        "channels": ["SMS"],
                        "sms_to_numbers": ["+15550000099"]
                    }
                }
            ]
        }
        
        utc_timestamp = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        local_time = datetime.datetime(2024, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        profile, reason_codes = self.service.select_routing_profile(
            service_type=ServiceType.PLUMBING,
            time_window=TimeWindow.IN_HOURS,
            routing_json=routing_config_no_match,
            utc_timestamp=utc_timestamp,
            timezone="America/New_York",
            local_time=local_time,
        )
        
        assert profile is not None
        assert profile["name"] == "catch_all"
        assert "ROUTING_PROFILE_MATCHED:catch_all" in reason_codes
