"""Map measurements from already-fetched Strava running activities and laps.

No fetching, classification, or complete TrainingAnalysis construction happens
here. Callers must supply running data to the running-specific functions.
"""

from math import isfinite

from src.analytics.pace import moving_pace
from src.models.training_analysis import TrainingLap


def _nonnegative_number(value: object, field: str) -> float:
    message = f"{field} must be a finite nonnegative number."
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(message)
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(message) from None
    if not isfinite(number) or number < 0:
        raise ValueError(message)
    return number


def _optional_number(data: dict[str, object], field: str) -> float | None:
    value = data.get(field)
    return None if value is None else _nonnegative_number(value, field)


def average_heart_rate_from_strava(data: dict[str, object]) -> float | None:
    """Return activity or lap average heart rate in bpm, or None if absent."""
    return _optional_number(data, "average_heartrate")


def maximum_heart_rate_from_strava(data: dict[str, object]) -> float | None:
    """Return activity or lap maximum heart rate in bpm, or None if absent."""
    return _optional_number(data, "max_heartrate")


def running_cadence_from_strava(data: dict[str, object]) -> float | None:
    """Convert running average_cadence from strides/min to individual steps/min.

    Multiply by two for both activity and lap data; 80 API units become 160
    steps/min. Never guess units from the magnitude or apply this to cycling.
    The API reference leaves the cadence unit unspecified. First-hand developer
    reports document the API/UI factor of two and its use with lap cadence:
    https://communityhub.strava.com/developers-api-7/cadence-numbers-from-strava-api-3130
    https://communityhub.strava.com/developers-api-7/step-count-missing-in-detailedactivity-1946
    """
    cadence = _optional_number(data, "average_cadence")
    if cadence is None:
        return None
    return _nonnegative_number(cadence * 2, "average_cadence")


def elevation_gain_from_strava(data: dict[str, object]) -> float | None:
    """Return activity total elevation gain in meters, or None if absent."""
    return _optional_number(data, "total_elevation_gain")


def running_lap_from_strava(data: dict[str, object]) -> TrainingLap:
    """Map a running lap; malformed required or supplied optional fields raise.

    Distance is meters; moving_time is integer seconds, per the API reference:
    https://developers.strava.com/docs/reference/#api-models-Lap
    Zero distance is valid and produces undefined pace, not zero pace.
    """
    if not isinstance(data, dict):
        raise ValueError("Lap must be an object.")
    distance = _nonnegative_number(data.get("distance"), "distance")
    moving_time = data.get("moving_time")
    if (
        not isinstance(moving_time, int)
        or isinstance(moving_time, bool)
        or moving_time < 0
    ):
        raise ValueError("moving_time must be a nonnegative integer.")

    return TrainingLap(
        distance_meters=distance,
        moving_time_seconds=moving_time,
        pace_seconds_per_km=moving_pace(distance, moving_time),
        average_heart_rate_bpm=average_heart_rate_from_strava(data),
        maximum_heart_rate_bpm=maximum_heart_rate_from_strava(data),
        cadence_steps_per_minute=running_cadence_from_strava(data),
    )


def running_laps_from_strava(data: dict[str, object]) -> tuple[TrainingLap, ...]:
    """Map a detailed running activity's laps in response order, without labels.

    Missing/null laps produce an empty tuple. Invalid collections or entries
    raise ValueError; an invalid entry's error includes its zero-based index.
    """
    laps = data.get("laps")
    if laps is None:
        return ()
    if not isinstance(laps, list):
        raise ValueError("laps must be a list.")
    result = []
    for index, lap in enumerate(laps):
        try:
            result.append(running_lap_from_strava(lap))
        except ValueError as error:
            raise ValueError(f"laps[{index}]: {error}") from None
    return tuple(result)
