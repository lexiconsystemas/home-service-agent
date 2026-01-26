"""Classification service for categorizing calls."""

from dataclasses import dataclass
from typing import Any

import structlog

from app.core.enums import CallClassification
from app.domain.models.call_event import CallEvent
from app.services.qualification_service import QualificationResult

logger = structlog.get_logger()


@dataclass
class ClassificationResult:
    """Result of call classification."""
    
    classification: CallClassification
    reason_codes: list[str]


class ClassificationService:
    """Service for classifying inbound calls."""
    
    async def classify_call(
        self,
        call_event: CallEvent,
        qualification_result: QualificationResult,
    ) -> ClassificationResult:
        """
        Classify a call event based on validation and qualification.
        
        Args:
            call_event: Call event data
            qualification_result: Result from qualification service
            
        Returns:
            Classification result with classification and reason codes
        """
        logger.info(
            "Classifying call",
            call_id=call_event.call_id,
            qualification_outcome=qualification_result.outcome,
        )
        
        # Check for invalid phone numbers
        if not self._is_valid_phone(call_event.from_number):
            logger.warning("Invalid phone number detected", call_id=call_event.call_id, from_number=call_event.from_number)
            return ClassificationResult(
                classification=CallClassification.DROPPED,
                reason_codes=["invalid_phone_number"],
            )
        
        # Check for missing required fields
        missing_fields = self._check_required_fields(call_event)
        if missing_fields:
            logger.warning("Missing required fields", call_id=call_event.call_id, missing_fields=missing_fields)
            return ClassificationResult(
                classification=CallClassification.DROPPED,
                reason_codes=[f"missing_{field}" for field in missing_fields],
            )
        
        # Check for spam patterns
        spam_reasons = self._check_spam_patterns(call_event)
        if spam_reasons:
            logger.warning("Spam patterns detected", call_id=call_event.call_id, spam_reasons=spam_reasons)
            return ClassificationResult(
                classification=CallClassification.SPAM,
                reason_codes=spam_reasons,
            )
        
        # Classification based on qualification
        if qualification_result.outcome == "qualified":
            classification = CallClassification.QUALIFIED
            reason_codes = []
        else:
            classification = CallClassification.UNQUALIFIED
            reason_codes = qualification_result.reason_codes
        
        logger.info(
            "Call classified",
            call_id=call_event.call_id,
            classification=classification.value,
            reason_codes=reason_codes,
        )
        
        return ClassificationResult(
            classification=classification,
            reason_codes=reason_codes,
        )
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Check if phone number is valid."""
        if not phone:
            return False
        
        # Remove all non-digit characters
        digits = "".join(filter(str.isdigit, phone))
        
        # Check if we have at least 10 digits (US number)
        return len(digits) >= 10
    
    def _check_required_fields(self, call_event: CallEvent) -> list[str]:
        """Check for missing required fields."""
        missing = []
        
        if not call_event.service_requested:
            missing.append("service_requested")
        
        if not call_event.location_zip:
            missing.append("location_zip")
        
        return missing
    
    def _check_spam_patterns(self, call_event: CallEvent) -> list[str]:
        """Check for spam patterns."""
        spam_reasons = []
        
        # Check for obviously fake phone numbers
        if call_event.from_number:
            digits = "".join(filter(str.isdigit, call_event.from_number))
            if len(digits) < 10:
                spam_reasons.append("phone_too_short")
            elif digits.startswith("555"):
                spam_reasons.append("fake_phone_pattern")
        
        # Check for suspicious caller names
        if call_event.caller_name:
            caller_name_lower = call_event.caller_name.lower()
            suspicious_names = ["test", "spam", "fake", "unknown", "anonymous"]
            if any(sus in caller_name_lower for sus in suspicious_names):
                spam_reasons.append("suspicious_caller_name")
        
        return spam_reasons
