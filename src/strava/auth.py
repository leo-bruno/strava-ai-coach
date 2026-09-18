"""Authentication helpers for the Strava API."""

import os
from typing import Any

import requests


STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
REQUIRED_ENVIRONMENT_VARIABLES = (
    "STRAVA_CLIENT_ID",
    "STRAVA_CLIENT_SECRET",
    "STRAVA_REFRESH_TOKEN",
)
TIMEOUT_SECONDS = 10


def refresh_access_token() -> tuple[str, str]:
    """Exchange the configured refresh token for current Strava tokens."""
    configuration = _get_required_configuration()

    try:
        response = requests.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": configuration["STRAVA_CLIENT_ID"],
                "client_secret": configuration["STRAVA_CLIENT_SECRET"],
                "grant_type": "refresh_token",
                "refresh_token": configuration["STRAVA_REFRESH_TOKEN"],
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Could not refresh the Strava access token.") from error

    try:
        token_data: Any = response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Strava returned an invalid token response.") from error

    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise RuntimeError("Strava returned an invalid token response.")

    return access_token, refresh_token


def _get_required_configuration() -> dict[str, str]:
    configuration = {
        variable: os.getenv(variable) for variable in REQUIRED_ENVIRONMENT_VARIABLES
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
