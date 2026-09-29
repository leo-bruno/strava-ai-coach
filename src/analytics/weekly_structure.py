"""Aggregate running counts, distances and moving times by type per local week."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.analytics._week import _local_week_bounds_utc
from src.analytics.training_type import classify_training_type
from src.models.activity import Activity
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary


def weekly_running_structure(
    activities: list[Activity],
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
) -> tuple[TrainingTypeSummary, ...]:
    """Return count, distance and moving time for all six types in enum order.

    Only Runs starting within the local Monday-to-Monday week are classified,
    exactly once per supplied entry. Start is inclusive and end exclusive.
    Duplicates count separately, inputs remain unchanged, and a naive reference
    raises ValueError even with empty input. Absent types have all metrics at
    zero. Distances retain float precision without rounding; moving times are
    summed exactly in integer seconds from Activity.moving_time_seconds.
    """
    week_start_utc, next_week_start_utc = _local_week_bounds_utc(
        reference_datetime=reference_datetime,
        athlete_timezone=athlete_timezone,
    )
    counts = dict.fromkeys(TrainingType, 0)
    distances = dict.fromkeys(TrainingType, 0.0)
    moving_times = dict.fromkeys(TrainingType, 0)
    for activity in activities:
        if (
            activity.sport_type == "Run"
            and week_start_utc <= activity.start_date < next_week_start_utc
        ):
            training_type = classify_training_type(activity)
            counts[training_type] += 1
            distances[training_type] += activity.distance_meters
            moving_times[training_type] += activity.moving_time_seconds

    return tuple(
        TrainingTypeSummary(
            training_type=training_type,
            activity_count=count,
            distance_meters=distances[training_type],
            moving_time_seconds=moving_times[training_type],
        )
        for training_type, count in counts.items()
    )
