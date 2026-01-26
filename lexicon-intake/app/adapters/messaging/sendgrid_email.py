"""SendGrid email adapter for sending emails."""

import asyncio
from typing import Any

import httpx
import structlog

from app.settings import settings

logger = structlog.get_logger()


class SendGridEmailAdapter:
    """Adapter for sending emails via SendGrid."""
    
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_url = "https://api.sendgrid.com/v3/mail/send"
        self.headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        }
    
    async def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        max_retries: int = 3,
    ) -> tuple[bool, str | None, int | None]:
        """
        Send email via SendGrid.
        
        Args:
            to_address: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (success: bool, error_message: str | None, status_code: int | None)
        """
        if not all([settings.sendgrid_api_key, settings.email_from]):
            error_msg = "SendGrid configuration missing"
            logger.error("SendGrid email failed", error=error_msg)
            return False, error_msg, None
        
        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_address}],
                    "subject": subject,
                }
            ],
            "from": {"email": settings.email_from},
            "content": [
                {
                    "type": "text/plain",
                    "value": body,
                }
            ],
        }
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    "Sending email via SendGrid",
                    to_address=to_address,
                    subject=subject,
                    attempt=attempt + 1,
                )
                
                response = await self.client.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                )
                
                # SendGrid returns 202 Accepted for successful delivery
                if response.status_code == 202:
                    logger.info(
                        "Email sent successfully",
                        to_address=to_address,
                        message_id=response.headers.get("X-Message-Id"),
                    )
                    return True, None, response.status_code
                
                else:
                    # Error response
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("errors", [{}])[0].get("message", f"HTTP {response.status_code}")
                    
                    logger.warning(
                        "Email delivery failed",
                        to_address=to_address,
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
                    "Email network error",
                    to_address=to_address,
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
