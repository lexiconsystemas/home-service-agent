"""Tests for rule engine."""

import json
import pytest

from app.domain.rules.rule_engine import RuleEngine
from app.domain.rules.rule_defs import QualificationRules


class TestRuleEngine:
    """Test cases for RuleEngine."""
    
    def test_evaluate_rules_all_passed(self) -> None:
        """Test qualification when all rules pass."""
        rules_json = json.dumps({
            "service_types_allowed": ["plumbing", "electrical", "hvac"],
            "service_area_zip_prefixes": ["90210", "90211", "90212"],
            "min_budget": 100,
            "urgency_allowed": ["low", "medium", "high"],
        })
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested="plumbing",
            location_zip="90210",
            budget=200,
            urgency="medium",
        )
        
        assert qualified is True
        assert reason_codes == []
    
    def test_evaluate_rules_service_type_not_allowed(self) -> None:
        """Test qualification when service type is not allowed."""
        rules_json = json.dumps({
            "service_types_allowed": ["plumbing", "electrical", "hvac"],
            "service_area_zip_prefixes": ["90210", "90211", "90212"],
            "min_budget": 100,
            "urgency_allowed": ["low", "medium", "high"],
        })
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested="landscaping",
            location_zip="90210",
            budget=200,
            urgency="medium",
        )
        
        assert qualified is False
        assert "service_type_not_allowed" in reason_codes
    
    def test_evaluate_rules_service_area_not_allowed(self) -> None:
        """Test qualification when service area is not allowed."""
        rules_json = json.dumps({
            "service_types_allowed": ["plumbing", "electrical", "hvac"],
            "service_area_zip_prefixes": ["90210", "90211", "90212"],
            "min_budget": 100,
            "urgency_allowed": ["low", "medium", "high"],
        })
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested="plumbing",
            location_zip="10001",
            budget=200,
            urgency="medium",
        )
        
        assert qualified is False
        assert "service_area_not_allowed" in reason_codes
    
    def test_evaluate_rules_budget_too_low(self) -> None:
        """Test qualification when budget is too low."""
        rules_json = json.dumps({
            "service_types_allowed": ["plumbing", "electrical", "hvac"],
            "service_area_zip_prefixes": ["90210", "90211", "90212"],
            "min_budget": 100,
            "urgency_allowed": ["low", "medium", "high"],
        })
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested="plumbing",
            location_zip="90210",
            budget=50,
            urgency="medium",
        )
        
        assert qualified is False
        assert "budget_too_low" in reason_codes
    
    def test_evaluate_rules_urgency_not_allowed(self) -> None:
        """Test qualification when urgency is not allowed."""
        rules_json = json.dumps({
            "service_types_allowed": ["plumbing", "electrical", "hvac"],
            "service_area_zip_prefixes": ["90210", "90211", "90212"],
            "min_budget": 100,
            "urgency_allowed": ["medium", "high"],
        })
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested="plumbing",
            location_zip="90210",
            budget=200,
            urgency="low",
        )
        
        assert qualified is False
        assert "urgency_not_allowed" in reason_codes
    
    def test_evaluate_rules_missing_fields(self) -> None:
        """Test qualification when required fields are missing."""
        rules_json = json.dumps({
            "service_types_allowed": ["plumbing", "electrical", "hvac"],
            "service_area_zip_prefixes": ["90210", "90211", "90212"],
            "min_budget": 100,
            "urgency_allowed": ["low", "medium", "high"],
        })
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested=None,
            location_zip=None,
            budget=None,
            urgency="medium",
        )
        
        assert qualified is False
        assert "missing_service_type" in reason_codes
        assert "missing_location" in reason_codes
        assert "missing_budget" in reason_codes
    
    def test_evaluate_rules_invalid_json(self) -> None:
        """Test qualification with invalid rules JSON."""
        rules_json = "invalid json"
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested="plumbing",
            location_zip="90210",
            budget=200,
            urgency="medium",
        )
        
        assert qualified is False
        assert "invalid_rules" in reason_codes
    
    def test_evaluate_rules_case_insensitive(self) -> None:
        """Test that service type and urgency matching is case insensitive."""
        rules_json = json.dumps({
            "service_types_allowed": ["Plumbing", "Electrical", "HVAC"],
            "service_area_zip_prefixes": ["90210", "90211", "90212"],
            "min_budget": 100,
            "urgency_allowed": ["Low", "Medium", "High"],
        })
        
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested="plumbing",  # lowercase
            location_zip="90210",
            budget=200,
            urgency="MEDIUM",  # mixed case
        )
        
        assert qualified is True
        assert reason_codes == []
