"""Service type normalization service."""

import re
from typing import Tuple

import structlog

from app.core.enums import ServiceType

logger = structlog.get_logger()


class ServiceNormalizationService:
    """Service for normalizing free-text service requests to standardized types."""
    
    # Keyword mapping for deterministic service type detection
    KEYWORD_MAPPINGS = {
        ServiceType.HVAC_REPAIR: [
            "ac", "air conditioner", "air conditioning", "hvac", "furnace", "heat",
            "heating", "cooling", "thermostat", "ac unit", "ac repair", "hvac repair",
            "air duct", "ventilation", "heat pump", "central air", "air handler"
        ],
        ServiceType.HVAC_INSTALL: [
            "ac install", "hvac install", "furnace install", "air conditioner install",
            "heating install", "cooling install", "new ac", "new furnace", "new hvac",
            "ac replacement", "furnace replacement", "hvac replacement"
        ],
        ServiceType.PLUMBING: [
            "pipe", "leak", "drain", "toilet", "sewer", "plumbing", "water heater",
            "faucet", "sink", "garbage disposal", "water line", "septic", "clog",
            "backup", "burst pipe", "pipe repair", "drain cleaning", "toilet repair"
        ],
        ServiceType.PRESSURE_WASH: [
            "pressure", "wash", "driveway", "softwash", "exterior", "power wash",
            "pressure washing", "power washing", "house washing", "deck cleaning",
            "siding cleaning", "roof cleaning", "concrete cleaning", "soft wash"
        ],
        ServiceType.RESTORATION: [
            "mold", "water damage", "fire damage", "restoration", "flood", "smoke damage",
            "storm damage", "emergency restoration", "water restoration", "fire restoration",
            "mold remediation", "water removal", "structural drying"
        ]
    }
    
    def __init__(self) -> None:
        # Pre-compile regex patterns for performance
        self._compiled_patterns = {}
        for service_type, keywords in self.KEYWORD_MAPPINGS.items():
            # Create regex pattern that matches any of the keywords as whole words
            pattern = r'\b(?:' + '|'.join(re.escape(keyword) for keyword in keywords) + r')\b'
            self._compiled_patterns[service_type] = re.compile(pattern, re.IGNORECASE)
    
    def normalize_service_type(self, service_requested: str) -> Tuple[ServiceType, list[str]]:
        """
        Normalize free-text service request to standardized service type.
        
        Args:
            service_requested: Free-text service description from caller
            
        Returns:
            Tuple of (normalized_service_type, reason_codes)
        """
        if not service_requested:
            return ServiceType.UNKNOWN, ["SERVICE_TYPE_EMPTY"]
        
        # Normalize input: lowercase and strip
        normalized_input = service_requested.lower().strip()
        reason_codes = []
        
        # Check each service type in priority order
        for service_type, pattern in self._compiled_patterns.items():
            if pattern.search(normalized_input):
                # Find which keyword matched for logging
                keywords = self.KEYWORD_MAPPINGS[service_type]
                matched_keyword = None
                for keyword in keywords:
                    if re.search(r'\b' + re.escape(keyword) + r'\b', normalized_input, re.IGNORECASE):
                        matched_keyword = keyword
                        break
                
                reason_codes.append(f"SERVICE_TYPE_KEYWORD:{matched_keyword or 'unknown'}")
                logger.info(
                    "Service type normalized",
                    original=service_requested,
                    normalized=service_type.value,
                    matched_keyword=matched_keyword,
                    reason_codes=reason_codes,
                )
                return service_type, reason_codes
        
        # No match found
        reason_codes.append("SERVICE_TYPE_NO_MATCH")
        logger.info(
            "Service type normalized to unknown",
            original=service_requested,
            normalized=ServiceType.UNKNOWN.value,
            reason_codes=reason_codes,
        )
        return ServiceType.UNKNOWN, reason_codes
    
    def get_all_keywords(self) -> dict[str, list[str]]:
        """
        Get all keyword mappings for reference.
        
        Returns:
            Dictionary mapping service types to their keywords
        """
        return {service_type.value: keywords for service_type, keywords in self.KEYWORD_MAPPINGS.items()}
