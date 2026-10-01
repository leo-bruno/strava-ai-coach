"""Compare running distance between consecutive local calendar weeks."""

from collections.abc import Sequence

from src.models.weekly_analysis import WeeklyAnalysis
from src.models.weekly_running_distance_change import WeeklyRunningDistanceChange
from src.trends._percentage import _percentage_change
from src.trends._week import _validate_consecutive_weeks
from src.trends.history import consecutive_week_pairs


def weekly_running_distance_change(
    previous: WeeklyAnalysis,
    current: WeeklyAnalysis,
) -> float:
    """Return current minus previous running distance in meters, unrounded.

    Both week dates must be Mondays, exactly seven calendar days apart in
    chronological order; otherwise raise ValueError. Inputs are not modified.
    This compares supplied observations without assessing calendar closure,
    history completeness or the significance of the change.
    """
    _validate_consecutive_weeks(previous, current)
    return current.running_distance_meters - previous.running_distance_meters


def weekly_running_distance_percentage_change(
    previous: WeeklyAnalysis,
    current: WeeklyAnalysis,
) -> float | None:
    """Return percentage change, where 10.0 means 10 percent, without rounding.

    None means the previous value is zero, including zero to zero; it does
    not mean missing data or no change. Require consecutive Monday dates or
    raise ValueError, even with a zero base. Inputs remain unchanged.
    """
    _validate_consecutive_weeks(previous, current)
    return _percentage_change(previous.running_distance_meters, current.running_distance_meters)


def weekly_running_distance_changes(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[WeeklyRunningDistanceChange, ...]:
    """Return dated absolute distance changes in meters for consecutive pairs.

    History normalization rejects duplicate dates and non-Mondays. Gaps produce
    no result; observed zero distances participate normally. Inputs are unchanged.
    No coverage, calendar closure or significance is assessed.
    """
    return tuple(
        WeeklyRunningDistanceChange(
            previous_week_start_date=previous.week_start_date,
            current_week_start_date=current.week_start_date,
            value=weekly_running_distance_change(previous, current),
        )
        for previous, current in consecutive_week_pairs(weeks)
    )
