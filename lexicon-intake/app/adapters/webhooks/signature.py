"""Webhook signature verification utilities."""

import hashlib
import hmac
from typing import Any


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """
    Generate HMAC signature for webhook payload.
    
    Args:
        payload: Raw payload bytes
        secret: Secret key for signing
        
    Returns:
        Hexadecimal signature string
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature.
    
    Args:
        payload: Raw payload bytes
        signature: Received signature
        secret: Secret key for verification
        
    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)
