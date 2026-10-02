"""Compare running moving time between consecutive local calendar weeks."""

from collections.abc import Sequence

from src.models.weekly_analysis import WeeklyAnalysis
from src.models.weekly_running_moving_time_change import WeeklyRunningMovingTimeChange
from src.models.weekly_running_moving_time_percentage_change import WeeklyRunningMovingTimePercentageChange
from src.trends._percentage import _percentage_change
from src.trends._week import _validate_consecutive_weeks
from src.trends.history import consecutive_week_pairs


def weekly_running_moving_time_change(
    previous: WeeklyAnalysis,
    current: WeeklyAnalysis,
) -> int:
    """Return current minus previous moving time in exact integer seconds.

    Require Monday dates exactly seven calendar days apart in chronological
    order, or raise ValueError. Inputs remain unchanged. No calendar closure,
    completeness or significance is assessed.
    """
    _validate_consecutive_weeks(previous, current)
    return current.running_moving_time_seconds - previous.running_moving_time_seconds


def weekly_running_moving_time_percentage_change(
    previous: WeeklyAnalysis,
    current: WeeklyAnalysis,
) -> float | None:
    """Return percentage change, where 10.0 means 10 percent, without rounding.

    None means the previous value is zero, including zero to zero; it does
    not mean missing data or no change. Require consecutive Monday dates or
    raise ValueError, even with a zero base. Inputs remain unchanged.
    """
    _validate_consecutive_weeks(previous, current)
    return _percentage_change(previous.running_moving_time_seconds, current.running_moving_time_seconds)


def weekly_running_moving_time_changes(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[WeeklyRunningMovingTimeChange, ...]:
    """Return dated absolute moving time changes in exact integer seconds.

    Observed zero values participate normally; gaps produce no result.
    Normalization errors propagate and inputs remain unchanged. No coverage
    or calendar closure is assessed.
    """
    return tuple(
        WeeklyRunningMovingTimeChange(
            previous_week_start_date=previous.week_start_date,
            current_week_start_date=current.week_start_date,
            value=weekly_running_moving_time_change(previous, current),
        )
        for previous, current in consecutive_week_pairs(weeks)
    )


def weekly_running_moving_time_percentage_changes(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[WeeklyRunningMovingTimePercentageChange, ...]:
    """Return dated moving time percentages for consecutive observations.

    A zero base retains a result with value None. Gaps produce no result.
    Normalization errors propagate; inputs remain unchanged. No coverage or
    calendar closure is assessed, and percentages are not rounded.
    """
    return tuple(
        WeeklyRunningMovingTimePercentageChange(
            previous_week_start_date=previous.week_start_date,
            current_week_start_date=current.week_start_date,
            value=weekly_running_moving_time_percentage_change(previous, current),
        )
        for previous, current in consecutive_week_pairs(weeks)
    )
