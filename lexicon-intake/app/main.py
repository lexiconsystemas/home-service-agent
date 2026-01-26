"""FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health, calls, admin, metrics, ops, sms
from app.core.logging import setup_logging
from app.core.errors import lexicon_exception_handler, general_exception_handler, LexiconError
from app.settings import settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting Lexicon Intake System")
    yield
    logger.info("Shutting down Lexicon Intake System")


app = FastAPI(
    title="Lexicon Systemas Intake System",
    description="Home Services Intake MVP",
    version="0.3.0",
    lifespan=lifespan,
)

# Add exception handlers
app.add_exception_handler(LexiconError, lexicon_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS middleware - disabled by default for security
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to context and response headers."""
    request_id = str(uuid.uuid4())
    
    # Add to request state for logging
    request.state.request_id = request_id
    
    # Add to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Structured logging middleware."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log request
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        logger.info(
            "Request completed",
            request_id=request_id,
            status_code=response.status_code,
        )
        
        return response
        
    except Exception as e:
        # Log error
        logger.error(
            "Request failed",
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise


# Include routers
app.include_router(health.router, prefix="/healthz", tags=["health"])
app.include_router(calls.router, prefix="/v1/calls", tags=["calls"])
app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
app.include_router(ops.router, tags=["ops"])
app.include_router(sms.router, tags=["sms"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"service": "Lexicon Intake System", "version": "0.3.0"}


if __name__ == "__main__":
    import uvicorn
    
    setup_logging()
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
