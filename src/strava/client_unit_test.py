"""Unit tests for the Strava API client."""

from unittest.mock import Mock, patch

import pytest, requests

from src.strava.client import ATHLETE_URL, TIMEOUT_SECONDS, StravaClient


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
