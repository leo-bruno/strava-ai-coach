"""Compare running activity counts between consecutive local calendar weeks."""

from src.models.weekly_analysis import WeeklyAnalysis
from src.trends._percentage import _percentage_change
from src.trends._week import _validate_consecutive_weeks


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
