"""Shared temporal contract for two weekly observations."""

from datetime import timedelta

from src.models.weekly_analysis import WeeklyAnalysis


def _validate_consecutive_weeks(previous: WeeklyAnalysis, current: WeeklyAnalysis) -> None:
    """Require Monday dates exactly seven calendar days apart, in order."""
    if previous.week_start_date.weekday() != 0 or current.week_start_date.weekday() != 0:
        raise ValueError("Both week_start_date values must be Mondays.")
    if current.week_start_date - previous.week_start_date != timedelta(days=7):
        raise ValueError("Current week must be exactly seven calendar days after previous week.")
