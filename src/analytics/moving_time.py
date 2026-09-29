"""Calculate running moving time within an athlete's local calendar week."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.analytics._week import _local_week_bounds_utc
from src.models.activity import Activity


def weekly_running_moving_time(
    activities: list[Activity],
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
) -> int:
    """Return integer seconds for Runs starting in the local calendar week.

    The first Monday is inclusive and the following Monday is exclusive.
    A naive reference raises ValueError, even with empty input. No matching
    runs returns 0. Activities must satisfy the Activity input contract;
    source validation belongs in the mapper. Entries are not deduplicated
    and their moving time is not split between weeks.
    """
    week_start_utc, next_week_start_utc = _local_week_bounds_utc(
        reference_datetime=reference_datetime,
        athlete_timezone=athlete_timezone,
    )

    return sum(
        activity.moving_time_seconds
        for activity in activities
        if activity.sport_type == "Run"
        and week_start_utc <= activity.start_date < next_week_start_utc
    )
