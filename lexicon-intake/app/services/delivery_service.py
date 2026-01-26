"""Delivery service for multi-channel lead delivery."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.enums import DeliveryChannel, DeliveryPurpose
from app.db.repos.delivery_repo import DeliveryRepository
from app.db.repos.lead_repo import LeadRepository
from app.db.repos.client_repo import ClientRepository
from app.workers.queue import enqueue_delivery_task, enqueue_followup_task

logger = structlog.get_logger()


class DeliveryService:
    """Service for delivering leads via multiple channels."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.delivery_repo = DeliveryRepository(db)
        self.lead_repo = LeadRepository(db)
        self.client_repo = ClientRepository(db)
    
    async def enqueue_lead_delivery(
        self,
        lead_id: str,
        client_config,
    ) -> None:
        """
        Enqueue lead delivery for all enabled channels.
        
        Args:
            lead_id: Lead identifier
            client_config: Client configuration object
        """
        logger.info("Enqueuing multi-channel delivery", lead_id=lead_id, channels=client_config.delivery_channels)
        
        # Enqueue delivery for each enabled channel
        for channel in client_config.delivery_channels:
            await self._enqueue_channel_delivery(
                lead_id=lead_id,
                channel=DeliveryChannel(channel),
                purpose=DeliveryPurpose.LEAD_DELIVERY,
                client_config=client_config,
            )
    
    async def enqueue_followup_confirmation(
        self,
        lead_id: str,
        client_config,
    ) -> None:
        """
        Enqueue follow-up confirmation to caller.
        
        Args:
            lead_id: Lead identifier
            client_config: Client configuration object
        """
        followup_flags = client_config.followup_flags or {}
        
        if followup_flags.get("send_confirmation_to_caller"):
            logger.info("Enqueuing follow-up confirmation", lead_id=lead_id)
            
            await self._enqueue_channel_delivery(
                lead_id=lead_id,
                channel=DeliveryChannel.SMS,
                purpose=DeliveryPurpose.FOLLOWUP_CONFIRMATION,
                client_config=client_config,
            )
    
    async def enqueue_followup_reminder(
        self,
        lead_id: str,
        client_config,
    ) -> None:
        """
        Enqueue follow-up reminder to caller (delayed).
        
        Args:
            lead_id: Lead identifier
            client_config: Client configuration object
        """
        followup_flags = client_config.followup_flags or {}
        
        if followup_flags.get("send_reminder_to_caller"):
            delay_minutes = followup_flags.get("reminder_delay_minutes", 30)
            
            logger.info("Enqueuing follow-up reminder", lead_id=lead_id, delay_minutes=delay_minutes)
            
            # Get lead record to check if qualified
            lead_record = await self.lead_repo.get_by_lead_id(lead_id)
            if not lead_record or lead_record.classification.value != "QUALIFIED":
                logger.info("Skipping reminder - not qualified", lead_id=lead_id)
                return
            
            # Create delivery record first
            delivery_record = await self.delivery_repo.create_delivery_record(
                lead_id=lead_id,
                channel=DeliveryChannel.SMS,
                purpose=DeliveryPurpose.FOLLOWUP_REMINDER,
                destination=lead_record.caller_phone,
            )
            
            # Enqueue delayed task
            await enqueue_followup_task(
                delivery_id=str(delivery_record.id),
                delay_minutes=delay_minutes,
            )
    
    async def enqueue_urgent_escalation(
        self,
        lead_id: str,
        client_config,
    ) -> None:
        """
        Enqueue urgent escalation notification.
        
        Args:
            lead_id: Lead identifier
            client_config: Client configuration object
        """
        followup_flags = client_config.followup_flags or {}
        
        if followup_flags.get("urgent_escalation"):
            # Get lead record to check urgency and classification
            lead_record = await self.lead_repo.get_by_lead_id(lead_id)
            if not lead_record:
                return
            
            # Check if urgent and qualified
            if (lead_record.urgency.value == "same_day" and 
                lead_record.classification.value == "QUALIFIED"):
                
                logger.info("Enqueuing urgent escalation", lead_id=lead_id)
                
                # Send to all SMS recipients
                sms_numbers = client_config.sms_to_numbers or []
                for sms_number in sms_numbers:
                    await self._enqueue_channel_delivery(
                        lead_id=lead_id,
                        channel=DeliveryChannel.SMS,
                        purpose=DeliveryPurpose.URGENT_ESCALATION,
                        client_config=client_config,
                        destination_override=sms_number,
                    )
    
    async def _enqueue_channel_delivery(
        self,
        lead_id: str,
        channel: DeliveryChannel,
        purpose: DeliveryPurpose,
        client_config,
        destination_override: str | None = None,
    ) -> None:
        """
        Enqueue delivery for a specific channel.
        
        Args:
            lead_id: Lead identifier
            channel: Delivery channel
            purpose: Delivery purpose
            client_config: Client configuration object
            destination_override: Override destination (for escalations)
        """
        # Determine destination
        if destination_override:
            destination = destination_override
        elif channel == DeliveryChannel.WEBHOOK:
            destination = client_config.webhook_url
        elif channel == DeliveryChannel.EMAIL:
            # Use first email address for lead delivery
            if purpose == DeliveryPurpose.LEAD_DELIVERY:
                destination = (client_config.email_to_addresses or [None])[0]
            else:
                # For follow-up, use caller phone (converted to email if needed)
                lead_record = await self.lead_repo.get_by_lead_id(lead_id)
                destination = lead_record.caller_phone if lead_record else None
        elif channel == DeliveryChannel.SMS:
            # Use caller phone for follow-up, or first SMS number for lead delivery
            if purpose == DeliveryPurpose.LEAD_DELIVERY:
                destination = (client_config.sms_to_numbers or [None])[0]
            else:
                lead_record = await self.lead_repo.get_by_lead_id(lead_id)
                destination = lead_record.caller_phone if lead_record else None
        else:
            destination = None
        
        if not destination:
            logger.warning(
                "No destination for channel delivery",
                lead_id=lead_id,
                channel=channel.value,
                purpose=purpose.value,
            )
            return
        
        # Create delivery record
        delivery_record = await self.delivery_repo.create_delivery_record(
            lead_id=lead_id,
            channel=channel,
            purpose=purpose,
            destination=destination,
        )
        
        # Enqueue delivery task
        await enqueue_delivery_task(str(delivery_record.id))
        
        logger.info(
            "Channel delivery enqueued",
            lead_id=lead_id,
            delivery_id=str(delivery_record.id),
            channel=channel.value,
            purpose=purpose.value,
            destination=destination,
        )
