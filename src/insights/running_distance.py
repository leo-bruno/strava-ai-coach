"""Detect persistent increases in supplied weekly running distance."""

from collections.abc import Sequence

from src.models.persistent_weekly_running_distance_increase import (
    PersistentWeeklyRunningDistanceIncrease,
)
from src.models.weekly_analysis import WeeklyAnalysis
from src.trends.distance import weekly_running_distance_changes
from src.trends.history import normalize_weekly_history


def detect_persistent_weekly_running_distance_increases(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[PersistentWeeklyRunningDistanceIncrease, ...]:
    """Return every four-week window with three strictly positive changes.

    All four observations must have positive distance and Run count. Trends
    validates and orders Mondays, selects consecutive pairs and subtracts
    distances; its ValueErrors propagate even for short histories. Gaps,
    equality and zero weeks break the pattern. Overlapping windows are retained
    chronologically, without rounding or a magnitude threshold. Inputs remain
    unchanged; compatible athlete/timezone context is the caller's responsibility.
    No coverage, calendar closure or physiological significance is inferred.
    """
    normalized = normalize_weekly_history(weeks)
    by_date = {week.week_start_date: week for week in normalized}
    changes = weekly_running_distance_changes(normalized)
    results = []
    for first, second, third in zip(changes, changes[1:], changes[2:]):
        if (
            first.current_week_start_date != second.previous_week_start_date
            or second.current_week_start_date != third.previous_week_start_date
        ):
            continue
        if not all(change.value > 0 for change in (first, second, third)):
            continue
        w1 = by_date[first.previous_week_start_date]
        w2 = by_date[first.current_week_start_date]
        w3 = by_date[second.current_week_start_date]
        w4 = by_date[third.current_week_start_date]
        if not all(
            week.running_distance_meters > 0 and week.running_activity_count > 0
            for week in (w1, w2, w3, w4)
        ):
            continue
        results.append(PersistentWeeklyRunningDistanceIncrease(
            start_week_date=w1.week_start_date,
            end_week_date=w4.week_start_date,
            weekly_distances_meters=(
                w1.running_distance_meters, w2.running_distance_meters,
                w3.running_distance_meters, w4.running_distance_meters,
            ),
            weekly_activity_counts=(
                w1.running_activity_count, w2.running_activity_count,
                w3.running_activity_count, w4.running_activity_count,
            ),
            distance_changes=(first, second, third),
        ))
    return tuple(results)
