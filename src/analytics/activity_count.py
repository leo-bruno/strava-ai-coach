"""Count running activities within an athlete's local calendar week."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.analytics._week import _local_week_bounds_utc
from src.models.activity import Activity


def weekly_running_activity_count(
    activities: list[Activity],
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
) -> int:
    """Return the number of Runs in the local week of an aware reference.

    The first Monday is inclusive and the following Monday is exclusive.
    A naive reference datetime raises ValueError. No matching runs returns 0.
    """
    week_start_utc, next_week_start_utc = _local_week_bounds_utc(
        reference_datetime=reference_datetime,
        athlete_timezone=athlete_timezone,
    )

    return sum(
        1
        for activity in activities
        if activity.sport_type == "Run"
        and week_start_utc <= activity.start_date < next_week_start_utc
    )
