"""Authentication service for client API keys and multi-tenant safety."""

import hashlib
import secrets
from typing import Any

import structlog

from app.core.errors import LexiconError

logger = structlog.get_logger()


class AuthService:
    """Service for handling authentication and authorization."""
    
    @staticmethod
    def generate_client_api_key(client_id: str) -> str:
        """Generate a secure client API key with embedded client ID."""
        return f"lexicon_client_{client_id}_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash."""
        return AuthService.hash_api_key(api_key) == hashed_key
    
    @staticmethod
    def extract_client_id_from_api_key(api_key: str) -> str | None:
        """Extract client ID from API key format."""
        # API key format: lexicon_client_{client_id}_{random_token}
        # The random token is 43 chars from token_urlsafe(32)
        if api_key.startswith("lexicon_client_"):
            # Remove the prefix
            remainder = api_key[len("lexicon_client_"):]
            # The last underscore separates client_id from the random token
            # The random token is 43 characters (base64 encoded 32 bytes)
            last_underscore = remainder.rfind("_")
            if last_underscore > 0:
                return remainder[:last_underscore]
        return None
    
    @staticmethod
    def validate_client_access(
        client_id: str,
        request_client_id: str | None,
        is_admin: bool = False,
    ) -> bool:
        """
        Validate that a client can access their own resources.
        
        Args:
            client_id: The client ID being accessed
            request_client_id: The client ID from the request
            is_admin: Whether the request is from an admin
            
        Returns:
            True if access is allowed
        """
        # Admin can access any client
        if is_admin:
            return True
        
        # Client can only access their own resources
        return client_id == request_client_id
    
    @staticmethod
    def sanitize_client_data(
        client_data: dict[str, Any],
        requesting_client_id: str | None,
        is_admin: bool = False,
    ) -> dict[str, Any]:
        """
        Sanitize client data based on requester permissions.
        
        Args:
            client_data: Raw client data
            requesting_client_id: Client ID making the request
            is_admin: Whether the request is from an admin
            
        Returns:
            Sanitized client data
        """
        client_id = client_data.get("client_id")
        
        # Check access permissions
        if not AuthService.validate_client_access(client_id, requesting_client_id, is_admin):
            raise LexiconError(
                "Access denied",
                error_code="ACCESS_DENIED",
                status_code=403,
            )
        
        # For client requests, only return safe fields
        if not is_admin:
            safe_fields = [
                "client_id",
                "to_number",
                "greeting_message",
                "delivery_channels",
                "message_templates",
                "followup_flags",
                "version",
                "updated_at",
            ]
            return {k: v for k, v in client_data.items() if k in safe_fields}
        
        # Admin gets all fields
        return client_data
    
    @staticmethod
    def validate_webhook_signature(
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """
        Validate webhook signature for security.
        
        Args:
            payload: Raw request payload
            signature: Signature from request header
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        import hmac
        
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        # Use secure comparison
        return hmac.compare_digest(expected_signature, signature)
    
    @staticmethod
    def generate_webhook_signature(
        payload: bytes,
        secret: str,
    ) -> str:
        """
        Generate webhook signature for outgoing requests.
        
        Args:
            payload: Raw request payload
            secret: Webhook secret
            
        Returns:
            Hex signature
        """
        import hmac
        
        return hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
