"""Tests for service type normalization."""

import pytest
from app.services.service_normalization import ServiceNormalizationService
from app.core.enums import ServiceType


class TestServiceNormalization:
    """Test cases for service type normalization."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = ServiceNormalizationService()
    
    def test_hvac_keywords(self) -> None:
        """Test HVAC keyword detection."""
        test_cases = [
            ("My AC is broken", ServiceType.HVAC_REPAIR),
            ("Air conditioner not working", ServiceType.HVAC_REPAIR),
            ("Need furnace repair", ServiceType.HVAC_REPAIR),
            ("Heating system issue", ServiceType.HVAC_REPAIR),
            ("Install new AC unit", ServiceType.HVAC_INSTALL),
            ("HAC installation needed", ServiceType.HVAC_INSTALL),
            ("New furnace installation", ServiceType.HVAC_INSTALL),
            ("AC replacement", ServiceType.HVAC_INSTALL),
            ("Thermostat not working", ServiceType.HVAC_REPAIR),
            ("Heat pump repair", ServiceType.HVAC_REPAIR),
        ]
        
        for service_request, expected_type in test_cases:
            result_type, reason_codes = self.service.normalize_service_type(service_request)
            assert result_type == expected_type
            assert any("SERVICE_TYPE_KEYWORD:" in code for code in reason_codes)
    
    def test_plumbing_keywords(self) -> None:
        """Test plumbing keyword detection."""
        test_cases = [
            ("Pipe is leaking", ServiceType.PLUMBING),
            ("Drain is clogged", ServiceType.PLUMBING),
            ("Toilet not flushing", ServiceType.PLUMBING),
            ("Sewer line issue", ServiceType.PLUMBING),
            ("Water heater broken", ServiceType.PLUMBING),
            ("Faucet dripping", ServiceType.PLUMBING),
            ("Garbage disposal not working", ServiceType.PLUMBING),
            ("Water line repair", ServiceType.PLUMBING),
            ("Septic tank problem", ServiceType.PLUMBING),
            "Burst pipe",
        ]
        
        for service_request, expected_type in test_cases:
            result_type, reason_codes = self.service.normalize_service_type(service_request)
            assert result_type == expected_type
            assert any("SERVICE_TYPE_KEYWORD:" in code for code in reason_codes)
    
    def test_pressure_wash_keywords(self) -> None:
        """Test pressure washing keyword detection."""
        test_cases = [
            ("Pressure washing needed", ServiceType.PRESSURE_WASH),
            "Power wash driveway",
            ("Softwash exterior", ServiceType.PRESSURE_WASH),
            ("House washing service", ServiceType.PRESSURE_WASH),
            ("Deck cleaning", ServiceType.PRESSURE_WASH),
            ("Siding cleaning", ServiceType.PRESSURE_WASH),
            ("Roof cleaning", ServiceType.PRESSURE_WASH),
            ("Concrete cleaning", ServiceType.PRESSURE_WASH),
            ("Exterior cleaning", ServiceType.PRESSURE_WASH),
        ]
        
        for service_request, expected_type in test_cases:
            result_type, reason_codes = self.service.normalize_service_type(service_request)
            assert result_type == expected_type
            assert any("SERVICE_TYPE_KEYWORD:" in code for code in reason_codes)
    
    def test_restoration_keywords(self) -> None:
        """Test restoration keyword detection."""
        test_cases = [
            ("Mold remediation", ServiceType.RESTORATION),
            ("Water damage restoration", ServiceType.RESTORATION),
            ("Fire damage cleanup", ServiceType.RESTORATION),
            ("Smoke damage repair", ServiceType.RESTORATION),
            ("Storm damage", ServiceType.RESTORATION),
            ("Emergency restoration", ServiceType.RESTORATION),
            ("Water removal", ServiceType.RESTORATION),
            ("Structural drying", ServiceType.RESTORATION),
            ("Flood cleanup", ServiceType.RESTORATION),
        ]
        
        for service_request, expected_type in test_cases:
            result_type, reason_codes = self.service.normalize_service_type(service_request)
            assert result_type == expected_type
            assert any("SERVICE_TYPE_KEYWORD:" in code for code in reason_codes)
    
    def test_unknown_service_type(self) -> None:
        """Test unknown service type when no keywords match."""
        test_cases = [
            "General maintenance",
            "Landscaping service",
            "Painting job",
            "Electrical work",  # Not in our keyword list
            "Roofing repair",  # Not in our keyword list
            "",  # Empty string
            "Random text with no relevant keywords",
        ]
        
        for service_request in test_cases:
            result_type, reason_codes = self.service.normalize_service_type(service_request)
            assert result_type == ServiceType.UNKNOWN
            if service_request:
                assert "SERVICE_TYPE_NO_MATCH" in reason_codes
            else:
                assert "SERVICE_TYPE_EMPTY" in reason_codes
    
    def test_case_insensitive_matching(self) -> None:
        """Test that keyword matching is case insensitive."""
        test_cases = [
            ("AC BROKEN", ServiceType.HVAC_REPAIR),
            ("air conditioner", ServiceType.HVAC_REPAIR),
            ("FURNACE Repair", ServiceType.HVAC_REPAIR),
            ("PIPE LEAK", ServiceType.PLUMBING),
            ("Pressure Wash", ServiceType.PRESSURE_WASH),
            ("MOLD REMEDIATION", ServiceType.RESTORATION),
        ]
        
        for service_request, expected_type in test_cases:
            result_type, reason_codes = self.service.normalize_service_type(service_request)
            assert result_type == expected_type
    
    def test_multiple_keywords_priority(self) -> None:
        """Test that the first matching keyword takes priority."""
        # HVAC keywords should match before others
        result_type, reason_codes = self.service.normalize_service_type("AC pipe leak")
        assert result_type == ServiceType.HVAC_REPAIR
        assert "SERVICE_TYPE_KEYWORD:ac" in reason_codes
        
        # Plumbing keywords should match
        result_type, reason_codes = self.service.normalize_service_type("pipe ac leak")
        assert result_type == ServiceType.PLUMBING
        assert "SERVICE_TYPE_KEYWORD:pipe" in reason_codes
    
    def test_get_all_keywords(self) -> None:
        """Test getting all keyword mappings."""
        keywords = self.service.get_all_keywords()
        
        # Check that all service types are present
        assert ServiceType.HVAC_REPAIR.value in keywords
        assert ServiceType.HVAC_INSTALL.value in keywords
        assert ServiceType.PLUMBING.value in keywords
        assert ServiceType.PRESSURE_WASH.value in keywords
        assert ServiceType.RESTORATION.value in keywords
        
        # Check that keywords are lists
        for service_type, keyword_list in keywords.items():
            assert isinstance(keyword_list, list)
            assert len(keyword_list) > 0
            
            # Check that all keywords are strings
            for keyword in keyword_list:
                assert isinstance(keyword, str)
                assert len(keyword) > 0
