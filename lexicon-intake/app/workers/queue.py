"""Redis Queue worker setup."""

import redis
from rq import Worker, Queue, Connection
import structlog

from app.settings import settings

logger = structlog.get_logger()

# Redis connection
redis_conn = redis.from_url(settings.redis_url)

# Queue names
DELIVERY_QUEUE = "delivery"

# Create queues
delivery_queue = Queue(DELIVERY_QUEUE, connection=redis_conn)


async def enqueue_delivery_task(delivery_id: str) -> None:
    """
    Enqueue a delivery task.
    
    Args:
        delivery_id: Delivery record ID
    """
    from app.workers.tasks import deliver_webhook_task
    
    job = delivery_queue.enqueue(
        deliver_webhook_task,
        delivery_id,
        timeout=60,  # 1 minute timeout
        retry=3,      # Retry 3 times on failure
    )
    
    logger.info("Delivery task enqueued", delivery_id=delivery_id, job_id=job.id)


def start_worker() -> None:
    """Start the RQ worker."""
    with Connection(redis_conn):
        worker = Worker([delivery_queue])
        logger.info("Starting worker", queues=[DELIVERY_QUEUE])
        worker.work()


if __name__ == "__main__":
    start_worker()
