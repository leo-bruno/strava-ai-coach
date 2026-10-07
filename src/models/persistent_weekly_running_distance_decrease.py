"""Evidence of three distance decreases across four observed running weeks."""

from dataclasses import dataclass
from datetime import date

from src.models.weekly_running_distance_change import WeeklyRunningDistanceChange


@dataclass(frozen=True)
class PersistentWeeklyRunningDistanceDecrease:
    """Supplied evidence without calculations or automatic validation.

    Dates identify the first and fourth local Mondays, not calendar end times.
    Distances and counts follow weekly order; changes retain Trends values and
    dates. This describes supplied observations, not significance, physiology,
    coverage, calendar closure or recommendations.
    """

    start_week_date: date
    end_week_date: date
    weekly_distances_meters: tuple[float, float, float, float]
    weekly_activity_counts: tuple[int, int, int, int]
    distance_changes: tuple[
        WeeklyRunningDistanceChange,
        WeeklyRunningDistanceChange,
        WeeklyRunningDistanceChange,
    ]
