"""Absolute moving time change across two observed consecutive weeks."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeeklyRunningMovingTimeChange:
    """A transition with current minus previous running moving time in seconds.

    Value is an integer difference, not a percentage or the current week's
    moving time. The caller supplies all fields; this model performs no
    calculation, validation, numeric conversion or rounding.
    """

    previous_week_start_date: date
    current_week_start_date: date
    value: int
