"""Rule engine for deterministic qualification."""

import json
from typing import Any

import structlog

from app.core.enums import ServiceType
from app.domain.rules.rule_defs import QualificationRules

logger = structlog.get_logger()


class RuleEngine:
    """Deterministic rule engine for call qualification."""
    
    @staticmethod
    def evaluate_rules(
        rules_json: str,
        service_requested: str | None,
        location_zip: str | None,
        budget: int | None,
        urgency: str,
    ) -> tuple[bool, list[str]]:
        """
        Evaluate qualification rules against call data.
        
        Args:
            rules_json: JSON string containing qualification rules
            service_requested: Service type requested
            location_zip: Service location ZIP code
            budget: Budget in dollars
            urgency: Urgency level
            
        Returns:
            Tuple of (qualified: bool, reason_codes: list[str])
        """
        try:
            rules = QualificationRules(**json.loads(rules_json))
        except Exception as e:
            logger.error("Failed to parse rules", error=str(e))
            return False, ["invalid_rules"]
        
        reason_codes = []
        
        # Check service type
        if service_requested:
            if service_requested.lower() not in [st.lower() for st in rules.service_types_allowed]:
                reason_codes.append("service_type_not_allowed")
        else:
            reason_codes.append("missing_service_type")
        
        # Check service area
        if location_zip:
            zip_prefix = location_zip[:5] if len(location_zip) >= 5 else location_zip
            if not any(zip_prefix.startswith(prefix) for prefix in rules.service_area_zip_prefixes):
                reason_codes.append("service_area_not_allowed")
        else:
            reason_codes.append("missing_location")
        
        # Check budget
        if budget is not None:
            if budget < rules.min_budget:
                reason_codes.append("budget_too_low")
        else:
            reason_codes.append("missing_budget")
        
        # Check urgency
        if urgency.lower() not in [u.lower() for u in rules.urgency_allowed]:
            reason_codes.append("urgency_not_allowed")
        
        # Qualified if no reason codes
        qualified = len(reason_codes) == 0
        
        logger.info(
            "Rules evaluated",
            qualified=qualified,
            reason_codes=reason_codes,
            service_requested=service_requested,
            location_zip=location_zip,
            budget=budget,
            urgency=urgency,
        )
        
        return qualified, reason_codes
