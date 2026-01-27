"""Redis Queue worker setup."""

import redis
from rq import Worker, Queue
from rq.connections import RedisConnection
import structlog

from app.settings import settings

logger = structlog.get_logger()

# Redis connection
redis_conn = redis.from_url(settings.redis_url)

# Queue names
DELIVERY_QUEUE = "delivery"
FOLLOWUP_QUEUE = "followup"

# Create queues
delivery_queue = Queue(DELIVERY_QUEUE, connection=redis_conn)
followup_queue = Queue(FOLLOWUP_QUEUE, connection=redis_conn)


async def enqueue_delivery_task(delivery_id: str) -> None:
    """
    Enqueue a delivery task.
    
    Args:
        delivery_id: Delivery record ID
    """
    from app.workers.tasks import deliver_multi_channel_task
    
    job = delivery_queue.enqueue(
        deliver_multi_channel_task,
        delivery_id,
        timeout=60,  # 1 minute timeout
        retry=3,      # Retry 3 times on failure
    )
    
    logger.info("Delivery task enqueued", delivery_id=delivery_id, job_id=job.id)


async def enqueue_followup_task(delivery_id: str, delay_minutes: int) -> None:
    """
    Enqueue a follow-up task with delay.
    
    Args:
        delivery_id: Delivery record ID
        delay_minutes: Delay in minutes
    """
    from app.workers.tasks import deliver_followup_task
    
    # Convert minutes to seconds for RQ
    delay_seconds = delay_minutes * 60
    
    job = followup_queue.enqueue(
        deliver_followup_task,
        delivery_id,
        scheduled_time=delay_seconds,
        timeout=60,
        retry=2,
    )
    
    logger.info("Followup task enqueued", delivery_id=delivery_id, delay_minutes=delay_minutes, job_id=job.id)


def start_worker() -> None:
    """Start the RQ worker."""
    with Connection(redis_conn):
        worker = Worker([delivery_queue, followup_queue])
        logger.info("Starting worker", queues=[DELIVERY_QUEUE, FOLLOWUP_QUEUE])
        worker.work()


if __name__ == "__main__":
    start_worker()
