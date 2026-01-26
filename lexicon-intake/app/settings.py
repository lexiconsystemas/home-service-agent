"""Application settings using Pydantic Settings."""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
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
        description="Secret key for signing",
    )
    webhook_signing_secret: str = Field(
        default="change-in-production",
        description="Secret for webhook signatures",
    )
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    
    def model_post_init(self, __context: Any) -> None:
        """Post-initialization setup."""
        # Convert log level to uppercase for consistency
        self.log_level = self.log_level.upper()


settings = Settings()
