"""Shared activity data used by the application."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Activity:
    """Activity measurements with a timezone-aware UTC start date."""

    id: int
    name: str
    sport_type: str
    start_date: datetime
    distance_meters: float
    moving_time_seconds: int
