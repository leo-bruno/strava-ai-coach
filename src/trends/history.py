"""Validate weekly identity and order supplied observations without filling gaps."""

from collections.abc import Sequence
from datetime import date, timedelta

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


def consecutive_week_pairs(
    weeks: Sequence[WeeklyAnalysis],
) -> tuple[tuple[WeeklyAnalysis, WeeklyAnalysis], ...]:
    """Return adjacent observations exactly seven calendar days apart.

    Normalize first, rejecting non-Mondays and duplicate dates. Gaps are
    skipped; existing zero observations participate normally. The original
    objects and input collection remain unchanged. Coverage is not assessed.
    """
    normalized = normalize_weekly_history(weeks)
    return tuple(
        (previous, current)
        for previous, current in zip(normalized, normalized[1:])
        if current.week_start_date - previous.week_start_date == timedelta(days=7)
    )
