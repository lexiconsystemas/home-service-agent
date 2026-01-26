"""Scheduling service for time window offerings and selection."""

import datetime
from typing import Any

from zoneinfo import ZoneInfo

import structlog

from app.core.enums import CallClassification
from app.db.repos.lead_repo import LeadRepository

logger = structlog.get_logger()


class SchedulingService:
    """Service for handling scheduling-lite functionality."""
    
    def __init__(self, lead_repo: LeadRepository) -> None:
        self.lead_repo = lead_repo
    
    def generate_scheduling_windows(
        self,
        base_time: datetime.datetime,
        timezone_str: str,
        windows_config: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Generate scheduling windows based on configuration.
        
        Args:
            base_time: Base time for window calculations (usually current time)
            timezone_str: Timezone string (e.g., "America/New_York")
            windows_config: List of window configurations from routing profile
            
        Returns:
            List of available windows with calculated times
        """
        try:
            tz = ZoneInfo(timezone_str)
            base_local = base_time.astimezone(tz)
            
            available_windows = []
            
            for window_config in windows_config:
                label = window_config["label"]
                start_offset = window_config["start_offset_min"]
                end_offset = window_config["end_offset_min"]
                
                # Calculate window times
                start_time = base_local + datetime.timedelta(minutes=start_offset)
                end_time = base_local + datetime.timedelta(minutes=end_offset)
                
                available_windows.append({
                    "label": label,
                    "start_time": start_time,
                    "end_time": end_time,
                    "start_offset_min": start_offset,
                    "end_offset_min": end_offset,
                })
            
            return available_windows
            
        except Exception as e:
            logger.error(
                "Failed to generate scheduling windows",
                timezone=timezone_str,
                windows_config=windows_config,
                error=str(e),
                exc_info=True,
            )
            return []
    
    def validate_scheduling_config(
        self,
        scheduling_config: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Validate scheduling configuration.
        
        Args:
            scheduling_config: Scheduling configuration from routing profile
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not scheduling_config.get("enabled", False):
            return True, errors
        
        windows = scheduling_config.get("windows", [])
        if not windows:
            errors.append("No windows configured for scheduling")
            return False, errors
        
        for i, window in enumerate(windows):
            if "label" not in window:
                errors.append(f"Window {i}: missing label")
            
            if "start_offset_min" not in window:
                errors.append(f"Window {i}: missing start_offset_min")
            
            if "end_offset_min" not in window:
                errors.append(f"Window {i}: missing end_offset_min")
            
            if "start_offset_min" in window and "end_offset_min" in window:
                start = window["start_offset_min"]
                end = window["end_offset_min"]
                
                if not isinstance(start, int) or start < 0:
                    errors.append(f"Window {i}: start_offset_min must be non-negative integer")
                
                if not isinstance(end, int) or end < 0:
                    errors.append(f"Window {i}: end_offset_min must be non-negative integer")
                
                if start >= end:
                    errors.append(f"Window {i}: start_offset_min must be less than end_offset_min")
        
        return len(errors) == 0, errors
    
    def select_window_by_response(
        self,
        response: str,
        available_windows: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Select window based on SMS response.
        
        Args:
            response: SMS response (e.g., "1", "2", "3")
            available_windows: List of available windows
            
        Returns:
            Selected window or None if invalid response
        """
        try:
            # Clean response - extract first digit
            response = response.strip()
            if not response or not response[0].isdigit():
                return None
            
            choice = int(response[0]) - 1  # Convert to 0-based index
            
            if 0 <= choice < len(available_windows):
                return available_windows[choice]
            
            return None
            
        except (ValueError, IndexError):
            return None
    
    def generate_scheduling_sms(
        self,
        available_windows: list[dict[str, Any]],
    ) -> str:
        """
        Generate SMS message for scheduling window selection.
        
        Args:
            available_windows: List of available windows
            
        Returns:
            SMS message content
        """
        if not available_windows:
            return "We can help. Please call us to schedule your service."
        
        lines = ["We can help. Reply with your preferred time:"]
        
        for i, window in enumerate(available_windows, 1):
            lines.append(f"{i}. {window['label']}")
        
        lines.append("Reply with the number of your choice.")
        
        return "\n".join(lines)
    
    async def process_scheduling_response(
        self,
        lead_id: str,
        response: str,
        available_windows: list[dict[str, Any]],
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        """
        Process scheduling response and update lead record.
        
        Args:
            lead_id: Lead ID
            response: SMS response
            available_windows: Available windows for selection
            
        Returns:
            Tuple of (success, error_message, selected_window)
        """
        selected_window = self.select_window_by_response(response, available_windows)
        
        if not selected_window:
            return False, "Invalid response. Please reply with a number from the list.", None
        
        try:
            # Update lead record with selected window
            await self.lead_repo.update_scheduling_selection(
                lead_id=lead_id,
                window_label=selected_window["label"],
                start_estimate=selected_window["start_time"],
                end_estimate=selected_window["end_time"],
            )
            
            logger.info(
                "Scheduling selection processed",
                lead_id=lead_id,
                selected_window=selected_window["label"],
                start_time=selected_window["start_time"].isoformat(),
                end_time=selected_window["end_time"].isoformat(),
            )
            
            return True, None, selected_window
            
        except Exception as e:
            logger.error(
                "Failed to process scheduling selection",
                lead_id=lead_id,
                selected_window=selected_window,
                error=str(e),
                exc_info=True,
            )
            return False, "System error processing your selection. Please try again.", None
    
    def should_offer_scheduling(
        self,
        classification: CallClassification,
        routing_config: dict[str, Any],
    ) -> bool:
        """
        Determine if scheduling should be offered.
        
        Args:
            classification: Lead classification
            routing_config: Routing configuration from selected profile
            
        Returns:
            True if scheduling should be offered
        """
        # Only offer scheduling for qualified leads
        if classification != CallClassification.QUALIFIED:
            return False
        
        # Check if scheduling is enabled in routing config
        scheduling_config = routing_config.get("scheduling", {})
        return scheduling_config.get("enabled", False)
    
    def generate_confirmation_message(
        self,
        selected_window: dict[str, Any],
    ) -> str:
        """
        Generate confirmation message after window selection.
        
        Args:
            selected_window: Selected scheduling window
            
        Returns:
            Confirmation message
        """
        return f"Thank you! We've scheduled your service for {selected_window['label']}. We'll send you a reminder before your appointment."
