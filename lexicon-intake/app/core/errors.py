"""Custom exceptions and HTTP error handling."""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class LexiconError(Exception):
    """Base exception for Lexicon application."""
    
    def __init__(self, message: str, error_code: str | None = None) -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ClientNotFoundError(LexiconError):
    """Exception raised when client configuration is not found."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, "CLIENT_NOT_FOUND")


class ValidationError(LexiconError):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR")


class RoutingError(LexiconError):
    """Exception raised when routing configuration is invalid."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, "ROUTING_ERROR")


class DeliveryError(LexiconError):
    """Exception raised when delivery fails."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, "DELIVERY_ERROR")


class DuplicateCallError(LexiconError):
    """Exception raised when a duplicate call is detected."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, "DUPLICATE_CALL")


class RateLimitExceededError(LexiconError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, "RATE_LIMIT_EXCEEDED")


async def lexicon_exception_handler(request: Request, exc: LexiconError) -> JSONResponse:
    """
    Global exception handler for Lexicon errors.
    
    Returns structured error responses with error codes.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "Lexicon error occurred",
        request_id=request_id,
        error_code=exc.error_code,
        error_message=exc.message,
        exc_info=True,
    )
    
    # Determine HTTP status code based on error type
    if isinstance(exc, ClientNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, RoutingError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, DeliveryError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, DuplicateCallError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, RateLimitExceededError):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code or "INTERNAL_ERROR",
                "message": exc.message,
                "request_id": request_id,
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unexpected errors.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "Unexpected error occurred",
        request_id=request_id,
        error_type=type(exc).__name__,
        error_message=str(exc),
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "request_id": request_id,
            }
        },
    )
