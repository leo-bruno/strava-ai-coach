"""Unit tests for Strava authentication helpers."""

from unittest.mock import Mock, patch

from src.strava.auth import refresh_access_token


def test_refresh_access_token_returns_tokens_from_valid_response(monkeypatch) -> None:
    """Returns the access and refresh tokens from Strava's response."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "existing-refresh-token")

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
    }

    with patch("src.strava.auth.requests.post", return_value=response):
        tokens = refresh_access_token()

    assert tokens == ("new-access-token", "new-refresh-token")
