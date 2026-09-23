"""Calculate running distance within an athlete's local calendar week."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from src.models.activity import Activity


def weekly_running_distance(
    activities: list[Activity],
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
) -> float:
    """Return meters run in the local Monday-to-Monday week of an aware reference.

    Activities belong to the week containing their UTC start time. The first
    Monday is inclusive and the following Monday is exclusive. A naive
    reference datetime raises ValueError.
    """
    if reference_datetime.tzinfo is None or reference_datetime.utcoffset() is None:
        raise ValueError("Reference datetime must be timezone-aware.")

    local_date = reference_datetime.astimezone(athlete_timezone).date()
    monday = local_date - timedelta(days=local_date.weekday())
    next_monday = monday + timedelta(days=7)
    week_start_utc = datetime.combine(
        monday, time.min, tzinfo=athlete_timezone
    ).astimezone(timezone.utc)
    next_week_start_utc = datetime.combine(
        next_monday, time.min, tzinfo=athlete_timezone
    ).astimezone(timezone.utc)

    return sum(
        (
            activity.distance_meters
            for activity in activities
            if activity.sport_type == "Run"
            and week_start_utc <= activity.start_date < next_week_start_utc
        ),
        0.0,
    )
