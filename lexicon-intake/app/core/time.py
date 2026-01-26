"""Time utilities."""

import datetime
from typing import Any

from zoneinfo import ZoneInfo


def utc_now() -> datetime.datetime:
    """Get current UTC time."""
    return datetime.datetime.now(ZoneInfo("UTC"))


def format_timestamp(dt: datetime.datetime) -> str:
    """Format datetime to ISO 8601 string."""
    return dt.isoformat()


def parse_timestamp(timestamp: str) -> datetime.datetime:
    """Parse ISO 8601 timestamp to datetime."""
    return datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
