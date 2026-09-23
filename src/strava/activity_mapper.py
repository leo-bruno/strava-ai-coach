"""Convert Strava activity responses into the shared activity model."""

from datetime import datetime, timezone
from math import isfinite

from src.models.activity import Activity


def activity_from_strava(data: dict[str, object]) -> Activity:
    """Validate required Strava fields and normalize measurements and dates."""
    activity_id = data.get("id")
    name = data.get("name")
    sport_type = data.get("sport_type")
    start_date = data.get("start_date")
    distance = data.get("distance")
    moving_time = data.get("moving_time")

    if not isinstance(activity_id, int) or isinstance(activity_id, bool):
        raise ValueError("Activity id must be an integer.")
    if not isinstance(name, str):
        raise ValueError("Activity name must be a string.")
    if not isinstance(sport_type, str):
        raise ValueError("Activity sport_type must be a string.")
    if not isinstance(start_date, str):
        raise ValueError("Activity start_date must be a timezone-aware date string.")

    try:
        parsed_date = datetime.fromisoformat(start_date)
        if parsed_date.tzinfo is None or parsed_date.utcoffset() is None:
            raise ValueError
        parsed_date = parsed_date.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise ValueError(
            "Activity start_date must be a timezone-aware date string."
        ) from None

    if not isinstance(distance, (int, float)) or isinstance(distance, bool):
        raise ValueError("Activity distance must be a finite nonnegative number.")
    try:
        distance_meters = float(distance)
    except OverflowError:
        raise ValueError(
            "Activity distance must be a finite nonnegative number."
        ) from None
    if not isfinite(distance_meters) or distance_meters < 0:
        raise ValueError("Activity distance must be a finite nonnegative number.")
    if (
        not isinstance(moving_time, int)
        or isinstance(moving_time, bool)
        or moving_time < 0
    ):
        raise ValueError("Activity moving_time must be a nonnegative integer.")

    return Activity(
        id=activity_id,
        name=name,
        sport_type=sport_type,
        start_date=parsed_date,
        distance_meters=distance_meters,
        moving_time_seconds=moving_time,
    )
