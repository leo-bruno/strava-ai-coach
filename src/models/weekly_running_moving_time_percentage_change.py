"""Percentage running moving time change across observed consecutive weeks."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeeklyRunningMovingTimePercentageChange:
    """A transition with a percentage value: 10.0 means ten percent.

    None means exclusively that the previous moving time is zero, including
    zero to zero. It does not mean a missing observation or no change.
    The caller supplies all fields; this model performs no calculation,
    validation, unit conversion or rounding.
    """

    previous_week_start_date: date
    current_week_start_date: date
    value: float | None
