"""Client for the Strava API."""

from typing import Any

import requests

from src.strava.auth import refresh_access_token


ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
TIMEOUT_SECONDS = 10


class StravaClient:
    """Provide authenticated access to Strava resources."""

    def __init__(self) -> None:
        self._access_token, _ = refresh_access_token()

    def get_athlete(self) -> dict[str, Any]:
        """Return the authenticated athlete's Strava profile."""
        try:
            response = requests.get(
                ATHLETE_URL,
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise RuntimeError("Could not retrieve the Strava athlete profile.") from error

        try:
            athlete = response.json()
        except ValueError as error:
            raise RuntimeError("Strava returned an invalid athlete response.") from error

        if not isinstance(athlete, dict):
            raise RuntimeError("Strava returned an invalid athlete response.")

        return athlete
