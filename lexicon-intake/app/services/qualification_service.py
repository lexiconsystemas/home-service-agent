"""Qualification service for evaluating call events."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domain.models.call_event import CallEvent
from app.domain.rules.rule_engine import RuleEngine

logger = structlog.get_logger()


@dataclass
class QualificationResult:
    """Result of qualification evaluation."""
    
    outcome: str  # "qualified" or "unqualified"
    reason_codes: list[str]


class QualificationService:
    """Service for qualifying inbound calls."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def qualify_call(
        self,
        call_event: CallEvent,
        rules_json: str,
    ) -> QualificationResult:
        """
        Qualify a call event based on rules.
        
        Args:
            call_event: Call event data
            rules_json: JSON string containing qualification rules
            
        Returns:
            Qualification result with outcome and reason codes
        """
        logger.info(
            "Qualifying call",
            call_id=call_event.call_id,
            service_requested=call_event.service_requested,
            location_zip=call_event.location_zip,
            budget=call_event.budget,
            urgency=call_event.urgency,
        )
        
        # Evaluate rules
        qualified, reason_codes = RuleEngine.evaluate_rules(
            rules_json=rules_json,
            service_requested=call_event.service_requested,
            location_zip=call_event.location_zip,
            budget=call_event.budget,
            urgency=call_event.urgency,
        )
        
        outcome = "qualified" if qualified else "unqualified"
        
        logger.info(
            "Qualification completed",
            call_id=call_event.call_id,
            outcome=outcome,
            reason_codes=reason_codes,
        )
        
        return QualificationResult(
            outcome=outcome,
            reason_codes=reason_codes,
        )
