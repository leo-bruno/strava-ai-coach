"""Compare running moving time between consecutive local calendar weeks."""

from src.models.weekly_analysis import WeeklyAnalysis
from src.trends._percentage import _percentage_change
from src.trends._week import _validate_consecutive_weeks


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
