"""Tests for business hours logic."""

import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.business_hours import BusinessHoursService
from app.core.enums import TimeWindow


class TestBusinessHours:
    """Test cases for business hours logic."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = BusinessHoursService()
        
        # Sample business hours configuration
        self.business_hours = {
            "mon": [{"start": "08:00", "end": "18:00"}],
            "tue": [{"start": "08:00", "end": "18:00"}],
            "wed": [{"start": "08:00", "end": "18:00"}],
            "thu": [{"start": "08:00", "end": "18:00"}],
            "fri": [{"start": "08:00", "end": "18:00"}],
            "sat": [{"start": "10:00", "end": "14:00"}],
            "sun": []
        }
    
    def test_in_hours_weekday(self) -> None:
        """Test in-hours during weekday."""
        # Monday 10:00 AM EST
        utc_time = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.IN_HOURS
        assert local_time.hour == 10  # 10:00 AM EST
        assert "BUSINESS_HOURS_IN_SCHEDULE:mon:08:00-18:00" in reason_codes
    
    def test_after_hours_weekday(self) -> None:
        """Test after-hours during weekday."""
        # Monday 8:00 PM EST
        utc_time = datetime.datetime(2024, 1, 9, 1, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.AFTER_HOURS
        assert local_time.hour == 20  # 8:00 PM EST
        assert "BUSINESS_HOURS_OUTSIDE_SCHEDULE:mon" in reason_codes
    
    def test_in_hours_saturday(self) -> None:
        """Test in-hours on Saturday."""
        # Saturday 11:00 AM EST
        utc_time = datetime.datetime(2024, 1, 13, 16, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.IN_HOURS
        assert local_time.hour == 11  # 11:00 AM EST
        assert "BUSINESS_HOURS_IN_SCHEDULE:sat:10:00-14:00" in reason_codes
    
    def test_after_hours_saturday(self) -> None:
        """Test after-hours on Saturday."""
        # Saturday 3:00 PM EST
        utc_time = datetime.datetime(2024, 1, 13, 20, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.AFTER_HOURS
        assert local_time.hour == 15  # 3:00 PM EST
        assert "BUSINESS_HOURS_OUTSIDE_SCHEDULE:sat" in reason_codes
    
    def test_no_schedule_sunday(self) -> None:
        """Test Sunday with no schedule."""
        # Sunday 10:00 AM EST
        utc_time = datetime.datetime(2024, 1, 14, 15, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.AFTER_HOURS
        assert local_time.hour == 10  # 10:00 AM EST
        assert "BUSINESS_HOURS_NO_SCHEDULE:sun" in reason_codes
    
    def test_multiple_time_blocks(self) -> None:
        """Test multiple time blocks in one day."""
        business_hours_multiple = {
            "mon": [
                {"start": "08:00", "end": "12:00"},
                {"start": "13:00", "end": "17:00"}
            ]
        }
        
        # Monday 10:00 AM EST (first block)
        utc_time = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=business_hours_multiple,
        )
        
        assert time_window == TimeWindow.IN_HOURS
        
        # Monday 12:30 PM EST (between blocks)
        utc_time = datetime.datetime(2024, 1, 8, 17, 30, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=business_hours_multiple,
        )
        
        assert time_window == TimeWindow.AFTER_HOURS
        
        # Monday 2:00 PM EST (second block)
        utc_time = datetime.datetime(2024, 1, 8, 19, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=business_hours_multiple,
        )
        
        assert time_window == TimeWindow.IN_HOURS
    
    def test_daylight_savings_time(self) -> None:
        """Test daylight savings time handling."""
        # Test during DST (July)
        utc_time_dst = datetime.datetime(2024, 7, 8, 14, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time_dst,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.IN_HOURS
        assert local_time.hour == 10  # 10:00 AM EDT (UTC-4)
        
        # Test during standard time (January)
        utc_time_std = datetime.datetime(2024, 1, 8, 13, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time_std,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.IN_HOURS
        assert local_time.hour == 8  # 8:00 AM EST (UTC-5)
    
    def test_different_timezones(self) -> None:
        """Test different timezones."""
        utc_time = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Pacific Time
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/Los_Angeles",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.AFTER_HOURS
        assert local_time.hour == 7  # 7:00 AM PST
        
        # Central Time
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/Chicago",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.IN_HOURS
        assert local_time.hour == 9  # 9:00 AM CST
    
    def test_invalid_timezone(self) -> None:
        """Test invalid timezone."""
        utc_time = datetime.datetime(2024, 1, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="Invalid/Timezone",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.AFTER_HOURS
        assert "BUSINESS_HOURS_ERROR:" in reason_codes[0]
    
    def test_validate_business_hours_config(self) -> None:
        """Test business hours configuration validation."""
        # Valid configuration
        is_valid, errors = self.service.validate_business_hours_config(self.business_hours)
        assert is_valid
        assert len(errors) == 0
        
        # Invalid configuration
        invalid_config = {
            "mon": [{"start": "25:00", "end": "26:00"}],  # Invalid time
            "invalid_day": [{"start": "08:00", "end": "18:00"}],  # Invalid day
        }
        
        is_valid, errors = self.service.validate_business_hours_config(invalid_config)
        assert not is_valid
        assert len(errors) > 0
        assert any("Invalid day name" in error for error in errors)
    
    def test_validate_timezone(self) -> None:
        """Test timezone validation."""
        # Valid timezones
        assert self.service.validate_timezone("America/New_York")
        assert self.service.validate_timezone("UTC")
        assert self.service.validate_timezone("Europe/London")
        
        # Invalid timezone
        assert not self.service.validate_timezone("Invalid/Timezone")
        assert not self.service.validate_timezone("")
    
    def test_boundary_times(self) -> None:
        """Test boundary times (exact start and end times)."""
        # Monday 8:00 AM EST (exact start time)
        utc_time = datetime.datetime(2024, 1, 8, 13, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.IN_HOURS
        
        # Monday 6:00 PM EST (exact end time)
        utc_time = datetime.datetime(2024, 1, 8, 23, 0, 0, tzinfo=datetime.timezone.utc)
        
        time_window, local_time, reason_codes = self.service.determine_time_window(
            utc_timestamp=utc_time,
            timezone="America/New_York",
            business_hours=self.business_hours,
        )
        
        assert time_window == TimeWindow.IN_HOURS
