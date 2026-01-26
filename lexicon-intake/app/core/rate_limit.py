"""Redis-based rate limiting."""

import asyncio
from typing import Any

import redis.asyncio as redis
import structlog

from app.settings import settings

logger = structlog.get_logger()


class RateLimiter:
    """Redis-based rate limiter using sliding window."""
    
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Rate limit key (e.g., IP address)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            True if allowed, False otherwise
        """
        current_time = asyncio.get_event_loop().time()
        window_start = current_time - window
        
        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current_requests = await self.redis.zcard(key)
        
        if current_requests >= limit:
            return False
        
        # Add current request
        await self.redis.zadd(key, {str(current_time): current_time})
        await self.redis.expire(key, window)
        
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
