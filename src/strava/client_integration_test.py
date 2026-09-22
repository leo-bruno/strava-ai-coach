"""Integration tests for the Strava API client and authentication flow."""

from unittest.mock import Mock, patch

from src.strava.auth import STRAVA_TOKEN_URL, TIMEOUT_SECONDS as AUTH_TIMEOUT_SECONDS
from src.strava.client import ATHLETE_URL, TIMEOUT_SECONDS, StravaClient


def test_get_athlete_refreshes_token_and_uses_it_for_athlete_request(
    monkeypatch, tmp_path
) -> None:
    """Refreshes the access token before retrieving the authenticated athlete."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "integration-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "integration-client-secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "integration-refresh-token")

    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {
        "access_token": "integration-access-token",
        "refresh_token": "integration-refresh-token",
    }
    athlete = {"id": 123, "firstname": "Integration", "lastname": "Athlete"}
    athlete_response = Mock()
    athlete_response.raise_for_status.return_value = None
    athlete_response.json.return_value = athlete

    with patch(
        "src.strava.auth.REFRESH_TOKEN_STORAGE_PATH", tmp_path / "refresh_token"
    ):
        with patch(
            "src.strava.auth.requests.post", return_value=token_response
        ) as mock_post:
            with patch(
                "src.strava.client.requests.get", return_value=athlete_response
            ) as mock_get:
                client = StravaClient()
                result = client.get_athlete()

    assert result == athlete
    mock_post.assert_called_once_with(
        STRAVA_TOKEN_URL,
        data={
            "client_id": "integration-client-id",
            "client_secret": "integration-client-secret",
            "grant_type": "refresh_token",
            "refresh_token": "integration-refresh-token",
        },
        timeout=AUTH_TIMEOUT_SECONDS,
    )
    mock_get.assert_called_once_with(
        ATHLETE_URL,
        headers={"Authorization": "Bearer integration-access-token"},
        timeout=TIMEOUT_SECONDS,
    )
    assert (tmp_path / "refresh_token").read_text(encoding="utf-8") == (
        "integration-refresh-token"
    )
