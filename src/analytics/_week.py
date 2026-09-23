"""Calculate UTC boundaries for an athlete's local calendar week."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def _local_week_bounds_utc(
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
) -> tuple[datetime, datetime]:
    """Return inclusive Monday and exclusive next-Monday boundaries in UTC.

    A naive reference datetime raises ValueError.
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

    return week_start_utc, next_week_start_utc
