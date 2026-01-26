"""Test Twilio signature verification."""

import pytest
from unittest.mock import AsyncMock, patch

from app.api.routers.sms import verify_twilio_signature


class TestTwilioSignatureVerification:
    """Test Twilio webhook signature verification."""
    
    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self):
        """Test that valid Twilio signatures are accepted."""
        # Mock request with valid signature
        mock_request = AsyncMock()
        mock_request.headers = {
            "X-Twilio-Signature": "valid_signature"
        }
        mock_request.url = "https://example.com/sms/inbound"
        mock_request.body.return_value = b"From=+1555000000&Body=1"
        
        # Mock Twilio RequestValidator
        with patch('app.api.routers.sms.RequestValidator') as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate.return_value = True
            
            # Verify signature
            result = await verify_twilio_signature(mock_request)
            
            # Should return True for valid signature
            assert result is True
            mock_validator.validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self):
        """Test that invalid Twilio signatures are rejected."""
        # Mock request with invalid signature
        mock_request = AsyncMock()
        mock_request.headers = {
            "X-Twilio-Signature": "invalid_signature"
        }
        mock_request.url = "https://example.com/sms/inbound"
        mock_request.body.return_value = b"From=+1555000000&Body=1"
        
        # Mock Twilio RequestValidator
        with patch('app.api.routers.sms.RequestValidator') as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate.return_value = False
            
            # Verify signature
            result = await verify_twilio_signature(mock_request)
            
            # Should return False for invalid signature
            assert result is False
            mock_validator.validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_missing_signature_rejected(self):
        """Test that missing signature header is rejected."""
        # Mock request without signature
        mock_request = AsyncMock()
        mock_request.headers = {}
        mock_request.url = "https://example.com/sms/inbound"
        mock_request.body.return_value = b"From=+1555000000&Body=1"
        
        # Verify signature
        result = await verify_twilio_signature(mock_request)
        
        # Should return False for missing signature
        assert result is False
    
    @pytest.mark.asyncio
    async def test_twilio_library_not_installed(self):
        """Test graceful handling when Twilio library is not installed."""
        # Mock request with signature
        mock_request = AsyncMock()
        mock_request.headers = {
            "X-Twilio-Signature": "some_signature"
        }
        mock_request.url = "https://example.com/sms/inbound"
        mock_request.body.return_value = b"From=+1555000000&Body=1"
        
        # Mock ImportError for Twilio library
        with patch('app.api.routers.sms.RequestValidator', side_effect=ImportError("No module named 'twilio'")):
            # Verify signature
            result = await verify_twilio_signature(mock_request)
            
            # Should return False when library not available
            assert result is False
    
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions during verification are handled gracefully."""
        # Mock request with signature
        mock_request = AsyncMock()
        mock_request.headers = {
            "X-Twilio-Signature": "some_signature"
        }
        mock_request.url = "https://example.com/sms/inbound"
        mock_request.body.return_value = b"From=+1555000000&Body=1"
        
        # Mock Twilio RequestValidator that raises exception
        with patch('app.api.routers.sms.RequestValidator') as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate.side_effect = Exception("Unexpected error")
            
            # Verify signature
            result = await verify_twilio_signature(mock_request)
            
            # Should return False on exception
            assert result is False
    
    @pytest.mark.asyncio
    async def test_signature_verification_parameters(self):
        """Test that correct parameters are passed to validator."""
        # Mock request with signature
        mock_request = AsyncMock()
        signature = "test_signature"
        mock_request.headers = {
            "X-Twilio-Signature": signature
        }
        mock_request.url = "https://example.com/sms/inbound"
        body_content = b"From=+1555000000&Body=1"
        mock_request.body.return_value = body_content
        
        # Mock Twilio RequestValidator and settings
        with patch('app.api.routers.sms.RequestValidator') as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate.return_value = True
            
            with patch('app.api.routers.sms.settings') as mock_settings:
                mock_settings.TWILIO_AUTH_TOKEN = "test_token"
                
                # Verify signature
                await verify_twilio_signature(mock_request)
                
                # Verify correct parameters passed to validate
                mock_validator.validate.assert_called_once_with(
                    "https://example.com/sms/inbound",
                    body_content,
                    signature
                )
                mock_validator_class.assert_called_once_with("test_token")
