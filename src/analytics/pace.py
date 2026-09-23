"""Calculate activity pace from moving time and distance."""

from src.models.activity import Activity


def average_moving_pace(activity: Activity) -> float | None:
    """Return seconds per kilometer, or None when distance is zero."""
    if activity.distance_meters == 0:
        return None

    return activity.moving_time_seconds / (activity.distance_meters / 1000)
