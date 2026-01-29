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
) -> dict[str, list[str]]:
    """Check database schema - list columns in client_configs table."""
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
            "migration_version": migration_version,
            "columns": columns,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "columns": [],
        }
