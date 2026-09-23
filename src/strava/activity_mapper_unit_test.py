"""Unit tests for converting Strava activity data."""

from datetime import datetime, timezone

import pytest

from src.models.activity import Activity
from src.strava.activity_mapper import activity_from_strava


@pytest.fixture
def activity_data() -> dict[str, object]:
    return {
        "id": 123,
        "name": "Morning Run",
        "sport_type": "Run",
        "start_date": "2026-09-22T08:00:00Z",
        "distance": 5000.5,
        "moving_time": 1500,
    }


def test_maps_required_fields_and_ignores_extra_fields(activity_data) -> None:
    activity_data["type"] = "DeprecatedType"
    activity_data["unused"] = {"extra": "data"}

    assert activity_from_strava(activity_data) == Activity(
        id=123,
        name="Morning Run",
        sport_type="Run",
        start_date=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
        distance_meters=5000.5,
        moving_time_seconds=1500,
    )


def test_normalizes_offset_date_to_utc(activity_data) -> None:
    activity_data["start_date"] = "2026-09-22T00:30:00+02:00"

    result = activity_from_strava(activity_data)

    assert result.start_date == datetime(2026, 9, 21, 22, 30, tzinfo=timezone.utc)
    assert result.start_date.tzinfo is timezone.utc


@pytest.mark.parametrize("distance", [0, 5000])
def test_accepts_integer_distance_and_zero_moving_time(activity_data, distance) -> None:
    activity_data["distance"] = distance
    activity_data["moving_time"] = 0

    result = activity_from_strava(activity_data)

    assert result.distance_meters == float(distance)
    assert isinstance(result.distance_meters, float)
    assert result.moving_time_seconds == 0


def test_preserves_unknown_sports(activity_data) -> None:
    activity_data["sport_type"] = "FutureSport"

    assert activity_from_strava(activity_data).sport_type == "FutureSport"


@pytest.mark.parametrize(
    "field", ["id", "name", "sport_type", "start_date", "distance", "moving_time"]
)
def test_rejects_missing_required_fields(activity_data, field) -> None:
    del activity_data[field]

    with pytest.raises(ValueError, match=field):
        activity_from_strava(activity_data)


@pytest.mark.parametrize(
    "field", ["id", "name", "sport_type", "start_date", "distance", "moving_time"]
)
def test_rejects_null_required_fields(activity_data, field) -> None:
    activity_data[field] = None

    with pytest.raises(ValueError, match=field):
        activity_from_strava(activity_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", True),
        ("id", 123.0),
        ("id", "123"),
        ("name", 123),
        ("sport_type", []),
        ("start_date", 123),
        ("start_date", "private-invalid-date"),
        ("start_date", "2026-09-22"),
        ("start_date", "2026-09-22T08:00:00"),
        ("start_date", "2026-02-30T08:00:00Z"),
        ("start_date", "0001-01-01T00:00:00+01:00"),
        ("distance", True),
        ("distance", "5000"),
        ("distance", -0.5),
        ("distance", float("nan")),
        ("distance", float("inf")),
        ("distance", float("-inf")),
        pytest.param("distance", 10**400, id="distance-overflow"),
        ("moving_time", True),
        ("moving_time", "1500"),
        ("moving_time", 1500.0),
        ("moving_time", -1),
    ],
)
def test_rejects_invalid_values(activity_data, field, value) -> None:
    activity_data[field] = value

    with pytest.raises(ValueError, match=field) as error:
        activity_from_strava(activity_data)

    assert "private-invalid-date" not in str(error.value)
