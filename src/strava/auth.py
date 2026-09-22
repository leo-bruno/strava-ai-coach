"""Authentication helpers for the Strava API."""

import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import urlencode

import requests


STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
REQUIRED_ENVIRONMENT_VARIABLES = (
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REFRESH_TOKEN",
)
CLIENT_CONFIGURATION_VARIABLES = (
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
)
AUTHORIZATION_CODE_REQUIRED_ENVIRONMENT_VARIABLES = (
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
)
AUTHORIZATION_URL = "https://www.strava.com/oauth/authorize"
REQUESTED_AUTHORIZATION_SCOPES = ("read", "activity:read_all")
REFRESH_TOKEN_STORAGE_PATH = Path.home() / ".strava-ai-coach" / "refresh_token"
TIMEOUT_SECONDS = 10


def refresh_access_token() -> tuple[str, str]:
    """Exchange the configured refresh token for current Strava tokens."""
    configuration = _get_required_configuration(CLIENT_CONFIGURATION_VARIABLES)
    refresh_token = _load_refresh_token()

    try:
        response = requests.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": configuration["STRAVA_CLIENT_ID"],
                "client_secret": configuration["STRAVA_CLIENT_SECRET"],
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        message = "Could not refresh the Strava access token."
        details = _get_safe_strava_error_details(error)
        if details:
            message = f"{message} {details}"
        raise RuntimeError(message) from error

    try:
        token_data: Any = response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Strava returned an invalid token response.") from error

    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise RuntimeError("Strava returned an invalid token response.")

    persist_refresh_token(refresh_token)
    return access_token, refresh_token


def build_authorization_url(redirect_uri: str) -> str:
    """Build a Strava authorization URL for the scopes required by this project."""
    configuration = _get_required_configuration(("STRAVA_CLIENT_ID",))
    return f"{AUTHORIZATION_URL}?{urlencode({
        'client_id': configuration['STRAVA_CLIENT_ID'],
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'approval_prompt': 'force',
        'scope': ','.join(REQUESTED_AUTHORIZATION_SCOPES),
    })}"


def exchange_authorization_code(authorization_code: str) -> dict[str, Any]:
    """Exchange an authorization code for Strava token data."""
    configuration = _get_required_configuration(
        AUTHORIZATION_CODE_REQUIRED_ENVIRONMENT_VARIABLES
    )

    try:
        response = requests.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": configuration["STRAVA_CLIENT_ID"],
                "client_secret": configuration["STRAVA_CLIENT_SECRET"],
                "code": authorization_code,
                "grant_type": "authorization_code",
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Could not exchange the Strava authorization code.") from error

    try:
        token_data: Any = response.json()
    except ValueError as error:
        raise RuntimeError("Strava returned an invalid authorization response.") from error

    if not isinstance(token_data, dict):
        raise RuntimeError("Strava returned an invalid authorization response.")

    return token_data


def persist_refresh_token(refresh_token: str) -> None:
    """Store a refresh token locally with owner-only file permissions."""
    if not refresh_token:
        raise RuntimeError("Cannot persist an empty Strava refresh token.")

    storage_directory = REFRESH_TOKEN_STORAGE_PATH.parent
    temporary_path: Path | None = None
    try:
        storage_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        storage_directory.chmod(0o700)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=storage_directory,
            prefix=".refresh_token.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_path.chmod(0o600)
            temporary_file.write(refresh_token)

        temporary_path.replace(REFRESH_TOKEN_STORAGE_PATH)
        REFRESH_TOKEN_STORAGE_PATH.chmod(0o600)
    except OSError as error:
        raise RuntimeError("Could not persist the latest Strava refresh token.") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _load_refresh_token() -> str:
    """Return the locally persisted token or the initial environment token."""
    try:
        refresh_token = REFRESH_TOKEN_STORAGE_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        refresh_token = os.getenv("STRAVA_REFRESH_TOKEN", "")
    except OSError as error:
        raise RuntimeError("Could not read the stored Strava refresh token.") from error

    if not refresh_token:
        raise RuntimeError(
            "Missing required Strava environment variables: STRAVA_REFRESH_TOKEN."
        )

    return refresh_token


def _get_required_configuration(
    required_variables: tuple[str, ...] = REQUIRED_ENVIRONMENT_VARIABLES,
) -> dict[str, str]:
    configuration = {
        variable: os.getenv(variable) for variable in required_variables
    }
    missing_variables = [
        variable for variable, value in configuration.items() if not value
    ]
    if missing_variables:
        raise RuntimeError(
            "Missing required Strava environment variables: "
            f"{', '.join(missing_variables)}."
        )

    return {variable: value for variable, value in configuration.items() if value}


def _get_safe_strava_error_details(error: requests.RequestException) -> str:
    """Return non-sensitive details from a failed Strava HTTP response."""
    response = error.response
    if response is None:
        return ""

    try:
        error_data: Any = response.json()
    except ValueError:
        return f"Strava HTTP status: {response.status_code}."

    if isinstance(error_data, dict):
        safe_fields = [
            f"{field}={error_data[field]}"
            for field in ("message", "error", "error_description")
            if isinstance(error_data.get(field), str) and error_data[field]
        ]
        if safe_fields:
            return (
                f"Strava HTTP status: {response.status_code}. "
                f"Strava error: {', '.join(safe_fields)}."
            )

    return f"Strava HTTP status: {response.status_code}."
