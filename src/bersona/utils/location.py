from datetime import time
from timezonefinder import TimezoneFinder
import pytz

# Default location (Zhengzhou, Henan, China)
DEFAULT_LOCATION = (34.75, 113.62)
DEFAULT_TIME = time(12, 0)


def get_timezone_str(latitude: float, longitude: float) -> str:
    """
    Get the timezone string from latitude and longitude.
    """
    tf = TimezoneFinder()
    return tf.timezone_at(lng=longitude, lat=latitude)


def get_defaults(birth_time: time | None, location: tuple[float, float] | None) -> tuple[time, tuple[float, float]]:
    """
    Return default time and location if not provided.
    """
    if birth_time is None:
        birth_time = DEFAULT_TIME
    if location is None:
        location = DEFAULT_LOCATION
    return birth_time, location
