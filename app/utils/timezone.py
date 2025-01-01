from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
from typing import Optional
from app.logger import logger

CENTRAL_TZ = ZoneInfo("America/Chicago")

def get_central_now() -> datetime:
    """Get current datetime in Central Time"""
    utc_now = datetime.now(timezone.utc)
    central_now = utc_now.astimezone(CENTRAL_TZ)
    logger.debug(f"Current time - UTC: {utc_now}, Central: {central_now}")
    return central_now

def get_central_today_range() -> tuple[datetime, datetime]:
    """Get start and end datetime for today in Central Time"""
    logger.info("=== Calculating today's date range ===")
    now = get_central_now()
    logger.info(f"Current time (Central): {now}")
    
    # Start of day in Central Time
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # End of day in Central Time
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    logger.info(f"Date range in Central:")
    logger.info(f"- Start: {start}")
    logger.info(f"- End: {end}")
    
    # Convert to UTC for API calls
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    
    logger.info(f"Date range in UTC:")
    logger.info(f"- Start: {start_utc}")
    logger.info(f"- End: {end_utc}")
    logger.info("=== Completed date range calculation ===")
    
    return start_utc, end_utc

def parse_utc_datetime(datetime_str: str) -> datetime:
    """Parse UTC datetime string to datetime object and convert to Central Time"""
    logger.debug(f"Parsing UTC datetime string: {datetime_str}")
    # Replace 'Z' with '+00:00' for ISO format compatibility
    if datetime_str.endswith('Z'):
        datetime_str = datetime_str[:-1] + '+00:00'
        logger.debug(f"Converted Z timezone to +00:00: {datetime_str}")
    
    # Parse the datetime and convert to Central Time
    utc_dt = datetime.fromisoformat(datetime_str)
    central_dt = utc_dt.astimezone(CENTRAL_TZ)
    logger.debug(f"Parsed datetime - UTC: {utc_dt}, Central: {central_dt}")
    return central_dt

def format_utc_datetime(dt: datetime) -> str:
    """Format datetime object to UTC ISO format string"""
    logger.debug(f"Formatting datetime: {dt}")
    if dt.tzinfo is None:
        logger.debug("No timezone found, assuming Central")
        dt = dt.replace(tzinfo=CENTRAL_TZ)
    # Convert to UTC before formatting
    utc_dt = dt.astimezone(timezone.utc)
    formatted = utc_dt.isoformat()
    logger.debug(f"Formatted UTC datetime: {formatted}")
    return formatted 