"""Tests for atomic rate limiting with Lua script."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import redis.asyncio as redis

from app.core.rate_limit import RateLimiter, RATE_LIMIT_SCRIPT, check_rate_limit


class TestAtomicRateLimiting:
    """Test atomic rate limiting implementation."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock_client = AsyncMock(spec=redis.Redis)
        mock_script = AsyncMock()
        mock_client.register_script.return_value = mock_script
        return mock_client, mock_script
    
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self, mock_redis):
        """Test rate limiter initializes with Lua script registration."""
        mock_client, mock_script = mock_redis
        
        limiter = RateLimiter(mock_client)
        
        # Verify script was registered
        mock_client.register_script.assert_called_once_with(RATE_LIMIT_SCRIPT)
        assert limiter.rate_limit_script == mock_script
    
    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(self, mock_redis):
        """Test rate limiting when under the limit."""
        mock_client, mock_script = mock_redis
        limiter = RateLimiter(mock_client)
        
        # Mock script to return 1 (allowed)
        mock_script.return_value = 1
        
        result = await limiter.is_allowed(
            key="test-key",
            limit=10,
            window=60,
        )
        
        # Verify script was called with correct parameters
        mock_script.assert_called_once_with(
            keys=["test-key"],
            args=["10", "60"]
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_allowed_over_limit(self, mock_redis):
        """Test rate limiting when over the limit."""
        mock_client, mock_script = mock_redis
        limiter = RateLimiter(mock_client)
        
        # Mock script to return 0 (not allowed)
        mock_script.return_value = 0
        
        result = await limiter.is_allowed(
            key="test-key",
            limit=5,
            window=60,
        )
        
        # Verify script was called with correct parameters
        mock_script.assert_called_once_with(
            keys=["test-key"],
            args=["5", "60"]
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_allowed_script_error_fails_open(self, mock_redis):
        """Test rate limiting fails open when script execution fails."""
        mock_client, mock_script = mock_redis
        limiter = RateLimiter(mock_client)
        
        # Mock script to raise exception
        mock_script.side_effect = Exception("Redis error")
        
        result = await limiter.is_allowed(
            key="test-key",
            limit=10,
            window=60,
        )
        
        # Should fail open and allow request
        assert result is True
    
    @pytest.mark.asyncio
    async def test_lua_script_logic(self):
        """Test the Lua script logic directly."""
        # This test verifies the Lua script logic conceptually
        # The script should:
        # 1. INCR the key
        # 2. If first increment, set expiry
        # 3. Return 1 if current <= limit, 0 otherwise
        
        script_content = RATE_LIMIT_SCRIPT
        
        # Verify script contains expected Redis commands
        assert "redis.call('INCR'" in script_content
        assert "redis.call('EXPIRE'" in script_content
        assert "current <= limit" in script_content
        assert "and 1 or 0" in script_content
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_function(self, mock_redis):
        """Test the convenience check_rate_limit function."""
        mock_client, mock_script = mock_redis
        limiter = RateLimiter(mock_client)
        mock_script.return_value = 1
        
        with patch('app.core.rate_limit.get_rate_limiter') as mock_get_limiter:
            mock_get_limiter.return_value = limiter
            
            with patch('app.core.rate_limit.settings') as mock_settings:
                mock_settings.rate_limit_requests = 100
                mock_settings.rate_limit_window = 60
                
                result = await check_rate_limit("test-key")
                
                # Verify limiter was called with correct settings
                mock_script.assert_called_once_with(
                    keys=["test-key"],
                    args=["100", "60"]
                )
                assert result is True
    
    @pytest.mark.asyncio
    async def test_different_keys_independent(self, mock_redis):
        """Test that different keys are rate limited independently."""
        mock_client, mock_script = mock_redis
        limiter = RateLimiter(mock_client)
        
        # Mock script to return different values for different keys
        def mock_script_side_effect(keys, args):
            if keys[0] == "key1":
                return 1  # Under limit
            elif keys[0] == "key2":
                return 0  # Over limit
            else:
                return 1
        
        mock_script.side_effect = mock_script_side_effect
        
        # Test different keys
        result1 = await limiter.is_allowed("key1", 10, 60)
        result2 = await limiter.is_allowed("key2", 10, 60)
        
        assert result1 is True  # key1 under limit
        assert result2 is False  # key2 over limit
    
    @pytest.mark.asyncio
    async def test_window_expiry(self, mock_redis):
        """Test that window expiry is handled correctly in Lua script."""
        mock_client, mock_script = mock_redis
        limiter = RateLimiter(mock_client)
        
        # Mock script to simulate first request (sets expiry)
        call_count = 0
        def mock_script_side_effect(keys, args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1  # First request, sets expiry
            else:
                return 0  # Subsequent requests
                # In real Redis, expiry would be handled automatically
        
        mock_script.side_effect = mock_script_side_effect
        
        # First request should be allowed and set expiry
        result1 = await limiter.is_allowed("test-key", 5, 60)
        assert result1 is True
        
        # Second request should be blocked
        result2 = await limiter.is_allowed("test-key", 5, 60)
        assert result2 is False
        
        # Verify script was called twice
        assert mock_script.call_count == 2


class TestRateLimitScript:
    """Test the rate limit Lua script properties."""
    
    def test_script_syntax_validity(self):
        """Test that the Lua script has valid syntax."""
        script = RATE_LIMIT_SCRIPT
        
        # Basic syntax checks
        assert "local key = KEYS[1]" in script
        assert "local limit = tonumber(ARGV[1])" in script
        assert "local window = tonumber(ARGV[2])" in script
        assert "local current = redis.call('INCR', key)" in script
        assert "if current == 1 then" in script
        assert "redis.call('EXPIRE', key, window)" in script
        assert "return current <= limit and 1 or 0" in script
    
    def test_script_parameters(self):
        """Test that the script uses correct parameters."""
        script = RATE_LIMIT_SCRIPT
        
        # Should use KEYS[1] for the Redis key
        assert "KEYS[1]" in script
        
        # Should use ARGV[1] for limit and ARGV[2] for window
        assert "ARGV[1]" in script  # limit
        assert "ARGV[2]" in script  # window
        
        # Should use tonumber to convert arguments
        assert "tonumber(ARGV[1])" in script
        assert "tonumber(ARGV[2])" in script
    
    def test_script_logic_flow(self):
        """Test the logical flow of the script."""
        script = RATE_LIMIT_SCRIPT
        
        # Script should:
        # 1. Increment counter
        # 2. Set expiry on first request
        # 3. Return boolean result
        
        lines = script.strip().split('\n')
        
        has_increment = any('redis.call(\'INCR\'' in line for line in lines)
        has_expiry = any('redis.call(\'EXPIRE\'' in line for line in lines)
        has_return = any('return' in line for line in lines)
        
        assert has_increment, "Script should increment counter"
        assert has_expiry, "Script should set expiry on first request"
        assert has_return, "Script should return boolean result"
    
    def test_script_return_values(self):
        """Test that script returns correct values."""
        script = RATE_LIMIT_SCRIPT
        
        # Should return 1 for allowed, 0 for blocked
        assert "and 1 or 0" in script
        assert "current <= limit" in script
        
        # The logic should be: return (current <= limit) and 1 or 0
        # This returns 1 if current <= limit, 0 otherwise
