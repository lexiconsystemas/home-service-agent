"""Test client API key extraction and verification."""

import pytest

from app.services.auth_service import AuthService


class TestClientApiKeyExtraction:
    """Test client API key format and extraction."""
    
    def test_api_key_generation_with_client_id(self):
        """Test that API key generation includes client_id."""
        client_id = "test-client-123"
        
        # Generate API key
        api_key = AuthService.generate_client_api_key(client_id)
        
        # Verify format
        assert api_key.startswith("lexicon_client_")
        assert client_id in api_key
        assert api_key.count("_") >= 3  # lexicon_client_{client_id}_{token}
        
        # Verify different each time
        api_key2 = AuthService.generate_client_api_key(client_id)
        assert api_key != api_key2
        assert client_id in api_key2
    
    def test_api_key_extraction_valid_format(self):
        """Test extraction of client_id from valid API key format."""
        api_key = "lexicon_client_test-client-123_abc123def456"
        
        # Extract client_id
        extracted_client_id = AuthService.extract_client_id_from_api_key(api_key)
        
        # Should extract correctly
        assert extracted_client_id == "test-client-123"
    
    def test_api_key_extraction_invalid_format(self):
        """Test extraction returns None for invalid formats."""
        invalid_keys = [
            "invalid_key",
            "lexicon_client_",
            "lexicon_client_abc",  # Missing token
            "client_test-token",  # Wrong prefix
            "LEXICON_CLIENT_test-token",  # Wrong case
            "",  # Empty
            "lexicon_client_test_token_extra_part",  # Too many parts
        ]
        
        for invalid_key in invalid_keys:
            extracted_client_id = AuthService.extract_client_id_from_api_key(invalid_key)
            assert extracted_client_id is None
    
    def test_api_key_extraction_edge_cases(self):
        """Test edge cases for client_id extraction."""
        # Client ID with special characters
        api_key = "lexicon_client_test-client_123_abc123"
        extracted = AuthService.extract_client_id_from_api_key(api_key)
        assert extracted == "test-client_123"
        
        # Client ID with numbers only
        api_key = "lexicon_client_12345_abc123"
        extracted = AuthService.extract_client_id_from_api_key(api_key)
        assert extracted == "12345"
        
        # Long client ID
        long_client_id = "very-long-client-identifier-with-many-parts"
        api_key = AuthService.generate_client_api_key(long_client_id)
        extracted = AuthService.extract_client_id_from_api_key(api_key)
        assert extracted == long_client_id
    
    def test_api_key_hashing_and_verification(self):
        """Test that API key hashing and verification works."""
        api_key = AuthService.generate_client_api_key("test-client")
        
        # Hash the API key
        hashed_key = AuthService.hash_api_key(api_key)
        
        # Verify the hash is consistent
        hashed_key2 = AuthService.hash_api_key(api_key)
        assert hashed_key == hashed_key2
        
        # Verify correct key passes verification
        assert AuthService.verify_api_key(api_key, hashed_key) is True
        
        # Verify incorrect key fails verification
        assert AuthService.verify_api_key("wrong_key", hashed_key) is False
    
    def test_api_key_format_consistency(self):
        """Test that generated keys follow expected format consistently."""
        client_ids = ["client1", "test-client", "client_123", "Client-ABC"]
        
        for client_id in client_ids:
            api_key = AuthService.generate_client_api_key(client_id)
            extracted = AuthService.extract_client_id_from_api_key(api_key)
            
            # Should round-trip correctly
            assert extracted == client_id
            
            # Should be verifiable
            hashed = AuthService.hash_api_key(api_key)
            assert AuthService.verify_api_key(api_key, hashed) is True
    
    def test_api_key_security_properties(self):
        """Test that API keys have good security properties."""
        client_id = "test-client"
        
        # Generate multiple keys
        keys = [AuthService.generate_client_api_key(client_id) for _ in range(10)]
        
        # All should be different
        assert len(set(keys)) == 10
        
        # All should contain client_id
        for key in keys:
            assert client_id in key
            assert key.startswith("lexicon_client_")
        
        # All should be reasonably long
        for key in keys:
            assert len(key) > 40  # lexicon_client_{client_id}_{32-char token}
        
        # All should be URL-safe
        for key in keys:
            # Should not contain spaces or special characters that need encoding
            assert " " not in key
            assert "\n" not in key
            assert "\r" not in key
