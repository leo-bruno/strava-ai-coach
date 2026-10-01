"""Absolute running distance change across two observed consecutive weeks."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeeklyRunningDistanceChange:
    """A transition from previous to current, with a float value in meters.

    Value is current running distance minus previous running distance, not a
    percentage. The caller supplies all fields; no calculation, validation,
    rounding or unit conversion is performed by this model. Value is not optional.
    """

    previous_week_start_date: date
    current_week_start_date: date
    value: float
