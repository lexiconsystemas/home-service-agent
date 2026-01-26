"""Application settings using Pydantic Settings."""

from typing import Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://lexicon:lexicon@localhost:5432/lexicon_intake",
        description="Database connection URL",
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    
    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=False, description="Enable auto-reload")
    
    # Security
    secret_key: str = Field(
        default="change-in-production",
        description="Application secret key",
    )
    webhook_signing_secret: str = Field(
        default="change-in-production",
        description="Webhook signature secret",
    )
    admin_api_key: str = Field(
        default="change-in-production",
        description="Admin API key for configuration endpoints",
    )
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    
    # CORS (disabled by default for security)
    cors_enabled: bool = Field(default=False, description="Enable CORS middleware")
    cors_origins: list[str] | None = Field(default=None, description="CORS allowed origins")
    
    # Twilio SMS
    twilio_account_sid: str | None = Field(
        default=None,
        description="Twilio account SID",
    )
    twilio_auth_token: str | None = Field(
        default=None,
        description="Twilio auth token",
    )
    twilio_from_number: str | None = Field(
        default=None,
        description="Twilio from number",
    )
    
    # SendGrid Email
    sendgrid_api_key: str | None = Field(
        default=None,
        description="SendGrid API key",
    )
    email_from: str | None = Field(
        default=None,
        description="From email address",
    )
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
