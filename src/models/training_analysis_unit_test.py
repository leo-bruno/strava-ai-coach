"""Unit tests for the training analysis data contract."""

from datetime import datetime, timezone

import pytest

from src.models.activity import Activity
from src.models.training_analysis import TrainingAnalysis, TrainingLap, TrainingType


@pytest.fixture
def activity() -> Activity:
    return Activity(
        id=123,
        name="Morning Run",
        sport_type="Run",
        start_date=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
        distance_meters=5000.0,
        moving_time_seconds=1500,
    )


def test_supported_training_types() -> None:
    assert {training_type.value for training_type in TrainingType} == {
        "Easy", "Long", "Tempo", "Intervals", "Race", "Other"
    }


def test_analysis_reuses_activity_and_allows_missing_measurements(activity) -> None:
    analysis = TrainingAnalysis(
        activity=activity,
        training_type=TrainingType.OTHER,
        average_pace_seconds_per_km=None,
    )

    assert analysis.activity is activity
    assert analysis.average_pace_seconds_per_km is None
    assert analysis.average_heart_rate_bpm is None
    assert analysis.maximum_heart_rate_bpm is None
    assert analysis.cadence_steps_per_minute is None
    assert analysis.elevation_gain_meters is None
    assert analysis.laps == ()


def test_lap_allows_missing_measurements_and_undefined_pace() -> None:
    lap = TrainingLap(
        distance_meters=0.0,
        moving_time_seconds=0,
        pace_seconds_per_km=None,
    )

    assert lap.pace_seconds_per_km is None
    assert lap.average_heart_rate_bpm is None
    assert lap.maximum_heart_rate_bpm is None
    assert lap.cadence_steps_per_minute is None


def test_analysis_preserves_supplied_measurements_and_lap_order(activity) -> None:
    first_lap = TrainingLap(
        distance_meters=1000.5,
        moving_time_seconds=301,
        pace_seconds_per_km=300.85,
        average_heart_rate_bpm=140.5,
        maximum_heart_rate_bpm=152.0,
        cadence_steps_per_minute=172.5,
    )
    second_lap = TrainingLap(
        distance_meters=0.0,
        moving_time_seconds=0,
        pace_seconds_per_km=None,
        cadence_steps_per_minute=0.0,
    )
    analysis = TrainingAnalysis(
        activity=activity,
        training_type=TrainingType.INTERVALS,
        average_pace_seconds_per_km=300.0,
        average_heart_rate_bpm=145.5,
        maximum_heart_rate_bpm=165.0,
        cadence_steps_per_minute=174.5,
        elevation_gain_meters=0.0,
        laps=(first_lap, second_lap),
    )

    assert analysis.training_type is TrainingType.INTERVALS
    assert analysis.average_pace_seconds_per_km == 300.0
    assert analysis.average_heart_rate_bpm == 145.5
    assert analysis.maximum_heart_rate_bpm == 165.0
    assert analysis.cadence_steps_per_minute == 174.5
    assert analysis.elevation_gain_meters == 0.0
    assert analysis.laps == (first_lap, second_lap)
    assert analysis.laps[0].average_heart_rate_bpm == 140.5
    assert analysis.laps[1].cadence_steps_per_minute == 0.0
