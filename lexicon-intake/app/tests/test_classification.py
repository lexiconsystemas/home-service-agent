"""Tests for classification service."""

import pytest
from datetime import datetime

from app.core.enums import CallClassification
from app.domain.models.call_event import CallEvent
from app.services.classification_service import ClassificationService
from app.services.qualification_service import QualificationResult


class TestClassificationService:
    """Test cases for ClassificationService."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.classification_service = ClassificationService()
    
    async def test_classify_qualified_call(self) -> None:
        """Test classification of a qualified call."""
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="+15551234567",
            to_number="+15550001111",
            timestamp=datetime.now(),
            caller_name="John Doe",
            service_requested="plumbing",
            urgency="medium",
            budget=200,
            location_zip="90210",
        )
        
        qualification_result = QualificationResult(
            outcome="qualified",
            reason_codes=[],
        )
        
        result = await self.classification_service.classify_call(
            call_event=call_event,
            qualification_result=qualification_result,
        )
        
        assert result.classification == CallClassification.QUALIFIED
        assert result.reason_codes == []
    
    async def test_classify_unqualified_call(self) -> None:
        """Test classification of an unqualified call."""
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="+15551234567",
            to_number="+15550001111",
            timestamp=datetime.now(),
            caller_name="John Doe",
            service_requested="plumbing",
            urgency="medium",
            budget=50,  # Too low
            location_zip="90210",
        )
        
        qualification_result = QualificationResult(
            outcome="unqualified",
            reason_codes=["budget_too_low"],
        )
        
        result = await self.classification_service.classify_call(
            call_event=call_event,
            qualification_result=qualification_result,
        )
        
        assert result.classification == CallClassification.UNQUALIFIED
        assert result.reason_codes == ["budget_too_low"]
    
    async def test_classify_invalid_phone(self) -> None:
        """Test classification with invalid phone number."""
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="123",  # Invalid phone
            to_number="+15550001111",
            timestamp=datetime.now(),
            caller_name="John Doe",
            service_requested="plumbing",
            urgency="medium",
            budget=200,
            location_zip="90210",
        )
        
        qualification_result = QualificationResult(
            outcome="qualified",
            reason_codes=[],
        )
        
        result = await self.classification_service.classify_call(
            call_event=call_event,
            qualification_result=qualification_result,
        )
        
        assert result.classification == CallClassification.DROPPED
        assert "invalid_phone_number" in result.reason_codes
    
    async def test_classify_missing_required_fields(self) -> None:
        """Test classification with missing required fields."""
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="+15551234567",
            to_number="+15550001111",
            timestamp=datetime.now(),
            caller_name="John Doe",
            service_requested=None,  # Missing
            urgency="medium",
            budget=200,
            location_zip=None,  # Missing
        )
        
        qualification_result = QualificationResult(
            outcome="qualified",
            reason_codes=[],
        )
        
        result = await self.classification_service.classify_call(
            call_event=call_event,
            qualification_result=qualification_result,
        )
        
        assert result.classification == CallClassification.DROPPED
        assert "missing_service_requested" in result.reason_codes
        assert "missing_location" in result.reason_codes
    
    async def test_classify_spam_patterns(self) -> None:
        """Test classification with spam patterns."""
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="5551234567",  # Fake pattern
            to_number="+15550001111",
            timestamp=datetime.now(),
            caller_name="Test User",  # Suspicious name
            service_requested="plumbing",
            urgency="medium",
            budget=200,
            location_zip="90210",
        )
        
        qualification_result = QualificationResult(
            outcome="qualified",
            reason_codes=[],
        )
        
        result = await self.classification_service.classify_call(
            call_event=call_event,
            qualification_result=qualification_result,
        )
        
        assert result.classification == CallClassification.SPAM
        assert "fake_phone_pattern" in result.reason_codes
        assert "suspicious_caller_name" in result.reason_codes
    
    async def test_classify_phone_too_short(self) -> None:
        """Test classification with phone number too short."""
        call_event = CallEvent(
            call_id="test-call-123",
            from_number="123456789",  # 9 digits
            to_number="+15550001111",
            timestamp=datetime.now(),
            caller_name="John Doe",
            service_requested="plumbing",
            urgency="medium",
            budget=200,
            location_zip="90210",
        )
        
        qualification_result = QualificationResult(
            outcome="qualified",
            reason_codes=[],
        )
        
        result = await self.classification_service.classify_call(
            call_event=call_event,
            qualification_result=qualification_result,
        )
        
        assert result.classification == CallClassification.SPAM
        assert "phone_too_short" in result.reason_codes
    
    def test_is_valid_phone(self) -> None:
        """Test phone number validation."""
        service = ClassificationService()
        
        # Valid phones
        assert service._is_valid_phone("+15551234567") is True
        assert service._is_valid_phone("15551234567") is True
        assert service._is_valid_phone("(555) 123-4567") is True
        
        # Invalid phones
        assert service._is_valid_phone("") is False
        assert service._is_valid_phone("123456789") is False
        assert service._is_valid_phone("abc") is False
    
    def test_check_required_fields(self) -> None:
        """Test required fields checking."""
        service = ClassificationService()
        
        # All fields present
        call_event = CallEvent(
            call_id="test",
            from_number="+15551234567",
            to_number="+15550001111",
            timestamp=datetime.now(),
            service_requested="plumbing",
            urgency="medium",
            budget=200,
            location_zip="90210",
        )
        missing = service._check_required_fields(call_event)
        assert missing == []
        
        # Missing fields
        call_event.service_requested = None
        call_event.location_zip = None
        missing = service._check_required_fields(call_event)
        assert "missing_service_requested" in missing
        assert "missing_location" in missing
    
    def test_check_spam_patterns(self) -> None:
        """Test spam pattern detection."""
        service = ClassificationService()
        
        # Normal call
        call_event = CallEvent(
            call_id="test",
            from_number="+15551234567",
            to_number="+15550001111",
            timestamp=datetime.now(),
            caller_name="John Doe",
            service_requested="plumbing",
            urgency="medium",
            budget=200,
            location_zip="90210",
        )
        spam_reasons = service._check_spam_patterns(call_event)
        assert spam_reasons == []
        
        # Spam patterns
        call_event.from_number = "5551234567"
        call_event.caller_name = "Test User"
        spam_reasons = service._check_spam_patterns(call_event)
        assert "fake_phone_pattern" in spam_reasons
        assert "suspicious_caller_name" in spam_reasons
