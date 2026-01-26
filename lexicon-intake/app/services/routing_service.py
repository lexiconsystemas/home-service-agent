"""Routing profile selection service."""

import datetime
from typing import Dict, List, Optional, Tuple, Any

import structlog

from app.core.enums import ServiceType, TimeWindow, DeliveryChannel
from app.services.business_hours import BusinessHoursService

logger = structlog.get_logger()


class RoutingService:
    """Service for selecting routing profiles based on service type and business hours."""
    
    def __init__(self) -> None:
        self.business_hours_service = BusinessHoursService()
    
    def select_routing_profile(
        self,
        service_type: ServiceType,
        time_window: TimeWindow,
        routing_json: Dict[str, Any],
        utc_timestamp: datetime.datetime,
        timezone: str,
        local_time: datetime.datetime,
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Select the first matching routing profile based on service type and time window.
        
        Args:
            service_type: Normalized service type
            time_window: IN_HOURS or AFTER_HOURS
            routing_json: Client routing configuration
            utc_timestamp: Original UTC timestamp
            timezone: Timezone used for conversion
            local_time: Local time after conversion
            
        Returns:
            Tuple of (selected_profile, reason_codes)
        """
        reason_codes = []
        
        if not routing_json:
            reason_codes.append("ROUTING_NO_CONFIG")
            logger.info("No routing configuration found", reason_codes=reason_codes)
            return None, reason_codes
        
        profiles = routing_json.get("profiles", [])
        if not profiles:
            reason_codes.append("ROUTING_NO_PROFILES")
            logger.info("No routing profiles found", reason_codes=reason_codes)
            return None, reason_codes
        
        # Check each profile in order (first match wins)
        for i, profile in enumerate(profiles):
            if self._profile_matches(profile, service_type, time_window):
                profile_name = profile.get("name", f"profile_{i}")
                reason_codes.append(f"ROUTING_PROFILE_MATCHED:{profile_name}")
                reason_codes.append(f"ROUTING_SERVICE_TYPE:{service_type.value}")
                reason_codes.append(f"ROUTING_TIME_WINDOW:{time_window.value}")
                
                logger.info(
                    "Routing profile selected",
                    profile_name=profile_name,
                    service_type=service_type.value,
                    time_window=time_window.value,
                    profile_index=i,
                    reason_codes=reason_codes,
                )
                
                return profile, reason_codes
        
        # No profile matched
        reason_codes.append("ROUTING_NO_PROFILE_MATCH")
        logger.info(
            "No routing profile matched",
            service_type=service_type.value,
            time_window=time_window.value,
            profile_count=len(profiles),
            reason_codes=reason_codes,
        )
        
        return None, reason_codes
    
    def _profile_matches(
        self,
        profile: Dict[str, Any],
        service_type: ServiceType,
        time_window: TimeWindow,
    ) -> bool:
        """
        Check if a profile matches the given service type and time window.
        
        Args:
            profile: Routing profile configuration
            service_type: Normalized service type
            time_window: IN_HOURS or AFTER_HOURS
            
        Returns:
            True if profile matches, False otherwise
        """
        match_config = profile.get("match", {})
        
        # Check service type filter
        service_type_filter = match_config.get("service_type_in", [])
        if service_type_filter:
            if service_type.value not in service_type_filter:
                return False
        
        # Check time window filter
        time_window_filter = match_config.get("time_window")
        if time_window_filter:
            if time_window_filter != time_window.value:
                return False
        
        # All filters passed
        return True
    
    def extract_routing_config(
        self,
        profile: Optional[Dict[str, Any]],
        base_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract routing configuration from selected profile, falling back to base config.
        
        Args:
            profile: Selected routing profile (may be None)
            base_config: Base client configuration
            
        Returns:
            Merged routing configuration
        """
        if not profile:
            # Use base configuration
            return {
                "channels": base_config.get("delivery_channels", ["WEBHOOK"]),
                "webhook_url": base_config.get("webhook_url"),
                "sms_to_numbers": base_config.get("sms_to_numbers", []),
                "email_to_addresses": base_config.get("email_to_addresses", []),
                "followup": base_config.get("followup_flags", {}),
                "escalation": {
                    "urgent_escalation": base_config.get("followup_flags", {}).get("urgent_escalation", False)
                },
            }
        
        # Extract from profile
        profile_delivery = profile.get("delivery", {})
        profile_followup = profile.get("followup", {})
        profile_escalation = profile.get("escalation", {})
        
        # Merge with base config (profile takes precedence)
        config = {
            "channels": profile_delivery.get("channels", base_config.get("delivery_channels", ["WEBHOOK"])),
            "webhook_url": profile_delivery.get("webhook_url", base_config.get("webhook_url")),
            "sms_to_numbers": profile_delivery.get("sms_to_numbers", base_config.get("sms_to_numbers", [])),
            "email_to_addresses": profile_delivery.get("email_to_addresses", base_config.get("email_to_addresses", [])),
            "followup": {
                "send_confirmation_to_caller": profile_followup.get(
                    "send_confirmation_to_caller",
                    base_config.get("followup_flags", {}).get("send_confirmation_to_caller", False)
                ),
                "send_reminder_to_caller": profile_followup.get(
                    "send_reminder_to_caller",
                    base_config.get("followup_flags", {}).get("send_reminder_to_caller", False)
                ),
                "reminder_delay_minutes": profile_followup.get(
                    "reminder_delay_minutes",
                    base_config.get("followup_flags", {}).get("reminder_delay_minutes", 30)
                ),
            },
            "escalation": {
                "urgent_escalation": profile_escalation.get(
                    "urgent_escalation",
                    base_config.get("followup_flags", {}).get("urgent_escalation", False)
                ),
                "urgent_override_channels": profile_escalation.get("urgent_override_channels", []),
                "urgent_override_recipients": profile_escalation.get("urgent_override_recipients", []),
            },
        }
        
        return config
    
    def validate_routing_config(self, routing_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate routing configuration.
        
        Args:
            routing_json: Routing configuration to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not isinstance(routing_json, dict):
            errors.append("Routing configuration must be a dictionary")
            return False, errors
        
        # Validate timezone
        timezone = routing_json.get("timezone")
        if timezone and not self.business_hours_service.validate_timezone(timezone):
            errors.append(f"Invalid timezone: {timezone}")
        
        # Validate business hours
        business_hours = routing_json.get("business_hours", {})
        if business_hours:
            is_valid, business_errors = self.business_hours_service.validate_business_hours_config(business_hours)
            if not is_valid:
                errors.extend([f"Business hours error: {error}" for error in business_errors])
        
        # Validate profiles
        profiles = routing_json.get("profiles", [])
        if not isinstance(profiles, list):
            errors.append("Profiles must be a list")
        else:
            for i, profile in enumerate(profiles):
                profile_errors = self._validate_profile(profile, i)
                errors.extend(profile_errors)
        
        return len(errors) == 0, errors
    
    def _validate_profile(self, profile: Dict[str, Any], index: int) -> List[str]:
        """Validate a single routing profile."""
        errors = []
        profile_name = profile.get("name", f"profile_{index}")
        
        if not isinstance(profile, dict):
            errors.append(f"Profile {profile_name} must be a dictionary")
            return errors
        
        # Validate match configuration
        match_config = profile.get("match", {})
        if not isinstance(match_config, dict):
            errors.append(f"Profile {profile_name} match configuration must be a dictionary")
        else:
            # Check service_type_in if present
            service_type_filter = match_config.get("service_type_in")
            if service_type_filter is not None:
                if not isinstance(service_type_filter, list):
                    errors.append(f"Profile {profile_name} service_type_in must be a list")
                else:
                    valid_service_types = [st.value for st in ServiceType]
                    for st in service_type_filter:
                        if st not in valid_service_types:
                            errors.append(f"Profile {profile_name} has invalid service type: {st}")
            
            # Check time_window if present
            time_window_filter = match_config.get("time_window")
            if time_window_filter is not None:
                valid_time_windows = [tw.value for tw in TimeWindow]
                if time_window_filter not in valid_time_windows:
                    errors.append(f"Profile {profile_name} has invalid time window: {time_window_filter}")
        
        # Validate delivery configuration
        delivery_config = profile.get("delivery", {})
        if not isinstance(delivery_config, dict):
            errors.append(f"Profile {profile_name} delivery configuration must be a dictionary")
        else:
            # Validate channels
            channels = delivery_config.get("channels", [])
            if not isinstance(channels, list):
                errors.append(f"Profile {profile_name} channels must be a list")
            else:
                valid_channels = [dc.value for dc in DeliveryChannel]
                for channel in channels:
                    if channel not in valid_channels:
                        errors.append(f"Profile {profile_name} has invalid channel: {channel}")
        
        # Validate followup configuration
        followup_config = profile.get("followup", {})
        if not isinstance(followup_config, dict):
            errors.append(f"Profile {profile_name} followup configuration must be a dictionary")
        else:
            # Validate reminder_delay_minutes
            delay = followup_config.get("reminder_delay_minutes")
            if delay is not None and (not isinstance(delay, int) or delay < 5 or delay > 1440):
                errors.append(f"Profile {profile_name} reminder_delay_minutes must be between 5 and 1440")
        
        # Validate escalation configuration
        escalation_config = profile.get("escalation", {})
        if not isinstance(escalation_config, dict):
            errors.append(f"Profile {profile_name} escalation configuration must be a dictionary")
        
        return errors
