"""Intake service for processing inbound calls."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.errors import ClientNotFoundError, ValidationError
from app.core.time import utc_now
from app.db.repos.client_repo import ClientRepository
from app.db.repos.lead_repo import LeadRepository
from app.domain.models.call_event import CallEvent, CallEventResponse
from app.services.qualification_service import QualificationService
from app.services.classification_service import ClassificationService
from app.services.service_normalization import ServiceNormalizationService
from app.services.business_hours import BusinessHoursService
from app.services.routing_service import RoutingService
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
        self.service_normalization_service = ServiceNormalizationService()
        self.business_hours_service = BusinessHoursService()
        self.routing_service = RoutingService()
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
        utc_timestamp = utc_now()
        
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
                has_routing=bool(client_config.routing_json),
            )
            
            # Normalize service type
            service_type, service_reason_codes = self.service_normalization_service.normalize_service_type(
                call_event.service_requested or ""
            )
            
            # Determine time window if routing is configured
            time_window = None
            timezone_used = None
            local_time = None
            time_reason_codes = []
            
            if client_config.routing_json:
                timezone = client_config.routing_json.get("timezone", "UTC")
                business_hours = client_config.routing_json.get("business_hours", {})
                
                time_window, local_time, time_reason_codes = self.business_hours_service.determine_time_window(
                    utc_timestamp=utc_timestamp,
                    timezone=timezone,
                    business_hours=business_hours,
                )
                timezone_used = timezone
            
            # Select routing profile
            routing_profile = None
            routing_config = None
            routing_reason_codes = []
            
            if client_config.routing_json and time_window:
                routing_profile, routing_reason_codes = self.routing_service.select_routing_profile(
                    service_type=service_type,
                    time_window=time_window,
                    routing_json=client_config.routing_json,
                    utc_timestamp=utc_timestamp,
                    timezone=timezone_used,
                    local_time=local_time,
                )
                
                # Extract routing configuration
                base_config = {
                    "delivery_channels": client_config.delivery_channels,
                    "webhook_url": client_config.webhook_url,
                    "sms_to_numbers": client_config.sms_to_numbers,
                    "email_to_addresses": client_config.email_to_addresses,
                    "followup_flags": client_config.followup_flags,
                }
                routing_config = self.routing_service.extract_routing_config(routing_profile, base_config)
            
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
            
            # Combine all reason codes
            all_reason_codes = []
            all_reason_codes.extend(service_reason_codes)
            all_reason_codes.extend(time_reason_codes)
            all_reason_codes.extend(routing_reason_codes)
            all_reason_codes.extend(classification_result.reason_codes)
            
            # Prepare routing decision data
            routing_decision = {
                "profile_name": routing_profile.get("name") if routing_profile else None,
                "time_window": time_window.value if time_window else None,
                "timezone_used": timezone_used,
                "computed_local_time": local_time,
                "chosen_channels": routing_config["channels"] if routing_config else None,
                "chosen_destinations": {
                    "webhook_url": routing_config.get("webhook_url"),
                    "sms_to_numbers": routing_config.get("sms_to_numbers", []),
                    "email_to_addresses": routing_config.get("email_addresses", []),
                } if routing_config else None,
                "reason_codes": routing_reason_codes,
            }
            
            # Create lead record with routing decision inside transaction
            lead_record = await self.lead_repo.create_lead(
                lead_id=lead_id,
                call_id=call_event.call_id,
                client_id=client_config.client_id,
                caller_name=call_event.caller_name,
                caller_phone=call_event.from_number,
                service_requested=call_event.service_requested,
                service_type_normalized=service_type,
                service_normalization_reason_codes=service_reason_codes,
                urgency=call_event.urgency,
                budget=call_event.budget,
                location_zip=call_event.location_zip,
                classification=classification_result.classification,
                reason_codes=all_reason_codes,
                qualification_outcome=qualification_result.outcome,
                routing_profile_name=routing_decision["profile_name"],
                time_window=routing_decision["time_window"],
                timezone_used=routing_decision["timezone_used"],
                computed_local_time=routing_decision["computed_local_time"],
                chosen_channels=routing_decision["chosen_channels"],
                chosen_destinations=routing_decision["chosen_destinations"],
                routing_reason_codes=routing_decision["reason_codes"],
            )
            
            logger.info(
                "Lead record created with routing",
                lead_id=lead_id,
                classification=classification_result.classification.value,
                service_type=service_type.value,
                routing_profile=routing_decision["profile_name"],
                time_window=routing_decision["time_window"],
                chosen_channels=routing_decision["chosen_channels"],
                reason_codes=all_reason_codes,
            )
            
            # Commit transaction before enqueuing tasks
            await self.db.commit()
            
            # Enqueue tasks AFTER commit
            delivery_success = True
            if classification_result.classification.value == "QUALIFIED":
                delivery_success = await self._enqueue_delivery_with_routing(
                    lead_id=lead_id,
                    client_config=client_config,
                    routing_config=routing_config,
                )
                
                if not delivery_success:
                    # Mark delivery as failed but still return success
                    await self.lead_repo.update_delivery_pending(lead_id, False)
                    logger.warning(
                        "Delivery enqueue failed, marked as pending false",
                        lead_id=lead_id,
                    )
                else:
                    logger.info("Lead delivery enqueued successfully", lead_id=lead_id)
            
            # Enqueue follow-up automation using routing configuration
            await self._enqueue_followup_with_routing(
                lead_id=lead_id,
                classification_result=classification_result,
                client_config=client_config,
                routing_config=routing_config,
            )
            
            response_data = {
                "lead_id": lead_id,
                "classification": classification_result.classification.value,
                "service_type": service_type.value,
                "routing_profile": routing_decision["profile_name"],
                "time_window": routing_decision["time_window"],
                "message": f"Call processed successfully. Classification: {classification_result.classification.value}",
            }
            
            # Add warning if delivery failed
            if not delivery_success and classification_result.classification.value == "QUALIFIED":
                response_data["warning"] = "Delivery enqueue failed, will retry"
            
            return CallEventResponse(**response_data)
            
        except Exception as e:
            # Rollback on any error
            await self.db.rollback()
            logger.error(
                "Failed to process inbound call",
                call_id=call_event.call_id,
                lead_id=lead_id,
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def _enqueue_delivery_with_routing(
        self,
        lead_id: str,
        client_config,
        routing_config: dict | None,
    ) -> bool:
        """
        Enqueue delivery using routing configuration.
        
        Args:
            lead_id: Lead identifier
            client_config: Client configuration object
            routing_config: Routing configuration from profile or None
            
        Returns:
            True if enqueue succeeded, False otherwise
        """
        try:
            if routing_config:
                # Use routing configuration
                channels = routing_config["channels"]
                destinations = routing_config["chosen_destinations"]
                
                # Create a mock client config for delivery service
                mock_client_config = type('MockClientConfig', (), {
                    'delivery_channels': channels,
                    'webhook_url': destinations.get('webhook_url'),
                    'sms_to_numbers': destinations.get('sms_to_numbers', []),
                    'email_to_addresses': destinations.get('email_to_addresses', []),
                    'followup_flags': routing_config.get('followup', {}),
                    'message_templates': client_config.message_templates,
                })()
                
                await self.delivery_service.enqueue_lead_delivery(
                    lead_id=lead_id,
                    client_config=mock_client_config,
                )
            else:
                # Use base client configuration
                await self.delivery_service.enqueue_lead_delivery(
                    lead_id=lead_id,
                    client_config=client_config,
                )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to enqueue delivery",
                lead_id=lead_id,
                routing_profile_used=routing_config is not None,
                error=str(e),
                exc_info=True,
            )
            return False
    
    async def _enqueue_followup_with_routing(
        self,
        lead_id: str,
        classification_result,
        client_config,
        routing_config: dict | None,
    ) -> None:
        """
        Enqueue follow-up automation using routing configuration.
        
        Args:
            lead_id: Lead identifier
            classification_result: Classification result
            client_config: Client configuration object
            routing_config: Routing configuration from profile or None
        """
        # Only send follow-up for QUALIFIED and UNQUALIFIED (not SPAM/DROPPED)
        if classification_result.classification.value not in ["QUALIFIED", "UNQUALIFIED"]:
            return
        
        try:
            if routing_config:
                # Use routing configuration
                followup_flags = routing_config.get("followup", {})
                escalation_config = routing_config.get("escalation", {})
                
                # Create mock client config for delivery service
                mock_client_config = type('MockClientConfig', (), {
                    'followup_flags': followup_flags,
                    'message_templates': client_config.message_templates,
                    'sms_to_numbers': routing_config["chosen_destinations"].get('sms_to_numbers', []),
                })()
                
                # Confirmation message
                if followup_flags.get("send_confirmation_to_caller"):
                    await self.delivery_service.enqueue_followup_confirmation(
                        lead_id=lead_id,
                        client_config=mock_client_config,
                    )
                
                # Reminder message (only for qualified)
                if (classification_result.classification.value == "QUALIFIED" and 
                    followup_flags.get("send_reminder_to_caller")):
                    await self.delivery_service.enqueue_followup_reminder(
                        lead_id=lead_id,
                        client_config=mock_client_config,
                    )
                
                # Urgent escalation
                if escalation_config.get("urgent_escalation"):
                    await self._enqueue_urgent_override(
                        lead_id=lead_id,
                        escalation_config=escalation_config,
                        client_config=client_config,
                    )
            else:
                # Use base client configuration
                await self.delivery_service.enqueue_followup_confirmation(
                    lead_id=lead_id,
                    client_config=client_config,
                )
                
                if classification_result.classification.value == "QUALIFIED":
                    await self.delivery_service.enqueue_followup_reminder(
                        lead_id=lead_id,
                        client_config=client_config,
                    )
                
                await self.delivery_service.enqueue_urgent_escalation(
                    lead_id=lead_id,
                    client_config=client_config,
                )
                
        except Exception as e:
            logger.error(
                "Failed to enqueue follow-up",
                lead_id=lead_id,
                classification=classification_result.classification.value,
                routing_profile_used=routing_config is not None,
                error=str(e),
                exc_info=True,
            )
    
    async def _enqueue_urgent_override(
        self,
        lead_id: str,
        escalation_config: dict,
        client_config,
    ) -> None:
        """
        Enqueue urgent escalation with override recipients.
        
        Args:
            lead_id: Lead identifier
            escalation_config: Escalation configuration from routing profile
            client_config: Original client configuration
        """
        # Get lead record to check urgency and classification
        lead_record = await self.lead_repo.get_by_lead_id(lead_id)
        if not lead_record:
            return
        
        # Check if urgent and qualified
        if (lead_record.urgency.value == "same_day" and 
            lead_record.classification.value == "QUALIFIED"):
            
            logger.info(
                "Urgent escalation with override",
                lead_id=lead_id,
                override_channels=escalation_config.get("urgent_override_channels", []),
                override_recipients=escalation_config.get("urgent_override_recipients", []),
            )
            
            # Send to override recipients
            override_recipients = escalation_config.get("urgent_override_recipients", [])
            for recipient in override_recipients:
                await self.delivery_service._enqueue_channel_delivery(
                    lead_id=lead_id,
                    channel="SMS",  # Override is typically SMS
                    purpose="URGENT_ESCALATION",
                    client_config=client_config,
                    destination_override=recipient,
                )
