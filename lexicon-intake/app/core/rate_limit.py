"""Redis-based rate limiting with atomic Lua script."""

import asyncio
from typing import Any

import redis.asyncio as redis
import structlog

from app.settings import settings

logger = structlog.get_logger()

# Atomic rate limiting Lua script
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end

return current <= limit and 1 or 0
"""


class RateLimiter:
    """Redis-based rate limiter using atomic Lua script."""
    
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client
        # Register the Lua script
        self.rate_limit_script = self.redis.register_script(RATE_LIMIT_SCRIPT)
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
        """
        Check if request is allowed based on rate limit using atomic Lua script.
        
        Args:
            key: Rate limit key (e.g., IP address)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            True if allowed, False otherwise
        """
        try:
            # Execute atomic Lua script
            result = await self.rate_limit_script(
                keys=[key],
                args=[str(limit), str(window)]
            )
            return result == 1
        except Exception as e:
            logger.error(
                "Rate limit check failed",
                key=key,
                limit=limit,
                window=window,
                error=str(e),
                exc_info=True,
            )
            # Fail open - allow request if rate limiting fails
            return True


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


async def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        redis_client = redis.from_url(settings.redis_url)
        _rate_limiter = RateLimiter(redis_client)
    
    return _rate_limiter


async def check_rate_limit(key: str) -> bool:
    """Check rate limit for given key."""
    limiter = await get_rate_limiter()
    return await limiter.is_allowed(
        key=key,
        limit=settings.rate_limit_requests,
        window=settings.rate_limit_window,
    )
