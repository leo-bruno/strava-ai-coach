"""Compare running activity counts between consecutive local calendar weeks."""

from collections.abc import Sequence

from src.models.weekly_analysis import WeeklyAnalysis
from src.models.weekly_running_activity_count_change import WeeklyRunningActivityCountChange
from src.trends._percentage import _percentage_change
from src.trends._week import _validate_consecutive_weeks
from src.trends.history import consecutive_week_pairs


def weekly_running_activity_count_change(
    previous: WeeklyAnalysis,
    current: WeeklyAnalysis,
) -> int:
    """Return current minus previous activity count as an exact integer.

    Require Monday dates exactly seven calendar days apart in chronological
    order, or raise ValueError. Inputs remain unchanged. No calendar closure,
    completeness or significance is assessed.
    """
    _validate_consecutive_weeks(previous, current)
    return current.running_activity_count - previous.running_activity_count


def weekly_running_activity_count_percentage_change(
    previous: WeeklyAnalysis,
    current: WeeklyAnalysis,
) -> float | None:
    """Return percentage change, where 10.0 means 10 percent, without rounding.

    None means the previous value is zero, including zero to zero; it does
    not mean missing data or no change. Require consecutive Monday dates or
    raise ValueError, even with a zero base. Inputs remain unchanged.
    """
    _validate_consecutive_weeks(previous, current)
    return _percentage_change(previous.running_activity_count, current.running_activity_count)


def weekly_running_activity_count_changes(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[WeeklyRunningActivityCountChange, ...]:
    """Return dated integer count changes for supplied consecutive observations.

    Observed zero counts participate normally; gaps produce no result.
    Normalization errors propagate and inputs remain unchanged. No coverage
    or calendar closure is assessed.
    """
    return tuple(
        WeeklyRunningActivityCountChange(
            previous_week_start_date=previous.week_start_date,
            current_week_start_date=current.week_start_date,
            value=weekly_running_activity_count_change(previous, current),
        )
        for previous, current in consecutive_week_pairs(weeks)
    )
