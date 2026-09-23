"""Calculate running distance within an athlete's local calendar week."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.analytics._week import _local_week_bounds_utc
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
    week_start_utc, next_week_start_utc = _local_week_bounds_utc(
        reference_datetime=reference_datetime,
        athlete_timezone=athlete_timezone,
    )

    return sum(
        (
            activity.distance_meters
            for activity in activities
            if activity.sport_type == "Run"
            and week_start_utc <= activity.start_date < next_week_start_utc
        ),
        0.0,
    )
