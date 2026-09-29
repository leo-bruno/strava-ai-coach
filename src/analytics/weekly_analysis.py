"""Build a weekly running analysis from supplied activities."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.analytics._week import _local_week_bounds_utc
from src.analytics.activity_count import weekly_running_activity_count
from src.analytics.distance import weekly_running_distance
from src.analytics.moving_time import weekly_running_moving_time
from src.analytics.weekly_structure import weekly_running_structure
from src.models.activity import Activity
from src.models.weekly_analysis import WeeklyAnalysis


def weekly_analysis_from_activities(
    activities: list[Activity],
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
) -> WeeklyAnalysis:
    """Combine existing metrics for the athlete's local Monday-to-Monday week.

    Only Run activities are included, using an inclusive start and exclusive
    end. A naive reference raises ValueError, including with empty input.
    Inputs are not modified. Results describe supplied activities without
    fetching missing history or deduplicating entries.
    """
    week_start_utc, _ = _local_week_bounds_utc(
        reference_datetime=reference_datetime,
        athlete_timezone=athlete_timezone,
    )

    return WeeklyAnalysis(
        week_start_date=week_start_utc.astimezone(athlete_timezone).date(),
        running_distance_meters=weekly_running_distance(
            activities,
            reference_datetime=reference_datetime,
            athlete_timezone=athlete_timezone,
        ),
        running_activity_count=weekly_running_activity_count(
            activities,
            reference_datetime=reference_datetime,
            athlete_timezone=athlete_timezone,
        ),
        running_moving_time_seconds=weekly_running_moving_time(
            activities,
            reference_datetime=reference_datetime,
            athlete_timezone=athlete_timezone,
        ),
        running_structure_by_type=weekly_running_structure(
            activities,
            reference_datetime=reference_datetime,
            athlete_timezone=athlete_timezone,
        ),
    )
