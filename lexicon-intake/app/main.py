"""FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health, calls
from app.core.logging import setup_logging
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
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


# Include routers
app.include_router(health.router, prefix="/healthz", tags=["health"])
app.include_router(calls.router, prefix="/v1/calls", tags=["calls"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"service": "Lexicon Intake System", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    
    setup_logging()
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
