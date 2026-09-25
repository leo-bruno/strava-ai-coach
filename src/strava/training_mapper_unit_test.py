"""Unit tests for mapping already-fetched running measurements."""

import pytest

from src.analytics.pace import average_moving_pace
from src.models.training_analysis import TrainingLap
from src.strava.activity_mapper import activity_from_strava
from src.strava.training_mapper import (
    average_heart_rate_from_strava,
    elevation_gain_from_strava,
    maximum_heart_rate_from_strava,
    running_cadence_from_strava,
    running_lap_from_strava,
    running_laps_from_strava,
)


@pytest.fixture
def lap_data() -> dict[str, object]:
    return {
        "distance": 400.5,
        "moving_time": 97,
        "elapsed_time": 120,
        "average_heartrate": 162.5,
        "max_heartrate": 175,
        "average_cadence": 84.5,
    }


def test_maps_lap_using_moving_time_and_converts_cadence(lap_data) -> None:
    lap = running_lap_from_strava(lap_data)

    assert lap == TrainingLap(
        distance_meters=400.5,
        moving_time_seconds=97,
        pace_seconds_per_km=pytest.approx(242.1972534332085),
        average_heart_rate_bpm=162.5,
        maximum_heart_rate_bpm=175.0,
        cadence_steps_per_minute=169.0,
    )


def test_realistic_interval_laps_preserve_response_order() -> None:
    # Synthetic interval measurements; no historical files or service access.
    data = {"laps": [
        {"distance": 1000.0, "moving_time": 360, "lap_index": 3,
         "average_heartrate": 130.5, "average_cadence": 79.5},
        {"distance": 400.0, "moving_time": 96, "lap_index": 1,
         "average_heartrate": 166, "max_heartrate": 178, "average_cadence": 88},
        {"distance": 200.0, "moving_time": 100, "lap_index": 2,
         "average_heartrate": 145, "average_cadence": 75},
        {"distance": 400.0, "moving_time": 94,
         "average_heartrate": 168, "max_heartrate": 180, "average_cadence": 89.5},
    ]}

    laps = running_laps_from_strava(data)

    assert isinstance(laps, tuple)
    assert [lap.distance_meters for lap in laps] == [1000, 400, 200, 400]
    assert [lap.pace_seconds_per_km for lap in laps] == [360, 240, 500, 235]
    assert [lap.cadence_steps_per_minute for lap in laps] == [159, 176, 150, 179]


def test_activity_measurements_reuse_existing_activity_and_pace_mapping() -> None:
    data = {
        "id": 123, "name": "Repeticiones: 400 m", "sport_type": "Run",
        "start_date": "2026-09-22T08:00:00Z", "distance": 5000.0,
        "moving_time": 1500, "average_heartrate": 150.5,
        "max_heartrate": 180, "average_cadence": 80.5,
        "total_elevation_gain": 42.5,
    }

    assert average_moving_pace(activity_from_strava(data)) == 300.0
    assert average_heart_rate_from_strava(data) == 150.5
    assert maximum_heart_rate_from_strava(data) == 180.0
    assert running_cadence_from_strava(data) == 161.0
    assert elevation_gain_from_strava(data) == 42.5


@pytest.mark.parametrize("explicit_null", [False, True])
def test_missing_optional_lap_measurements(explicit_null) -> None:
    data = {"distance": 0, "moving_time": 0}
    if explicit_null:
        data.update(average_heartrate=None, max_heartrate=None, average_cadence=None)

    assert running_lap_from_strava(data) == TrainingLap(0.0, 0, None)


_OPTIONAL_FIELDS = [
    ("average_heartrate", average_heart_rate_from_strava),
    ("max_heartrate", maximum_heart_rate_from_strava),
    ("average_cadence", running_cadence_from_strava),
    ("total_elevation_gain", elevation_gain_from_strava),
]


@pytest.mark.parametrize(("field", "mapper"), _OPTIONAL_FIELDS)
def test_optional_measurements_distinguish_missing_from_zero(field, mapper) -> None:
    assert mapper({}) is None
    assert mapper({field: None}) is None
    assert mapper({field: 0}) == 0.0


@pytest.mark.parametrize(("field", "mapper"), _OPTIONAL_FIELDS)
@pytest.mark.parametrize(
    "value", [True, "80", -1, float("nan"), float("inf"), [],
              pytest.param(10**400, id="overflow")],
)
def test_malformed_optional_measurements_raise(field, mapper, value) -> None:
    with pytest.raises(ValueError, match=field):
        mapper({field: value})


@pytest.mark.parametrize(("cadence", "expected"), [(80, 160), (92.4, 184.8), (160, 320)])
def test_running_cadence_always_doubles_without_unit_guessing(cadence, expected) -> None:
    assert running_cadence_from_strava({"average_cadence": cadence}) == expected


def test_cadence_conversion_overflow_raises() -> None:
    with pytest.raises(ValueError, match="average_cadence"):
        running_cadence_from_strava({"average_cadence": 1e308})


@pytest.mark.parametrize("field", ["distance", "moving_time"])
def test_missing_required_lap_fields_raise(lap_data, field) -> None:
    del lap_data[field]
    with pytest.raises(ValueError, match=field):
        running_lap_from_strava(lap_data)


@pytest.mark.parametrize("field", ["distance", "moving_time"])
@pytest.mark.parametrize("value", [None, True, "400", -1, float("nan"), float("inf"), {}])
def test_malformed_required_lap_fields_raise(lap_data, field, value) -> None:
    lap_data[field] = value
    with pytest.raises(ValueError, match=field):
        running_lap_from_strava(lap_data)


def test_fractional_moving_time_raises(lap_data) -> None:
    lap_data["moving_time"] = 97.5
    with pytest.raises(ValueError, match="moving_time"):
        running_lap_from_strava(lap_data)


def test_overflowing_distance_raises(lap_data) -> None:
    lap_data["distance"] = 10**400
    with pytest.raises(ValueError, match="distance"):
        running_lap_from_strava(lap_data)


@pytest.mark.parametrize("data", [{}, {"laps": None}, {"laps": []}])
def test_absent_laps_produce_empty_tuple(data) -> None:
    assert running_laps_from_strava(data) == ()


@pytest.mark.parametrize("laps", [{}, "invalid", 0])
def test_malformed_lap_collection_raises(laps) -> None:
    with pytest.raises(ValueError, match="laps must be a list"):
        running_laps_from_strava({"laps": laps})


@pytest.mark.parametrize("bad_lap", [None, [], "invalid", {}, {"distance": -1}])
def test_malformed_lap_reports_index(lap_data, bad_lap) -> None:
    with pytest.raises(ValueError, match=r"laps\[1\]"):
        running_laps_from_strava({"laps": [lap_data, bad_lap]})
