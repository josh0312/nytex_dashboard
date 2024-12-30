"""Jinja2 template filters for the application."""

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

# Dictionary of all filters to register
filters = {
    "currency": format_currency
} 