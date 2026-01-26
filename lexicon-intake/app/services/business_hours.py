"""Business hours logic with timezone support."""

import datetime
from typing import Tuple, Optional
from zoneinfo import ZoneInfo

import structlog

from app.core.enums import TimeWindow

logger = structlog.get_logger()


class BusinessHoursService:
    """Service for determining business hours based on timezone and schedule."""
    
    # Day of week mapping
    DAY_MAPPING = {
        "mon": 0,  # Monday
        "tue": 1,  # Tuesday
        "wed": 2,  # Wednesday
        "thu": 3,  # Thursday
        "fri": 4,  # Friday
        "sat": 5,  # Saturday
        "sun": 6,  # Sunday
    }
    
    def __init__(self) -> None:
        pass
    
    def determine_time_window(
        self,
        utc_timestamp: datetime.datetime,
        timezone: str,
        business_hours: dict,
    ) -> Tuple[TimeWindow, datetime.datetime, list[str]]:
        """
        Determine if a given UTC timestamp falls within business hours for a timezone.
        
        Args:
            utc_timestamp: UTC timestamp to check
            timezone: IANA timezone string (e.g., "America/New_York")
            business_hours: Business hours configuration
            
        Returns:
            Tuple of (time_window, local_time, reason_codes)
        """
        reason_codes = []
        
        try:
            # Convert UTC timestamp to local timezone
            zone = ZoneInfo(timezone)
            local_time = utc_timestamp.astimezone(zone)
            
            logger.info(
                "Time zone conversion",
                utc_time=utc_timestamp.isoformat(),
                timezone=timezone,
                local_time=local_time.isoformat(),
            )
            
            # Get day of week (0=Monday, 6=Sunday)
            day_of_week = local_time.weekday()
            current_time = local_time.time()
            
            # Find business hours for current day
            day_name = self._get_day_name(day_of_week)
            day_schedule = business_hours.get(day_name, [])
            
            if not day_schedule:
                # No schedule for this day = after hours
                reason_codes.append(f"BUSINESS_HOURS_NO_SCHEDULE:{day_name}")
                logger.info(
                    "No business hours schedule for day",
                    day=day_name,
                    time_window=TimeWindow.AFTER_HOURS.value,
                )
                return TimeWindow.AFTER_HOURS, local_time, reason_codes
            
            # Check if current time falls within any scheduled window
            for schedule in day_schedule:
                start_time = self._parse_time(schedule["start"])
                end_time = self._parse_time(schedule["end"])
                
                if start_time <= current_time <= end_time:
                    reason_codes.append(f"BUSINESS_HOURS_IN_SCHEDULE:{day_name}:{schedule['start']}-{schedule['end']}")
                    logger.info(
                        "Within business hours",
                        day=day_name,
                        current_time=current_time.isoformat(),
                        schedule=f"{schedule['start']}-{schedule['end']}",
                        time_window=TimeWindow.IN_HOURS.value,
                    )
                    return TimeWindow.IN_HOURS, local_time, reason_codes
            
            # Not within any scheduled window
            reason_codes.append(f"BUSINESS_HOURS_OUTSIDE_SCHEDULE:{day_name}")
            logger.info(
                "Outside business hours",
                day=day_name,
                current_time=current_time.isoformat(),
                schedules=day_schedule,
                time_window=TimeWindow.AFTER_HOURS.value,
            )
            return TimeWindow.AFTER_HOURS, local_time, reason_codes
            
        except Exception as e:
            # Error in timezone or schedule processing = assume after hours for safety
            reason_codes.append(f"BUSINESS_HOURS_ERROR:{str(e)}")
            logger.error(
                "Error determining business hours",
                timezone=timezone,
                error=str(e),
                time_window=TimeWindow.AFTER_HOURS.value,
                exc_info=True,
            )
            # Return UTC time as fallback
            return TimeWindow.AFTER_HOURS, utc_timestamp, reason_codes
    
    def _get_day_name(self, day_of_week: int) -> str:
        """Convert day of week number to day name used in config."""
        reverse_mapping = {v: k for k, v in self.DAY_MAPPING.items()}
        return reverse_mapping.get(day_of_week, "unknown")
    
    def _parse_time(self, time_str: str) -> datetime.time:
        """Parse time string in HH:MM format to time object."""
        try:
            hour, minute = map(int, time_str.split(":"))
            return datetime.time(hour=hour, minute=minute)
        except Exception as e:
            logger.error("Invalid time format", time_str=time_str, error=str(e))
            raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")
    
    def validate_business_hours_config(self, business_hours: dict) -> Tuple[bool, list[str]]:
        """
        Validate business hours configuration.
        
        Args:
            business_hours: Business hours configuration to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not isinstance(business_hours, dict):
            errors.append("Business hours must be a dictionary")
            return False, errors
        
        # Check each day
        for day_name, day_schedule in business_hours.items():
            if day_name not in self.DAY_MAPPING:
                errors.append(f"Invalid day name: {day_name}")
                continue
            
            if not isinstance(day_schedule, list):
                errors.append(f"Schedule for {day_name} must be a list")
                continue
            
            for schedule in day_schedule:
                if not isinstance(schedule, dict):
                    errors.append(f"Schedule entry for {day_name} must be a dictionary")
                    continue
                
                if "start" not in schedule or "end" not in schedule:
                    errors.append(f"Schedule for {day_name} missing start or end time")
                    continue
                
                # Validate time format
                try:
                    self._parse_time(schedule["start"])
                    self._parse_time(schedule["end"])
                except ValueError as e:
                    errors.append(f"Invalid time format in {day_name} schedule: {str(e)}")
        
        return len(errors) == 0, errors
    
    def validate_timezone(self, timezone: str) -> bool:
        """
        Validate timezone string.
        
        Args:
            timezone: IANA timezone string
            
        Returns:
            True if valid, False otherwise
        """
        try:
            ZoneInfo(timezone)
            return True
        except Exception:
            return False
