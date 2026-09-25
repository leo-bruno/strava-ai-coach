"""Training analysis data shared by analytics and its consumers."""

from dataclasses import dataclass
from enum import Enum

from src.models.activity import Activity


class TrainingType(str, Enum):
    """Supported training categories; classification is supplied by the caller."""

    EASY = "Easy"
    LONG = "Long"
    TEMPO = "Tempo"
    INTERVALS = "Intervals"
    RACE = "Race"
    OTHER = "Other"


@dataclass(frozen=True)
class TrainingLap:
    """Lap measurements; None represents unavailable or undefined values.

    Heart rates are beats per minute. Cadence counts individual steps per minute.
    """

    distance_meters: float
    moving_time_seconds: int
    pace_seconds_per_km: float | None
    average_heart_rate_bpm: float | None = None
    maximum_heart_rate_bpm: float | None = None
    cadence_steps_per_minute: float | None = None


@dataclass(frozen=True)
class TrainingAnalysis:
    """Analysis result without classification or calculation behavior.

    The activity supplies id, name, UTC start_date, distance_meters and
    moving_time_seconds. Pace uses the existing analytics unit of seconds per
    kilometer; None represents undefined pace. Optional measurements use None
    for missing data, preserving zero as a measured value. Heart rates are
    beats per minute, and cadence counts individual steps per minute.
    Laps retain activity order; an empty tuple represents no available laps.
    """

    activity: Activity
    training_type: TrainingType
    average_pace_seconds_per_km: float | None
    average_heart_rate_bpm: float | None = None
    maximum_heart_rate_bpm: float | None = None
    cadence_steps_per_minute: float | None = None
    elevation_gain_meters: float | None = None
    laps: tuple[TrainingLap, ...] = ()
