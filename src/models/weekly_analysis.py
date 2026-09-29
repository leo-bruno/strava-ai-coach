"""Weekly running analysis data shared by analytics and its consumers."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeeklyAnalysis:
    """Supplied weekly results without calculation or validation behavior.

    week_start_date identifies the Monday in the athlete's local calendar.
    Metrics cover only Run activities supplied for that week; they do not
    guarantee a complete activity history. Zero distance and zero count are
    valid results, and zero distance may accompany a positive activity count.
    The caller supplies all fields, including the local Monday date.
    """

    week_start_date: date
    running_distance_meters: float
    running_activity_count: int
