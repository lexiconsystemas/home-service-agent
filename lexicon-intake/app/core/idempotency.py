"""Idempotency handling for call events."""

import uuid
from typing import Any

import structlog

from app.db.repos.call_repo import CallRepository
from app.db.session import get_async_session

logger = structlog.get_logger()


class IdempotencyManager:
    """Manages idempotency for call events using call_id."""
    
    @staticmethod
    async def check_and_record_call_id(call_id: str) -> bool:
        """
        Check if call_id has been processed and record it if not.
        
        Args:
            call_id: Unique identifier for the call event
            
        Returns:
            True if call_id is new (not processed), False if duplicate
        """
        async with get_async_session() as session:
            call_repo = CallRepository(session)
            
            # Check if call_id already exists
            existing_call = await call_repo.get_by_call_id(call_id)
            if existing_call:
                logger.info("Duplicate call_id detected", call_id=call_id)
                return False
            
            # Record the call_id
            await call_repo.create_call_record(call_id=call_id)
            logger.info("Call_id recorded", call_id=call_id)
            return True
    
    @staticmethod
    def generate_call_id() -> str:
        """Generate a unique call ID."""
        return str(uuid.uuid4())
