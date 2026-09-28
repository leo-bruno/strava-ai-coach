"""Unit tests for assembling one running activity's complete analysis."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

import pytest

from src.analytics.pace import average_moving_pace
from src.models.activity import Activity
from src.models.training_analysis import TrainingAnalysis, TrainingLap, TrainingType
from src.strava.training_analysis import training_analysis_from_strava


@pytest.fixture
def activity() -> Activity:
    return Activity(
        id=123,
        name="Repeticiones 1 km",
        sport_type="Run",
        start_date=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
        distance_meters=2500.0,
        moving_time_seconds=750,
    )


def test_complete_analysis_preserves_lap_order_and_inputs(activity) -> None:
    data = {
        "id": 123, "name": activity.name, "sport_type": "Run",
        "distance": 2500.0, "moving_time": 750, "elapsed_time": 900,
        "average_heartrate": 155.5, "max_heartrate": 181,
        "average_cadence": 82.5, "total_elevation_gain": 25.5,
        "laps": [
            {"distance": 1000.0, "moving_time": 240, "lap_index": 3,
             "average_heartrate": 165, "max_heartrate": 178,
             "average_cadence": 87},
            {"distance": 500.0, "moving_time": 275, "lap_index": 1},
            {"distance": 1000.0, "moving_time": 235, "lap_index": 2,
             "average_heartrate": 168, "max_heartrate": 181,
             "average_cadence": 88.5},
        ],
    }
    original = deepcopy(data)

    result = training_analysis_from_strava(activity, data)

    assert result == TrainingAnalysis(
        activity=activity,
        training_type=TrainingType.INTERVALS,
        average_pace_seconds_per_km=300.0,
        average_heart_rate_bpm=155.5,
        maximum_heart_rate_bpm=181.0,
        cadence_steps_per_minute=165.0,
        elevation_gain_meters=25.5,
        laps=(
            TrainingLap(1000.0, 240, 240.0, 165.0, 178.0, 174.0),
            TrainingLap(500.0, 275, 550.0),
            TrainingLap(1000.0, 235, 235.0, 168.0, 181.0, 177.0),
        ),
    )
    assert result.activity is activity
    assert data == original
    with pytest.raises(FrozenInstanceError):
        result.training_type = TrainingType.OTHER


@pytest.mark.parametrize(("name", "expected"), [
    ("Carrera fácil", TrainingType.EASY),
    ("Carrera larga", TrainingType.LONG),
    ("Tempo 5km", TrainingType.TEMPO),
    ("Repeticiones 1 km", TrainingType.INTERVALS),
    ("2 km alternos", TrainingType.INTERVALS),
    ("Carrera de mañana", TrainingType.OTHER),
])
def test_classifies_typed_activity_name(activity, name, expected) -> None:
    result = training_analysis_from_strava(
        replace(activity, name=name), {"name": "Contrarreloj"}
    )
    assert result.training_type is expected


@pytest.mark.parametrize(("distance", "time"), [(5000.0, 1500), (0.0, 0)])
def test_pace_uses_typed_activity_and_shared_logic(activity, distance, time) -> None:
    activity = replace(activity, distance_meters=distance, moving_time_seconds=time)
    result = training_analysis_from_strava(
        activity, {"distance": 1000, "moving_time": 200, "elapsed_time": 300}
    )
    assert result.average_pace_seconds_per_km == average_moving_pace(activity)


@pytest.mark.parametrize("data", [
    {},
    {"average_heartrate": None, "max_heartrate": None,
     "average_cadence": None, "total_elevation_gain": None, "laps": None},
    {"laps": []},
])
def test_missing_measurements_and_laps(activity, data) -> None:
    assert training_analysis_from_strava(activity, data) == TrainingAnalysis(
        activity, TrainingType.INTERVALS, 300.0
    )


def test_zero_measurements_remain_zero(activity) -> None:
    result = training_analysis_from_strava(activity, {
        "average_heartrate": 0, "max_heartrate": 0,
        "average_cadence": 0, "total_elevation_gain": 0,
    })
    assert result.average_heart_rate_bpm == 0
    assert result.maximum_heart_rate_bpm == 0
    assert result.cadence_steps_per_minute == 0
    assert result.elevation_gain_meters == 0


def test_mismatched_identity_raises(activity) -> None:
    with pytest.raises(ValueError, match=r"id must match Activity.id"):
        training_analysis_from_strava(activity, {"id": 456})


@pytest.mark.parametrize("value", [None, "123", 123.0, True])
def test_malformed_supplied_identity_raises(activity, value) -> None:
    with pytest.raises(ValueError, match="id must be an integer"):
        training_analysis_from_strava(replace(activity, id=1), {"id": value})


@pytest.mark.parametrize("sport_type", ["Ride", "Walk", "TrailRun", ""])
def test_unsupported_sport_raises(activity, sport_type) -> None:
    with pytest.raises(ValueError, match="supports only sport_type 'Run'"):
        training_analysis_from_strava(
            replace(activity, sport_type=sport_type), {"average_cadence": 80}
        )


@pytest.mark.parametrize(("data", "message"), [
    ({"average_heartrate": "155"}, "average_heartrate"),
    ({"max_heartrate": -1}, "max_heartrate"),
    ({"average_cadence": True}, "average_cadence"),
    ({"total_elevation_gain": float("nan")}, "total_elevation_gain"),
    ({"laps": {}}, "laps must be a list"),
    ({"laps": [{"distance": 1000, "moving_time": 240},
               {"distance": 1000, "moving_time": "240"}]},
     r"laps\[1\]: moving_time"),
])
def test_malformed_measurements_propagate_errors(activity, data, message) -> None:
    with pytest.raises(ValueError, match=message):
        training_analysis_from_strava(activity, data)


@pytest.mark.parametrize("data", [None, [], "invalid"])
def test_malformed_detailed_object_raises(activity, data) -> None:
    with pytest.raises(ValueError, match="Detailed activity data must be an object"):
        training_analysis_from_strava(activity, data)
