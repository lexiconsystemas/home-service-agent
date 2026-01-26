"""Intake service for processing inbound calls."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.errors import ClientNotFoundError, ValidationError
from app.db.repos.client_repo import ClientRepository
from app.db.repos.lead_repo import LeadRepository
from app.domain.models.call_event import CallEvent, CallEventResponse
from app.services.qualification_service import QualificationService
from app.services.classification_service import ClassificationService
from app.services.delivery_service import DeliveryService

logger = structlog.get_logger()


class IntakeService:
    """Service for processing inbound call events."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.client_repo = ClientRepository(db)
        self.lead_repo = LeadRepository(db)
        self.qualification_service = QualificationService(db)
        self.classification_service = ClassificationService()
        self.delivery_service = DeliveryService(db)
    
    async def process_inbound_call(self, call_event: CallEvent) -> CallEventResponse:
        """
        Process inbound call event through the complete pipeline.
        
        Args:
            call_event: Inbound call event data
            
        Returns:
            Call event processing response
            
        Raises:
            ClientNotFoundError: If client configuration not found
            ValidationError: If validation fails
        """
        # Generate lead ID
        lead_id = str(uuid.uuid4())
        
        try:
            # Get client configuration
            client_config = await self.client_repo.get_by_to_number(call_event.to_number)
            if not client_config:
                # Fallback to demo client
                client_config = await self.client_repo.get_by_client_id("demo")
                if not client_config:
                    raise ClientNotFoundError(f"No client configuration found for to_number: {call_event.to_number}")
            
            logger.info(
                "Client configuration loaded",
                call_id=call_event.call_id,
                lead_id=lead_id,
                client_id=client_config.client_id,
                delivery_channels=client_config.delivery_channels,
            )
            
            # Run qualification
            qualification_result = await self.qualification_service.qualify_call(
                call_event=call_event,
                rules_json=client_config.rules_json,
            )
            
            # Run classification
            classification_result = await self.classification_service.classify_call(
                call_event=call_event,
                qualification_result=qualification_result,
            )
            
            # Create lead record
            lead_record = await self.lead_repo.create_lead(
                lead_id=lead_id,
                call_id=call_event.call_id,
                client_id=client_config.client_id,
                caller_name=call_event.caller_name,
                caller_phone=call_event.from_number,
                service_requested=call_event.service_requested,
                urgency=call_event.urgency,
                budget=call_event.budget,
                location_zip=call_event.location_zip,
                classification=classification_result.classification,
                reason_codes=classification_result.reason_codes,
                qualification_outcome=qualification_result.outcome,
            )
            
            logger.info(
                "Lead record created",
                lead_id=lead_id,
                classification=classification_result.classification.value,
                reason_codes=classification_result.reason_codes,
            )
            
            # Enqueue multi-channel delivery for qualified leads
            if classification_result.classification.value == "QUALIFIED":
                await self.delivery_service.enqueue_lead_delivery(
                    lead_id=lead_id,
                    client_config=client_config,
                )
                logger.info("Lead delivery enqueued", lead_id=lead_id)
            
            # Enqueue follow-up automation
            await self._enqueue_followup_automation(
                lead_id=lead_id,
                classification_result=classification_result,
                client_config=client_config,
            )
            
            return CallEventResponse(
                lead_id=lead_id,
                classification=classification_result.classification.value,
                message=f"Call processed successfully. Classification: {classification_result.classification.value}",
            )
            
        except Exception as e:
            logger.error(
                "Failed to process inbound call",
                call_id=call_event.call_id,
                lead_id=lead_id,
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def _enqueue_followup_automation(
        self,
        lead_id: str,
        classification_result,
        client_config,
    ) -> None:
        """
        Enqueue follow-up automation based on classification and client config.
        
        Args:
            lead_id: Lead identifier
            classification_result: Classification result
            client_config: Client configuration
        """
        # Only send follow-up for QUALIFIED and UNQUALIFIED (not SPAM/DROPPED)
        if classification_result.classification.value in ["QUALIFIED", "UNQUALIFIED"]:
            # Confirmation message
            await self.delivery_service.enqueue_followup_confirmation(
                lead_id=lead_id,
                client_config=client_config,
            )
            
            # Reminder message (only for qualified)
            if classification_result.classification.value == "QUALIFIED":
                await self.delivery_service.enqueue_followup_reminder(
                    lead_id=lead_id,
                    client_config=client_config,
                )
            
            # Urgent escalation
            await self.delivery_service.enqueue_urgent_escalation(
                lead_id=lead_id,
                client_config=client_config,
            )
