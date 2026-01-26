"""Twilio SMS adapter for sending SMS messages."""

import asyncio
from typing import Any

import httpx
import structlog

from app.settings import settings

logger = structlog.get_logger()


class TwilioSMSAdapter:
    """Adapter for sending SMS messages via Twilio."""
    
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}"
        self.auth = (settings.twilio_account_sid, settings.twilio_auth_token)
    
    async def send_sms(
        self,
        to_number: str,
        message: str,
        max_retries: int = 3,
    ) -> tuple[bool, str | None, int | None]:
        """
        Send SMS message via Twilio.
        
        Args:
            to_number: Recipient phone number in E.164 format
            message: SMS message content (max 480 chars)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (success: bool, error_message: str | None, status_code: int | None)
        """
        if not all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number]):
            error_msg = "Twilio configuration missing"
            logger.error("Twilio SMS failed", error=error_msg)
            return False, error_msg, None
        
        # Truncate message if too long
        if len(message) > 480:
            message = message[:477] + "..."
            logger.warning("SMS message truncated", original_length=len(message))
        
        payload = {
            "From": settings.twilio_from_number,
            "To": to_number,
            "Body": message,
        }
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    "Sending SMS via Twilio",
                    to_number=to_number,
                    attempt=attempt + 1,
                    message_length=len(message),
                )
                
                response = await self.client.post(
                    f"{self.base_url}/Messages.json",
                    data=payload,
                    auth=self.auth,
                )
                
                if response.status_code == 201:
                    # Success
                    logger.info(
                        "SMS sent successfully",
                        to_number=to_number,
                        message_sid=response.json().get("sid"),
                    )
                    return True, None, response.status_code
                
                else:
                    # Error response
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("message", f"HTTP {response.status_code}")
                    
                    logger.warning(
                        "SMS delivery failed",
                        to_number=to_number,
                        status_code=response.status_code,
                        error_message=error_message,
                        attempt=attempt + 1,
                    )
                    
                    # Don't retry client errors (except 429)
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        return False, error_message, response.status_code
                    
                    # Retry on rate limiting and server errors
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        return False, error_message, response.status_code
            
            except httpx.RequestError as e:
                logger.warning(
                    "SMS network error",
                    to_number=to_number,
                    error=str(e),
                    attempt=attempt + 1,
                )
                
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return False, str(e), None
        
        return False, "Max retries exceeded", None
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
