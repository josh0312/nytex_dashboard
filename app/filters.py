"""Jinja2 template filters for the application."""

from datetime import datetime
from dateutil import parser

def format_currency(value):
    """Format a number as currency with commas and 2 decimal places.
    
    Args:
        value: The number to format
        
    Returns:
        str: The formatted currency string (e.g. "7,483.62")
    """
    try:
        return "{:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return "0.00"

def parse_iso_datetime(value):
    """Parse an ISO datetime string into a datetime object.
    
    Args:
        value: The ISO datetime string to parse
        
    Returns:
        datetime: The parsed datetime object
    """
    try:
        if isinstance(value, str):
            return parser.isoparse(value)
        return value
    except (ValueError, TypeError):
        return datetime.now()

def format_datetime(value, format_string='%Y-%m-%d %H:%M:%S'):
    """Format a datetime object using the specified format string.
    
    Args:
        value: The datetime object to format
        format_string: The format string to use
        
    Returns:
        str: The formatted datetime string
    """
    try:
        if isinstance(value, str):
            value = parser.isoparse(value)
        return value.strftime(format_string)
    except (ValueError, TypeError, AttributeError):
        return "Unknown"

# Dictionary of all filters to register
filters = {
    "currency": format_currency,
    "parse_iso_datetime": parse_iso_datetime,
    "format_datetime": format_datetime
} 