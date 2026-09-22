"""Unit tests for Strava authentication helpers."""

import os
import stat
from unittest.mock import Mock, patch

import pytest, requests
from src.strava import auth
from src.strava.auth import (
    STRAVA_TOKEN_URL,
    TIMEOUT_SECONDS,
    build_authorization_url,
    exchange_authorization_code,
    refresh_access_token,
)


@pytest.fixture(autouse=True)
def isolated_refresh_token_storage(tmp_path, monkeypatch) -> None:
    """Prevent tests from reading or writing the user's local token store."""
    monkeypatch.setattr(auth, "REFRESH_TOKEN_STORAGE_PATH", tmp_path / "refresh_token")


def test_refresh_access_token_returns_tokens_from_valid_response(
    monkeypatch, tmp_path
) -> None:
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
    assert (tmp_path / "refresh_token").read_text(encoding="utf-8") == "new-refresh-token"


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes are required")
def test_refresh_access_token_persists_token_with_owner_only_permissions(
    monkeypatch, tmp_path
) -> None:
    """Stores the latest refresh token in a file readable only by its owner."""
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
        refresh_access_token()

    file_mode = stat.S_IMODE((tmp_path / "refresh_token").stat().st_mode)
    assert file_mode == 0o600


def test_refresh_access_token_prefers_the_persisted_refresh_token(
    monkeypatch, tmp_path
) -> None:
    """Uses the latest stored token instead of the initial shell token."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "stale-shell-refresh-token")
    (tmp_path / "refresh_token").write_text(
        "latest-stored-refresh-token", encoding="utf-8"
    )
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "newer-refresh-token",
    }

    with patch("src.strava.auth.requests.post", return_value=response) as mock_post:
        refresh_access_token()

    assert mock_post.call_args.kwargs["data"]["refresh_token"] == "latest-stored-refresh-token"


def test_build_authorization_url_requests_required_activity_scopes(monkeypatch) -> None:
    """Builds an authorization request for public and full activity read access."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")

    authorization_url = build_authorization_url("http://localhost/exchange_token")

    assert "client_id=test-client-id" in authorization_url
    assert "response_type=code" in authorization_url
    assert "approval_prompt=force" in authorization_url
    assert "scope=read%2Cactivity%3Aread_all" in authorization_url

def test_refresh_access_token_raises_when_client_secret_is_missing(monkeypatch) -> None:
    """Raises a RuntimeError if STRAVA_CLIENT_SECRET is missing."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.delenv("STRAVA_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "existing-refresh-token")


    with patch("src.strava.auth.requests.post") as mock_post:
        with pytest.raises(RuntimeError):
                refresh_access_token()

        mock_post.assert_not_called()

def test_refresh_access_token_raises_when_strava_returns_invalid_response(monkeypatch) -> None:
    """Could not refresh the Strava access token."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "existing-refresh-token")

    response = Mock()
    response.raise_for_status.side_effect = requests.RequestException("Invalid response from Strava")

    with patch("src.strava.auth.requests.post", return_value=response):
        with pytest.raises(
            RuntimeError, match=r"^Could not refresh the Strava access token\.$"
        ):
            refresh_access_token()


def test_refresh_access_token_includes_safe_json_error_details(monkeypatch) -> None:
    """Includes Strava's safe JSON error fields when a refresh is rejected."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "existing-refresh-token")

    response = Mock()
    response.status_code = 400
    response.json.return_value = {
        "message": "Bad Request",
        "error": "invalid_grant",
        "error_description": "Invalid refresh token",
    }
    error = requests.HTTPError()
    error.response = response
    response.raise_for_status.side_effect = error

    with patch("src.strava.auth.requests.post", return_value=response):
        with pytest.raises(
            RuntimeError,
            match=(
                r"^Could not refresh the Strava access token\. "
                r"Strava HTTP status: 400\. "
                r"Strava error: message=Bad Request, error=invalid_grant, "
                r"error_description=Invalid refresh token\.$"
            ),
        ):
            refresh_access_token()


def test_refresh_access_token_includes_status_for_non_json_error(monkeypatch) -> None:
    """Includes only the HTTP status when Strava's error response is not JSON."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "existing-refresh-token")

    response = Mock()
    response.status_code = 400
    response.json.side_effect = ValueError("Invalid JSON")
    error = requests.HTTPError()
    error.response = response
    response.raise_for_status.side_effect = error

    with patch("src.strava.auth.requests.post", return_value=response):
        with pytest.raises(
            RuntimeError,
            match=r"^Could not refresh the Strava access token\. Strava HTTP status: 400\.$",
        ):
            refresh_access_token()


def test_refresh_access_token_raises_when_response_has_no_access_token(monkeypatch) -> None:
    """Raises a RuntimeError when Strava omits the access token."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("STRAVA_REFRESH_TOKEN", "existing-refresh-token")

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"refresh_token": "new-refresh-token"}

    with patch("src.strava.auth.requests.post", return_value=response):
        with pytest.raises(
            RuntimeError, match=r"Strava returned an invalid token response\."
        ):
            refresh_access_token()


def test_exchange_authorization_code_returns_complete_token_response(monkeypatch) -> None:
    """Returns all token data produced by a successful code exchange."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    token_data = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "scope": "activity:read_all",
    }
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = token_data

    with patch("src.strava.auth.requests.post", return_value=response) as mock_post:
        result = exchange_authorization_code("authorization-code")

    assert result == token_data
    mock_post.assert_called_once_with(
        STRAVA_TOKEN_URL,
        data={
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "code": "authorization-code",
            "grant_type": "authorization_code",
        },
        timeout=TIMEOUT_SECONDS,
    )


def test_exchange_authorization_code_raises_when_configuration_is_missing(
    monkeypatch,
) -> None:
    """Fails before making a request when client configuration is incomplete."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.delenv("STRAVA_CLIENT_SECRET", raising=False)

    with patch("src.strava.auth.requests.post") as mock_post:
        with pytest.raises(
            RuntimeError,
            match=r"^Missing required Strava environment variables: STRAVA_CLIENT_SECRET\.$",
        ):
            exchange_authorization_code("authorization-code")

    mock_post.assert_not_called()


def test_exchange_authorization_code_raises_when_request_fails(monkeypatch) -> None:
    """Converts Strava HTTP errors into a clear application error."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    response = Mock()
    response.raise_for_status.side_effect = requests.RequestException("HTTP error")

    with patch("src.strava.auth.requests.post", return_value=response):
        with pytest.raises(
            RuntimeError,
            match=r"^Could not exchange the Strava authorization code\.$",
        ):
            exchange_authorization_code("authorization-code")


@pytest.mark.parametrize("json_result", [ValueError("Invalid JSON"), []])
def test_exchange_authorization_code_raises_for_invalid_response(
    monkeypatch, json_result
) -> None:
    """Rejects malformed JSON and JSON responses that are not objects."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test-client-secret")
    response = Mock()
    response.raise_for_status.return_value = None
    if isinstance(json_result, ValueError):
        response.json.side_effect = json_result
    else:
        response.json.return_value = json_result

    with patch("src.strava.auth.requests.post", return_value=response):
        with pytest.raises(
            RuntimeError,
            match=r"^Strava returned an invalid authorization response\.$",
        ):
            exchange_authorization_code("authorization-code")
