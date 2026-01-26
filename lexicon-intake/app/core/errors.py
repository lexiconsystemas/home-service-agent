"""Custom exceptions and error handling."""

from typing import Any

from fastapi import HTTPException, status


class LexiconException(Exception):
    """Base exception for Lexicon application."""
    
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class DuplicateCallError(LexiconException):
    """Raised when a duplicate call event is received."""
    
    pass


class RateLimitExceededError(LexiconException):
    """Raised when rate limit is exceeded."""
    
    pass


class ClientNotFoundError(LexiconException):
    """Raised when client configuration is not found."""
    
    pass


class DeliveryError(LexiconException):
    """Raised when webhook delivery fails."""
    
    pass


class ValidationError(LexiconException):
    """Raised when validation fails."""
    
    pass


def http_exception_from_lexicon(exc: LexiconException) -> HTTPException:
    """Convert LexiconException to HTTPException."""
    if isinstance(exc, DuplicateCallError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_call", "message": exc.message},
        )
    elif isinstance(exc, RateLimitExceededError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limit_exceeded", "message": exc.message},
        )
    elif isinstance(exc, ClientNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "client_not_found", "message": exc.message},
        )
    elif isinstance(exc, ValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": exc.message},
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Internal server error"},
        )
