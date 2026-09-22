"""Client for the Strava API."""

from typing import Any

import requests

from src.strava.auth import refresh_access_token


ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
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

    def get_activities(
        self,
        before: int | None = None,
        after: int | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """Return the authenticated athlete's activities."""
        params: dict[str, int] = {"page": page, "per_page": per_page}
        if before is not None:
            params["before"] = before
        if after is not None:
            params["after"] = after

        try:
            response = requests.get(
                ACTIVITIES_URL,
                headers={"Authorization": f"Bearer {self._access_token}"},
                params=params,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise RuntimeError("Could not retrieve Strava activities.") from error

        try:
            activities = response.json()
        except ValueError as error:
            raise RuntimeError("Strava returned an invalid activities response.") from error

        if not isinstance(activities, list):
            raise RuntimeError("Strava returned an invalid activities response.")

        return activities
