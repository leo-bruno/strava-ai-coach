"""Validate weekly identity and order supplied observations without filling gaps."""

from collections.abc import Sequence
from datetime import date

from src.models.weekly_analysis import WeeklyAnalysis


def normalize_weekly_history(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[WeeklyAnalysis, ...]:
    """Return the original observations sorted by unique Monday dates.

    Gaps and existing zero observations are retained. The caller is responsible
    for compatible athlete/timezone context; coverage is not assessed here.
    """
    seen: set[date] = set()
    for week in weeks:
        if week.week_start_date.weekday() != 0:
            raise ValueError("Each week_start_date must be a Monday.")
        if week.week_start_date in seen:
            raise ValueError(f"Duplicate week_start_date: {week.week_start_date}.")
        seen.add(week.week_start_date)
    return tuple(sorted(weeks, key=lambda week: week.week_start_date))
