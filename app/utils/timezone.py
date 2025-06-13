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

def convert_utc_to_central(utc_dt: datetime) -> datetime:
    """
    Convert UTC datetime (stored in database) to Central Time for display.
    Handles timezone-naive UTC datetimes from database storage.
    """
    if utc_dt is None:
        return None
    
    # If timezone-naive, assume it's UTC (our database storage format)
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # Convert to Central Time
    central_dt = utc_dt.astimezone(CENTRAL_TZ)
    logger.debug(f"Converted UTC {utc_dt} to Central {central_dt}")
    return central_dt

def convert_central_to_utc(central_dt: datetime) -> datetime:
    """
    Convert Central Time datetime to UTC for database storage.
    Handles DST transitions properly.
    """
    if central_dt is None:
        return None
    
    # If timezone-naive, assume it's Central Time
    if central_dt.tzinfo is None:
        central_dt = central_dt.replace(tzinfo=CENTRAL_TZ)
    
    # Convert to UTC
    utc_dt = central_dt.astimezone(timezone.utc)
    logger.debug(f"Converted Central {central_dt} to UTC {utc_dt}")
    return utc_dt

def get_business_timezone_for_location(location_timezone: str = None) -> ZoneInfo:
    """
    Get the appropriate timezone for a business location.
    If location_timezone is provided, use it; otherwise default to Central.
    """
    if location_timezone:
        try:
            return ZoneInfo(location_timezone)
        except Exception as e:
            logger.warning(f"Invalid timezone '{location_timezone}', falling back to Central: {e}")
    
    return CENTRAL_TZ

def convert_order_time_to_display(order_created_at: datetime, location_timezone: str = None) -> datetime:
    """
    Convert order timestamp from database UTC storage to the appropriate local time for display.
    This ensures orders appear with the correct local time they were actually placed.
    
    Args:
        order_created_at: UTC datetime from database (timezone-naive)
        location_timezone: Optional timezone string from location (e.g., "America/Chicago")
    
    Returns:
        Datetime in the appropriate local timezone for display
    """
    if order_created_at is None:
        return None
    
    # Ensure we have a timezone-aware UTC datetime
    if order_created_at.tzinfo is None:
        utc_dt = order_created_at.replace(tzinfo=timezone.utc)
    else:
        utc_dt = order_created_at.astimezone(timezone.utc)
    
    # Get the target timezone (location's timezone or Central as fallback)
    target_tz = get_business_timezone_for_location(location_timezone)
    
    # Convert to local time
    local_dt = utc_dt.astimezone(target_tz)
    logger.debug(f"Converted order time from UTC {utc_dt} to {target_tz.key} {local_dt}")
    
    return local_dt

def format_datetime_for_display(dt: datetime, format_str: str = "%Y-%m-%d %I:%M %p") -> str:
    """
    Format datetime for display with timezone abbreviation.
    Default format shows: 2025-01-15 2:30 PM
    """
    if dt is None:
        return ""
    
    # Get timezone abbreviation (CST/CDT)
    tz_abbr = dt.strftime("%Z")
    formatted = dt.strftime(format_str)
    
    return f"{formatted} {tz_abbr}"

def is_central_time_location(location_timezone: str = None) -> bool:
    """
    Check if the given location timezone is in Central Time zone.
    """
    if not location_timezone:
        return True  # Default assumption
    
    central_zones = [
        "America/Chicago", 
        "America/Indiana/Knox", 
        "America/Indiana/Tell_City",
        "America/Menominee",
        "America/North_Dakota/Beulah",
        "America/North_Dakota/Center", 
        "America/North_Dakota/New_Salem",
        "CST", "CDT", "UTC-6", "UTC-5"
    ]
    
    return any(zone in location_timezone for zone in central_zones) 