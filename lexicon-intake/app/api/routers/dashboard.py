"""Dashboard API endpoints for frontend analytics."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_async_session
from app.db.repos.metrics_repo import MetricsRepository
from app.db.repos.client_repo import ClientRepository
from app.services.auth_service import AuthService

logger = structlog.get_logger()

router = APIRouter()


async def verify_client_api_key(
    x_client_api_key: str = Header(..., alias="X-Client-API-Key")
) -> str:
    """Verify client API key and return client_id."""
    client_id = AuthService.extract_client_id_from_api_key(x_client_api_key)
    if not client_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid client API key",
        )

    return client_id


@router.get("/metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
) -> dict[str, Any]:
    """
    Get overview metrics for dashboard cards.

    Returns total calls, booked jobs, revenue, and conversion rate.
    """
    try:
        # Calculate date range
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        metrics_repo = MetricsRepository(db)
        metrics = await metrics_repo.get_metrics_for_period(
            client_id=client_id,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "success": True,
            "data": metrics,
        }

    except Exception as e:
        logger.error(
            "Failed to get dashboard metrics",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve metrics",
        )


@router.get("/call-performance")
async def get_call_performance(
    db: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
    days: int = Query(7, description="Number of days to look back"),
) -> dict[str, Any]:
    """
    Get daily call volume for charts.

    Returns call volume data for the last N days.
    """
    try:
        metrics_repo = MetricsRepository(db)
        call_volume = await metrics_repo.get_call_volume_by_day(
            client_id=client_id,
            days=days,
        )

        return {
            "success": True,
            "data": {
                "call_volume": call_volume,
                "period_days": days,
            },
        }

    except Exception as e:
        logger.error(
            "Failed to get call performance data",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve call performance data",
        )


@router.get("/revenue")
async def get_revenue_breakdown(
    db: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
) -> dict[str, Any]:
    """
    Get revenue breakdown by service type.

    Returns revenue data categorized by service type.
    """
    try:
        metrics_repo = MetricsRepository(db)
        revenue_breakdown = await metrics_repo.get_revenue_by_service_type(
            client_id=client_id,
            period=period,
        )

        # Calculate total revenue
        total_revenue = sum(item["revenue"] for item in revenue_breakdown)

        return {
            "success": True,
            "data": {
                "revenue_breakdown": revenue_breakdown,
                "total_revenue": total_revenue,
                "period": period,
            },
        }

    except Exception as e:
        logger.error(
            "Failed to get revenue breakdown",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve revenue data",
        )


@router.get("/funnel")
async def get_conversion_funnel(
    db: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
) -> dict[str, Any]:
    """
    Get conversion funnel data.

    Returns funnel data showing calls → answered → appointments → completed.
    """
    try:
        metrics_repo = MetricsRepository(db)
        funnel_data = await metrics_repo.get_conversion_funnel(
            client_id=client_id,
            period=period,
        )

        return {
            "success": True,
            "data": funnel_data,
        }

    except Exception as e:
        logger.error(
            "Failed to get conversion funnel data",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve funnel data",
        )


@router.get("/calls")
async def get_recent_calls(
    db: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
    limit: int = Query(50, description="Number of records to return"),
    offset: int = Query(0, description="Pagination offset"),
) -> dict[str, Any]:
    """
    Get recent call logs.

    Returns paginated list of recent calls.
    """
    try:
        metrics_repo = MetricsRepository(db)
        call_logs = await metrics_repo.get_recent_calls(
            client_id=client_id,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "data": call_logs,
        }

    except Exception as e:
        logger.error(
            "Failed to get recent calls",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve call logs",
        )


@router.get("/ai-summaries")
async def get_ai_summaries(
    db: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
    limit: int = Query(20, description="Number of records to return"),
    offset: int = Query(0, description="Pagination offset"),
) -> dict[str, Any]:
    """
    Get AI-generated call summaries.

    Returns paginated list of AI call summaries.
    """
    try:
        metrics_repo = MetricsRepository(db)
        summaries = await metrics_repo.get_ai_summaries(
            client_id=client_id,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "data": summaries,
        }

    except Exception as e:
        logger.error(
            "Failed to get AI summaries",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve AI summaries",
        )


@router.get("/profile")
async def get_business_profile(
    db: AsyncSession = Depends(get_async_session),
    client_id: str = Depends(verify_client_api_key),
) -> dict[str, Any]:
    """
    Get current client business profile.

    Returns client configuration and business information.
    """
    try:
        client_repo = ClientRepository(db)
        client_config = await client_repo.get_by_client_id(client_id)

        if not client_config:
            raise HTTPException(
                status_code=404,
                detail="Client configuration not found",
            )

        # Extract business_name from rules_json if available
        rules = client_config.rules_json or {}
        business_name = rules.get("business_name", client_id)

        # Return safe profile data
        profile_data = {
            "client_id": client_config.client_id,
            "business_name": business_name,
            "to_number": client_config.to_number,
            "greeting_message": client_config.greeting_message,
            "delivery_channels": client_config.delivery_channels,
            "followup_flags": client_config.followup_flags,
            "created_at": client_config.created_at.isoformat() if client_config.created_at else None,
            "updated_at": client_config.updated_at.isoformat() if client_config.updated_at else None,
        }

        return {
            "success": True,
            "data": profile_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get business profile",
            client_id=client_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve business profile",
        )
