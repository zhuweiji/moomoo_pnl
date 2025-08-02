"""Constants used throughout the application."""

from datetime import datetime

FIRST_ORDER_DATE = "2024-03-31 00:00:00"


def get_current_datetime():
    """Get current datetime in the format required by Moomoo API."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
