"""Security utilities."""

import hashlib
import hmac
from typing import Any


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)


def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number to E.164 format."""
    # Remove all non-digit characters
    digits_only = "".join(filter(str.isdigit, phone))
    
    # Basic validation for US numbers
    if len(digits_only) == 10:
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith("1"):
        return f"+{digits_only}"
    elif len(digits_only) >= 10 and digits_only.startswith("+"):
        return f"+{digits_only[1:]}"
    
    return phone  # Return original if can't normalize


def sanitize_input(text: str) -> str:
    """Basic input sanitization."""
    if not text:
        return ""
    
    # Remove null bytes and control characters
    sanitized = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")
    
    # Trim whitespace
    return sanitized.strip()
