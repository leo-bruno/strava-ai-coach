"""Absolute activity count change across two observed consecutive weeks."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeeklyRunningActivityCountChange:
    """A transition with current minus previous running activity count.

    Value is an integer difference, not a percentage or the current week's
    count. The caller supplies all fields; this model performs no calculation,
    validation or numeric conversion.
    """

    previous_week_start_date: date
    current_week_start_date: date
    value: int
