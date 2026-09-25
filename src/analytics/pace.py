"""Calculate moving pace from time and distance for activities and laps."""

from math import isfinite

from src.models.activity import Activity


def average_moving_pace(activity: Activity) -> float | None:
    """Return activity pace using the shared moving-pace calculation."""
    return moving_pace(activity.distance_meters, activity.moving_time_seconds)


def moving_pace(distance_meters: float, moving_time_seconds: int) -> float | None:
    """Return seconds/km, or None for zero distance or invalid measurements.

    Distance must be finite and positive; time must be a nonnegative integer.
    Raw-source validation belongs in the mapper, which raises for malformed data.
    """
    if (
        not isinstance(distance_meters, (int, float))
        or isinstance(distance_meters, bool)
        or not isinstance(moving_time_seconds, int)
        or isinstance(moving_time_seconds, bool)
        or moving_time_seconds < 0
    ):
        return None
    try:
        if not isfinite(distance_meters) or distance_meters <= 0:
            return None
        pace = moving_time_seconds / (distance_meters / 1000)
    except (OverflowError, ZeroDivisionError):
        return None

    return pace if isfinite(pace) else None
