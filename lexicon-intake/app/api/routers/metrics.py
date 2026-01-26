"""Metrics endpoint for Prometheus monitoring."""

from fastapi import APIRouter, Response
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    """
    Return metrics in Prometheus format.
    
    Simple metrics for monitoring system health and performance.
    """
    # Basic metrics - in production, you'd want to track actual counters
    metrics_text = """# HELP lexicon_intake_requests_total Total number of inbound requests
# TYPE lexicon_intake_requests_total counter
lexicon_intake_requests_total 0

# HELP lexicon_intake_leads_created_total Total number of leads created
# TYPE lexicon_intake_leads_created_total counter
lexicon_intake_leads_created_total 0

# HELP lexicon_intake_delivery_attempts_total Total delivery attempts
# TYPE lexicon_intake_delivery_attempts_total counter
lexicon_intake_delivery_attempts_total 0

# HELP lexicon_intake_delivery_successes_total Total successful deliveries
# TYPE lexicon_intake_delivery_successes_total counter
lexicon_intake_delivery_successes_total 0

# HELP lexicon_intake_delivery_failures_total Total failed deliveries
# TYPE lexicon_intake_delivery_failures_total counter
lexicon_intake_delivery_failures_total 0

# HELP lexicon_intake_queue_size Current queue size
# TYPE lexicon_intake_queue_size gauge
lexicon_intake_queue_size 0

# HELP lexicon_intake_processing_duration_seconds Processing duration in seconds
# TYPE lexicon_intake_processing_duration_seconds histogram
lexicon_intake_processing_duration_seconds_bucket{le="0.1"} 0
lexicon_intake_processing_duration_seconds_bucket{le="0.5"} 0
lexicon_intake_processing_duration_seconds_bucket{le="1.0"} 0
lexicon_intake_processing_duration_seconds_bucket{le="2.0"} 0
lexicon_intake_processing_duration_seconds_bucket{le="5.0"} 0
lexicon_intake_processing_duration_seconds_bucket{le="+Inf"} 0
lexicon_intake_processing_duration_seconds_sum 0
lexicon_intake_processing_duration_seconds_count 0
"""
    
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
