"""Percentage running distance change across two observed consecutive weeks."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeeklyRunningDistancePercentageChange:
    """A transition with a percentage value: 10.0 means ten percent.

    None means exclusively that the previous distance is zero, including a
    zero-to-zero transition. It does not mean a missing observation or no change.
    The caller supplies all fields; this model performs no calculation,
    validation, rounding or unit conversion.
    """

    previous_week_start_date: date
    current_week_start_date: date
    value: float | None
