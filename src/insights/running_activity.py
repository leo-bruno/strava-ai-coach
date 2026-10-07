"""Detect observed Run activity following supplied zero-Run week episodes."""

from collections.abc import Sequence

from src.models.observed_running_after_zero_run_weeks import (
    ObservedRunningAfterZeroRunWeeks,
)
from src.models.weekly_analysis import WeeklyAnalysis
from src.trends.history import consecutive_week_pairs


def detect_observed_running_after_zero_run_weeks(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[ObservedRunningAfterZeroRunWeeks, ...]:
    """Return one result per maximal episode of at least two zero-Run weeks.

    Zero means count == 0; the immediately following week must have count > 0.
    Distance never determines eligibility. History supplies normalized,
    validated consecutive pairs; disconnected chains reset episode state.
    Its ValueErrors propagate even for short histories. Trailing zero weeks
    yield no result. Inputs remain unchanged, and results follow running-week
    order. Valid metrics and compatible athlete/timezone context are the
    caller's responsibility. Supplied observations establish no real inactivity,
    rest, training interruption, behavioral return or physiological meaning.
    """
    results = []
    last_week_date = None
    zero_week_count = 0
    for previous, current in consecutive_week_pairs(weeks):
        if last_week_date != previous.week_start_date:
            first_zero_week_date = previous.week_start_date
            zero_week_count = 1 if previous.running_activity_count == 0 else 0
        if current.running_activity_count == 0:
            if zero_week_count == 0:
                first_zero_week_date = current.week_start_date
            zero_week_count += 1
        else:
            if current.running_activity_count > 0 and zero_week_count >= 2:
                results.append(ObservedRunningAfterZeroRunWeeks(
                    first_zero_week_date=first_zero_week_date,
                    observed_zero_week_count=zero_week_count,
                    running_week_date=current.week_start_date,
                    running_week_activity_count=current.running_activity_count,
                    running_week_distance_meters=current.running_distance_meters,
                ))
            zero_week_count = 0
        last_week_date = current.week_start_date
    return tuple(results)
