from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
from typing import Optional

CENTRAL_TZ = ZoneInfo("America/Chicago")

def get_central_now() -> datetime:
    """Get current datetime in Central Time"""
    return datetime.now(CENTRAL_TZ)

def get_central_today_range() -> tuple[datetime, datetime]:
    """Get start and end datetime for today in Central Time"""
    now = get_central_now()
    # Start of day in Central Time
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # End of day in Central Time
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Convert to UTC for API calls
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    
    return start_utc, end_utc

def parse_utc_datetime(datetime_str: str) -> datetime:
    """Parse UTC datetime string to datetime object and convert to Central Time"""
    # Replace 'Z' with '+00:00' for ISO format compatibility
    if datetime_str.endswith('Z'):
        datetime_str = datetime_str[:-1] + '+00:00'
    # Parse the datetime and convert to Central Time
    utc_dt = datetime.fromisoformat(datetime_str)
    return utc_dt.astimezone(CENTRAL_TZ)

def format_utc_datetime(dt: datetime) -> str:
    """Format datetime object to UTC ISO format string"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CENTRAL_TZ)
    # Convert to UTC before formatting
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.isoformat() 