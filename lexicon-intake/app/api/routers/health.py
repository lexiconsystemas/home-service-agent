"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
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


@router.get("/db-schema")
async def db_schema_check(
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Check database schema - list columns in client_configs table."""
    import os
    import re

    from app.settings import settings

    # Show masked database URL for debugging
    db_url = settings.database_url
    if db_url:
        # Mask password in URL
        masked_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", db_url)
    else:
        masked_url = "NOT SET"

    # Also check raw env vars
    raw_database_url = os.environ.get("DATABASE_URL", "NOT SET")
    if raw_database_url != "NOT SET":
        raw_masked = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", raw_database_url)
    else:
        raw_masked = raw_database_url

    try:
        result = await db.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'client_configs'
                ORDER BY ordinal_position
            """)
        )
        columns = [
            {"name": row[0], "type": row[1], "nullable": row[2]}
            for row in result.fetchall()
        ]

        # Also get migration status
        migration_result = await db.execute(
            text("SELECT version_num FROM alembic_version")
        )
        migration_row = migration_result.fetchone()
        migration_version = migration_row[0] if migration_row else "none"

        return {
            "status": "ok",
            "database_url_masked": masked_url,
            "raw_database_url_masked": raw_masked,
            "migration_version": migration_version,
            "columns": columns,
        }
    except Exception as e:
        return {
            "status": "error",
            "database_url_masked": masked_url,
            "raw_database_url_masked": raw_masked,
            "error": str(e),
            "error_type": type(e).__name__,
            "columns": [],
        }
