"""Unit tests for the Strava API client."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from src.models.activity import Activity
from src.strava.client import ACTIVITIES_URL, ATHLETE_URL, TIMEOUT_SECONDS, StravaClient


def test_get_athlete_returns_athlete_from_valid_response() -> None:
    """Returns the athlete dictionary from Strava's response."""
    athlete = {"id": 123, "firstname": "Test", "lastname": "Athlete"}
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = athlete

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response) as mock_get:
            client = StravaClient()
            result = client.get_athlete()

    assert result == athlete
    assert client._refresh_token == "test-refresh-token"
    mock_get.assert_called_once_with(
        ATHLETE_URL,
        headers={"Authorization": "Bearer test-access-token"},
        timeout=TIMEOUT_SECONDS,
    )


def test_get_athlete_raises_when_strava_returns_an_http_error() -> None:
    """Raises a RuntimeError when Strava returns an HTTP error."""
    response = Mock()
    response.raise_for_status.side_effect = requests.RequestException("HTTP error")

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response):
            client = StravaClient()

            with pytest.raises(
                RuntimeError, match=r"^Could not retrieve the Strava athlete profile\.$"
            ):
                client.get_athlete()


def test_get_athlete_raises_when_strava_returns_invalid_json() -> None:
    """Raises a RuntimeError when Strava returns invalid JSON."""
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("Invalid JSON")

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response):
            client = StravaClient()

            with pytest.raises(
                RuntimeError, match=r"^Strava returned an invalid athlete response\.$"
            ):
                client.get_athlete()


def test_get_athlete_raises_when_strava_returns_a_non_dictionary_response() -> None:
    """Raises a RuntimeError when Strava returns a non-dictionary response."""
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = ["unexpected", "response"]

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response):
            client = StravaClient()

            with pytest.raises(
                RuntimeError, match=r"^Strava returned an invalid athlete response\.$"
            ):
                client.get_athlete()


def test_get_activities_returns_activities_and_sends_optional_parameters() -> None:
    """Returns activity data and includes supplied pagination parameters."""
    activities = [
        {
            "id": activity_id,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date": "2026-09-22T08:00:00Z",
            "distance": 5000.5,
            "moving_time": 1500,
        }
        for activity_id in (123, 456)
    ]
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = activities

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response) as mock_get:
            client = StravaClient()
            result = client.get_activities(before=200, after=100, page=2, per_page=50)

    assert result == [
        Activity(
            id=activity_id,
            name="Morning Run",
            sport_type="Run",
            start_date=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
            distance_meters=5000.5,
            moving_time_seconds=1500,
        )
        for activity_id in (123, 456)
    ]
    mock_get.assert_called_once_with(
        ACTIVITIES_URL,
        headers={"Authorization": "Bearer test-access-token"},
        params={"before": 200, "after": 100, "page": 2, "per_page": 50},
        timeout=TIMEOUT_SECONDS,
    )


def test_get_activities_omits_missing_date_parameters() -> None:
    """Does not send date filters when none are supplied."""
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = []

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response) as mock_get:
            client = StravaClient()
            result = client.get_activities()

    assert result == []
    assert mock_get.call_args.kwargs["params"] == {"page": 1, "per_page": 30}


def test_get_activities_raises_when_strava_returns_invalid_json() -> None:
    """Raises a RuntimeError when Strava returns invalid JSON."""
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("Invalid JSON")

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response):
            client = StravaClient()

            with pytest.raises(
                RuntimeError, match=r"^Strava returned an invalid activities response\.$"
            ):
                client.get_activities()


def test_get_activities_raises_when_strava_returns_a_non_list_response() -> None:
    """Raises a RuntimeError when Strava returns a non-list response."""
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"unexpected": "response"}

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response):
            client = StravaClient()

            with pytest.raises(
                RuntimeError, match=r"^Strava returned an invalid activities response\.$"
            ):
                client.get_activities()


def test_get_activities_raises_when_strava_returns_an_http_error() -> None:
    """Raises a RuntimeError when Strava returns an HTTP error."""
    response = Mock()
    response.raise_for_status.side_effect = requests.RequestException("HTTP error")

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response):
            client = StravaClient()

            with pytest.raises(RuntimeError, match=r"^Could not retrieve Strava activities\.$"):
                client.get_activities()


@pytest.mark.parametrize("invalid_activity", [None, [], "invalid", {"id": 456}])
def test_get_activities_rejects_invalid_items_without_returning_partial_results(
    invalid_activity,
) -> None:
    """Rejects malformed items even when earlier activities are valid."""
    response = Mock()
    response.json.return_value = [
        {
            "id": 123,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date": "2026-09-22T08:00:00Z",
            "distance": 5000,
            "moving_time": 1500,
        },
        invalid_activity,
    ]

    with patch(
        "src.strava.client.refresh_access_token",
        return_value=("test-access-token", "test-refresh-token"),
    ):
        with patch("src.strava.client.requests.get", return_value=response):
            client = StravaClient()

            with pytest.raises(
                RuntimeError, match=r"^Strava returned an invalid activities response\.$"
            ) as error:
                client.get_activities()

    if isinstance(invalid_activity, dict):
        assert isinstance(error.value.__cause__, ValueError)
