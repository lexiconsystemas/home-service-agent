"""Delivery recovery job for stuck pending deliveries."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog

try:
    from rq import Queue
    from rq_scheduler import Scheduler
    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False
    Queue = None
    Scheduler = None

from app.core.enums import DeliveryStatus
from app.db.repos.delivery_repo import DeliveryRepository
from app.db.repos.audit_repo import AuditRepository
from app.db.session import get_async_session_context
from app.workers.queue import enqueue_delivery_task
from app.settings import settings

logger = structlog.get_logger()


class DeliveryRecoveryJob:
    """Job to recover stuck pending deliveries."""
    
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.stuck_threshold_minutes = 5  # Deliveries stuck for > 5 minutes
    
    async def find_stuck_deliveries(self) -> list[Any]:
        """
        Find delivery records stuck in PENDING status for > threshold minutes.
        
        Returns:
            List of stuck delivery records
        """
        async with get_async_session_context() as db:
            delivery_repo = DeliveryRepository(db)
            
            # Calculate threshold time
            threshold_time = datetime.utcnow() - timedelta(minutes=self.stuck_threshold_minutes)
            
            # Find stuck deliveries
            stuck_deliveries = await delivery_repo.get_stuck_pending_deliveries(
                threshold_time=threshold_time
            )
            
            logger.info(
                "Found stuck deliveries",
                count=len(stuck_deliveries),
                threshold_minutes=self.stuck_threshold_minutes,
                threshold_time=threshold_time.isoformat(),
            )
            
            return stuck_deliveries
    
    async def recover_delivery(self, delivery_record) -> bool:
        """
        Recover a single stuck delivery.
        
        Args:
            delivery_record: Stuck delivery record
            
        Returns:
            True if recovery was successful
        """
        try:
            # Log recovery attempt to audit log
            await self._log_recovery_attempt(delivery_record)
            
            # Re-queue the delivery for processing
            await enqueue_delivery_task(str(delivery_record.id))
            
            logger.info(
                "Delivery recovery successful",
                delivery_id=str(delivery_record.id),
                lead_id=delivery_record.lead_id,
                channel=delivery_record.channel.value,
                purpose=delivery_record.purpose.value,
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Delivery recovery failed",
                delivery_id=str(delivery_record.id),
                lead_id=delivery_record.lead_id,
                error=str(e),
                exc_info=True,
            )
            return False
    
    async def _log_recovery_attempt(self, delivery_record) -> None:
        """Log recovery attempt to audit log."""
        async with get_async_session_context() as db:
            audit_repo = AuditRepository(db)
            
            await audit_repo.create_audit_log(
                actor_type="SYSTEM",
                actor_id="recovery_job",
                action="DELIVERY_RECOVERY",
                target_type="delivery",
                target_id=str(delivery_record.id),
                details={
                    "lead_id": delivery_record.lead_id,
                    "channel": delivery_record.channel.value,
                    "purpose": delivery_record.purpose.value,
                    "status": delivery_record.status.value,
                    "attempt_count": delivery_record.attempt_count,
                    "created_at": delivery_record.created_at.isoformat(),
                    "stuck_threshold_minutes": self.stuck_threshold_minutes,
                    "recovery_timestamp": datetime.utcnow().isoformat(),
                },
            )
    
    async def run_recovery_job(self) -> dict[str, Any]:
        """
        Run the complete recovery job.
        
        Returns:
            Recovery job statistics
        """
        logger.info("Starting delivery recovery job")
        
        try:
            # Find stuck deliveries
            stuck_deliveries = await self.find_stuck_deliveries()
            
            if not stuck_deliveries:
                logger.info("No stuck deliveries found")
                return {
                    "total_stuck": 0,
                    "recovered": 0,
                    "failed": 0,
                }
            
            # Recover each stuck delivery
            recovered_count = 0
            failed_count = 0
            
            for delivery_record in stuck_deliveries:
                if await self.recover_delivery(delivery_record):
                    recovered_count += 1
                else:
                    failed_count += 1
            
            stats = {
                "total_stuck": len(stuck_deliveries),
                "recovered": recovered_count,
                "failed": failed_count,
            }
            
            logger.info(
                "Delivery recovery job completed",
                **stats,
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                "Delivery recovery job failed",
                error=str(e),
                exc_info=True,
            )
            return {
                "total_stuck": 0,
                "recovered": 0,
                "failed": 0,
                "error": str(e),
            }


# Global recovery job instance
_recovery_job: DeliveryRecoveryJob | None = None


def get_recovery_job() -> DeliveryRecoveryJob:
    """Get or create recovery job instance."""
    global _recovery_job
    
    if _recovery_job is None:
        _recovery_job = DeliveryRecoveryJob(settings.redis_url)
    
    return _recovery_job


def recovery_job_task() -> dict[str, Any]:
    """
    RQ task wrapper for the recovery job.
    
    Returns:
        Recovery job statistics
    """
    logger.info("Starting scheduled recovery job task")
    
    try:
        # Run async recovery job in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            recovery_job = get_recovery_job()
            result = loop.run_until_complete(recovery_job.run_recovery_job())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(
            "Scheduled recovery job task failed",
            error=str(e),
            exc_info=True,
        )
        return {
            "total_stuck": 0,
            "recovered": 0,
            "failed": 0,
            "error": str(e),
        }


def schedule_recovery_job() -> None:
    """
    Schedule the recovery job to run every 5 minutes.
    
    This should be called during application startup.
    """
    if not RQ_AVAILABLE:
        logger.warning("RQ scheduler not available, skipping recovery job scheduling")
        return
    
    try:
        # Create RQ queue and scheduler
        queue = Queue("recovery", connection=settings.redis_url)
        scheduler = Scheduler(queue=queue, connection=settings.redis_url)
        
        # Schedule the job to run every 5 minutes
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),
            func=recovery_job_task,
            interval=300,  # 5 minutes in seconds
            repeat=None,  # Repeat indefinitely
            queue_name="recovery",
            description="Recover stuck pending deliveries",
        )
        
        logger.info("Delivery recovery job scheduled successfully")
        
    except Exception as e:
        logger.error(
            "Failed to schedule recovery job",
            error=str(e),
            exc_info=True,
        )
        raise


def run_recovery_job_now() -> dict[str, Any]:
    """
    Run the recovery job immediately (for manual execution).
    
    Returns:
        Recovery job statistics
    """
    return recovery_job_task()
