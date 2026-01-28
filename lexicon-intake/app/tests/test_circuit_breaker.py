"""Tests for circuit breaker implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import redis.asyncio as redis

from app.core.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitOpenError,
    get_circuit_breaker, with_circuit_breaker
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return AsyncMock(spec=redis.Redis)
    
    @pytest.fixture
    def circuit_breaker(self, mock_redis):
        """Create circuit breaker instance."""
        return CircuitBreaker(
            service_name="test-service",
            failure_threshold=3,
            recovery_timeout=60,
            redis_client=mock_redis,
        )
    
    @pytest.mark.asyncio
    async def test_initial_state_closed(self, circuit_breaker, mock_redis):
        """Test circuit starts in CLOSED state."""
        mock_redis.get.return_value = None
        
        state = await circuit_breaker.get_state()
        
        assert state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_successful_call_resets_failures(self, circuit_breaker, mock_redis):
        """Test successful call resets failure count."""
        # Set initial failures
        mock_redis.get.return_value = b"2"
        
        # Mock successful function
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        
        assert result == "success"
        mock_redis.set.assert_any_call("circuit_breaker:test-service:failures", "0", ex=3600)
    
    @pytest.mark.asyncio
    async def test_failure_increments_count(self, circuit_breaker, mock_redis):
        """Test failed call increments failure count."""
        mock_redis.get.return_value = b"1"
        
        # Mock failing function
        async def fail_func():
            raise Exception("Service error")
        
        with pytest.raises(Exception, match="Service error"):
            await circuit_breaker.call(fail_func)
        
        # Should increment failure count
        mock_redis.set.assert_any_call("circuit_breaker:test-service:failures", "2", ex=3600)
    
    @pytest.mark.asyncio
    async def test_circuit_opens_on_threshold(self, circuit_breaker, mock_redis):
        """Test circuit opens after failure threshold is reached."""
        mock_redis.get.return_value = b"2"  # One short of threshold
        
        async def fail_func():
            raise Exception("Service error")
        
        # This failure should open the circuit
        with pytest.raises(Exception, match="Service error"):
            await circuit_breaker.call(fail_func)
        
        # Check circuit was opened
        mock_redis.set.assert_any_call("circuit_breaker:test-service:state", "open", ex=3600)
    
    @pytest.mark.asyncio
    async def test_open_circuit_blocks_calls(self, circuit_breaker, mock_redis):
        """Test open circuit blocks calls with CircuitOpenError."""
        # Mock circuit state as OPEN
        mock_redis.get.return_value = b"open"
        
        async def any_func():
            return "should not execute"
        
        with pytest.raises(CircuitOpenError, match="Circuit breaker OPEN"):
            await circuit_breaker.call(any_func)
    
    @pytest.mark.asyncio
    async def test_half_open_state_transition(self, circuit_breaker, mock_redis):
        """Test transition from OPEN to HALF_OPEN after timeout."""
        import time
        
        # Mock circuit as OPEN with recent failure
        mock_redis.get.side_effect = [
            b"open",  # First call returns OPEN state
            str(time.time() - 70).encode(),  # Last failure was 70 seconds ago
        ]
        
        state = await circuit_breaker.get_state()
        
        # Should be HALF_OPEN since recovery timeout passed
        assert state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, circuit_breaker, mock_redis):
        """Test successful call in HALF_OPEN closes circuit."""
        # Mock circuit as HALF_OPEN
        mock_redis.get.return_value = None  # No state, will check timeout
        
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        
        assert result == "success"
        # Circuit should be closed after success
        mock_redis.set.assert_any_call("circuit_breaker:test-service:state", "closed", ex=3600)
    
    @pytest.mark.asyncio
    async def test_no_redis_fails_closed(self, circuit_breaker):
        """Test circuit breaker without Redis fails closed."""
        circuit_breaker_no_redis = CircuitBreaker(
            service_name="test-service",
            failure_threshold=3,
            recovery_timeout=60,
            redis_client=None,
        )
        
        async def any_func():
            return "success"
        
        # Should work normally without Redis
        result = await circuit_breaker_no_redis.call(any_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_redis_errors_fail_closed(self, circuit_breaker, mock_redis):
        """Test Redis errors cause circuit to fail closed."""
        mock_redis.get.side_effect = Exception("Redis error")
        
        async def any_func():
            return "success"
        
        # Should work normally despite Redis errors
        result = await circuit_breaker.call(any_func)
        assert result == "success"
    
    def test_get_circuit_breaker_singleton(self):
        """Test circuit breaker singleton pattern."""
        with patch('app.core.circuit_breaker.redis.from_url') as mock_redis_from_url:
            mock_redis = AsyncMock()
            mock_redis_from_url.return_value = mock_redis
            
            async def test_get():
                breaker1 = await get_circuit_breaker("test-service")
                breaker2 = await get_circuit_breaker("test-service")
                
                assert breaker1 is breaker2
                assert breaker1.service_name == "test-service"
            
            import asyncio
            asyncio.run(test_get())
    
    @pytest.mark.asyncio
    async def test_with_circuit_breaker_decorator(self):
        """Test circuit breaker decorator."""
        with patch('app.core.circuit_breaker.get_circuit_breaker') as mock_get_breaker:
            mock_breaker = AsyncMock()
            mock_breaker.call.return_value = "decorated result"
            mock_get_breaker.return_value = mock_breaker
            
            @with_circuit_breaker("test-service")
            async def test_func():
                return "original result"
            
            result = await test_func()
            
            assert result == "decorated result"
            mock_breaker.call.assert_called_once_with(test_func)


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete circuit breaker lifecycle."""
        mock_redis = AsyncMock()
        circuit_breaker = CircuitBreaker(
            service_name="integration-test",
            failure_threshold=2,
            recovery_timeout=1,  # Short timeout for testing
            redis_client=mock_redis,
        )
        
        # Start with no failures
        mock_redis.get.return_value = None
        
        # First successful call
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        
        # First failure
        mock_redis.get.return_value = b"0"
        async def fail_func():
            raise Exception("Service error")
        
        with pytest.raises(Exception):
            await circuit_breaker.call(fail_func)
        
        # Second failure should open circuit
        mock_redis.get.return_value = b"1"
        with pytest.raises(Exception):
            await circuit_breaker.call(fail_func)
        
        # Circuit should now be open
        mock_redis.get.return_value = b"open"
        with pytest.raises(CircuitOpenError):
            await circuit_breaker.call(success_func)
        
        # After timeout, should transition to HALF_OPEN
        import time
        mock_redis.get.side_effect = [
            b"open",
            str(time.time() - 2).encode(),  # 2 seconds ago (past 1 second timeout)
        ]
        
        state = await circuit_breaker.get_state()
        assert state == CircuitState.HALF_OPEN
        
        # Success in HALF_OPEN should close circuit
        mock_redis.get.side_effect = None
        mock_redis.get.return_value = None
        result = await circuit_breaker.call(success_func)
        assert result == "success"
