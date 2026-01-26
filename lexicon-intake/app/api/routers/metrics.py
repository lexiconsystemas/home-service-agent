"""Prometheus metrics endpoint."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response
import redis
import structlog

logger = structlog.get_logger()

router = APIRouter()

# Initialize Redis client for queue metrics
try:
    redis_client = redis.from_url("redis://localhost:6379/0")
except Exception as e:
    logger.warning("Redis not available for queue metrics", error=str(e))
    redis_client = None

# Define metrics
inbound_calls_total = Counter(
    'lexicon_inbound_calls_total',
    'Total number of inbound calls processed',
    ['client_id', 'classification']
)

leads_qualified_total = Counter(
    'lexicon_leads_qualified_total',
    'Total number of qualified leads',
    ['client_id', 'service_type']
)

leads_unqualified_total = Counter(
    'lexicon_leads_unqualified_total',
    'Total number of unqualified leads',
    ['client_id', 'reason']
)

deliveries_sent_total = Counter(
    'lexicon_deliveries_sent_total',
    'Total number of successful deliveries',
    ['client_id', 'channel', 'purpose']
)

deliveries_failed_total = Counter(
    'lexicon_deliveries_failed_total',
    'Total number of failed deliveries',
    ['client_id', 'channel', 'purpose', 'error_type']
)

delivery_duration_seconds = Histogram(
    'lexicon_delivery_duration_seconds',
    'Time spent processing deliveries',
    ['client_id', 'channel', 'purpose'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

queue_depth = Gauge(
    'lexicon_queue_depth',
    'Current queue depth',
    ['queue_name']
)

dlq_size = Gauge(
    'lexicon_dlq_size',
    'Current dead letter queue size',
    ['client_id']
)

scheduling_responses_total = Counter(
    'lexicon_scheduling_responses_total',
    'Total number of scheduling responses',
    ['client_id', 'response_type']  # response_type: valid, invalid, timeout
)

config_updates_total = Counter(
    'lexicon_config_updates_total',
    'Total number of configuration updates',
    ['client_id', 'config_type', 'actor_type']
)

delivery_replays_total = Counter(
    'lexicon_delivery_replays_total',
    'Total number of delivery replays',
    ['client_id', 'channel', 'original_status']
)


@router.get("/metrics")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    # Update queue metrics if Redis is available
    if redis_client:
        try:
            # Get queue depths
            for queue_name in ['high', 'default', 'low']:
                try:
                    queue_key = f"rq:queue:{queue_name}"
                    depth = redis_client.llen(queue_key)
                    queue_depth.labels(queue_name=queue_name).set(depth)
                except Exception as e:
                    logger.warning(f"Failed to get queue depth for {queue_name}", error=str(e))
            
            # Get DLQ size (this would need to be tracked separately)
            # For now, we'll set it to 0
            dlq_size.labels(client_id="all").set(0)
            
        except Exception as e:
            logger.warning("Failed to update queue metrics", error=str(e))
    
    # Generate metrics
    metrics_data = generate_latest()
    
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
    )
