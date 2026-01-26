"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import check_db_health, get_async_session

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Readiness check with database connectivity."""
    db_healthy = await check_db_health()
    
    if db_healthy:
        return {"status": "ready"}
    else:
        return {"status": "not_ready", "reason": "database_unhealthy"}
