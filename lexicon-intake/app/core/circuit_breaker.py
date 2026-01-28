"""Circuit breaker pattern for external service resilience."""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

import redis.asyncio as redis
import structlog

from app.settings import settings

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for external service calls with Redis state storage."""
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        redis_client: Optional[redis.Redis] = None,
    ) -> None:
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.redis = redis_client
        
        # Redis keys
        self.state_key = f"circuit_breaker:{service_name}:state"
        self.failure_count_key = f"circuit_breaker:{service_name}:failures"
        self.last_failure_key = f"circuit_breaker:{service_name}:last_failure"
    
    async def get_state(self) -> CircuitState:
        """Get current circuit state from Redis."""
        if not self.redis:
            # Fallback to in-memory state if no Redis
            return CircuitState.CLOSED
        
        try:
            state_str = await self.redis.get(self.state_key)
            if state_str:
                return CircuitState(state_str.decode())
            
            # Check if we should transition from OPEN to HALF_OPEN
            last_failure = await self.redis.get(self.last_failure_key)
            if last_failure:
                last_failure_time = float(last_failure.decode())
                if time.time() - last_failure_time > self.recovery_timeout:
                    return CircuitState.HALF_OPEN
            
            return CircuitState.CLOSED
        except Exception as e:
            logger.error(
                "Failed to get circuit state",
                service=self.service_name,
                error=str(e),
            )
            return CircuitState.CLOSED  # Fail closed
    
    async def set_state(self, state: CircuitState) -> None:
        """Set circuit state in Redis."""
        if not self.redis:
            return
        
        try:
            await self.redis.set(self.state_key, state.value, ex=3600)  # 1 hour expiry
            logger.info(
                "Circuit state changed",
                service=self.service_name,
                state=state.value,
            )
        except Exception as e:
            logger.error(
                "Failed to set circuit state",
                service=self.service_name,
                state=state.value,
                error=str(e),
            )
    
    async def get_failure_count(self) -> int:
        """Get current failure count from Redis."""
        if not self.redis:
            return 0
        
        try:
            count = await self.redis.get(self.failure_count_key)
            return int(count.decode()) if count else 0
        except Exception as e:
            logger.error(
                "Failed to get failure count",
                service=self.service_name,
                error=str(e),
            )
            return 0
    
    async def set_failure_count(self, count: int) -> None:
        """Set failure count in Redis."""
        if not self.redis:
            return
        
        try:
            await self.redis.set(self.failure_count_key, str(count), ex=3600)
        except Exception as e:
            logger.error(
                "Failed to set failure count",
                service=self.service_name,
                count=count,
                error=str(e),
            )
    
    async def record_success(self) -> None:
        """Record a successful call."""
        current_state = await self.get_state()
        if current_state == CircuitState.HALF_OPEN:
            # Service recovered, close the circuit
            await self.set_state(CircuitState.CLOSED)
            await self.set_failure_count(0)
            logger.info(
                "Circuit closed after successful test",
                service=self.service_name,
            )
        else:
            # Reset failure count on success
            await self.set_failure_count(0)
    
    async def record_failure(self) -> None:
        """Record a failed call."""
        failure_count = await self.get_failure_count() + 1
        await self.set_failure_count(failure_count)
        
        if self.redis:
            await self.redis.set(self.last_failure_key, str(time.time()), ex=3600)
        
        if failure_count >= self.failure_threshold:
            await self.set_state(CircuitState.OPEN)
            logger.warning(
                "Circuit opened due to failures",
                service=self.service_name,
                failure_count=failure_count,
                threshold=self.failure_threshold,
            )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result if allowed
            
        Raises:
            Exception: Original exception or CircuitOpenError
        """
        state = await self.get_state()
        
        if state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit breaker OPEN for {self.service_name}")
        
        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure()
            raise e


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breaker instances
_circuit_breakers: Dict[str, CircuitBreaker] = {}


async def get_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
) -> CircuitBreaker:
    """Get or create circuit breaker instance."""
    if service_name not in _circuit_breakers:
        redis_client = redis.from_url(settings.redis_url)
        _circuit_breakers[service_name] = CircuitBreaker(
            service_name=service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            redis_client=redis_client,
        )
    
    return _circuit_breakers[service_name]


def with_circuit_breaker(service_name: str):
    """Decorator to apply circuit breaker to async functions."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            breaker = await get_circuit_breaker(service_name)
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
