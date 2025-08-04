from datetime import datetime
from typing import TypeAlias

from dateutil import parser

from src.core.utilities import DEFAULT_TZ

datetime_iso8601_str: TypeAlias = str

def get_current_datetime():
    """Get current datetime in the format required by Moomoo API."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def datetime_from_iso8601(dt_str: str):
    """
    Parse an ISO 8601 datetime string into a Python datetime object.

    Acceptable input formats include:
    - Timezone-aware strings:
        * UTC indicated by 'Z', e.g., "2023-08-03T12:34:56Z"
        * Explicit offsets, e.g., "2023-08-03T12:34:56+05:30" or "2023-08-03T23:45:00-07:00"
        * Fractional seconds, e.g., "2023-08-03T12:34:56.789Z" or "2023-08-03T12:34:56.789123Z"

    - Naive (timezone-unaware) strings:
        * Full datetime without offset, e.g., "2023-08-03T12:34:56"

    - Reduced accuracy:
        * Without seconds, e.g., "2023-08-03T12:34Z"

    - Date-only strings:
        * "2023-08-03" (interpreted as midnight)

    The parser supports leap years (e.g., "2024-02-29T15:00:00Z").

    Invalid inputs (wrong format, empty string, unsupported offset) return None.

    :param s: ISO 8601 datetime string
    :return: datetime.datetime object (timezone-aware, utc if timezone not specified)
    """

    try:
        dt = parser.parse(dt_str)
        return dt if dt.tzinfo else DEFAULT_TZ.localize(dt)

    except ValueError:
        return None


def datetime_to_iso8601_str(dt:datetime) -> str:
    """
    Convert a datetime object to ISO 8601 formatted string.
    
    Args:
        dt (datetime): The datetime object to convert
        
    Returns:
        str: ISO 8601 formatted datetime string
    """
    return dt.isoformat()
