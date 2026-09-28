"""Build a running analysis from an Activity and already-fetched Strava data."""

from src.analytics.pace import average_moving_pace
from src.analytics.training_type import classify_training_type
from src.models.activity import Activity
from src.models.training_analysis import TrainingAnalysis
from src.strava.training_mapper import (
    average_heart_rate_from_strava,
    elevation_gain_from_strava,
    maximum_heart_rate_from_strava,
    running_cadence_from_strava,
    running_laps_from_strava,
)


def training_analysis_from_strava(
    activity: Activity, data: dict[str, object]
) -> TrainingAnalysis:
    """Combine typed activity fields with detailed running measurements.

    Only the project's supported running sport, Run, is accepted. A supplied
    detailed id must be an integer matching activity.id; it may be omitted.
    The Activity supplies classification and pace inputs. Detailed measurements
    and laps use the existing mappers, including their missing-data behavior
    and ValueErrors for malformed values. Neither input is modified.
    """
    if activity.sport_type != "Run":
        raise ValueError("Training analysis supports only sport_type 'Run'.")
    if not isinstance(data, dict):
        raise ValueError("Detailed activity data must be an object.")
    if "id" in data:
        detailed_id = data["id"]
        if not isinstance(detailed_id, int) or isinstance(detailed_id, bool):
            raise ValueError("Detailed activity id must be an integer.")
        if detailed_id != activity.id:
            raise ValueError("Detailed activity id must match Activity.id.")

    return TrainingAnalysis(
        activity=activity,
        training_type=classify_training_type(activity),
        average_pace_seconds_per_km=average_moving_pace(activity),
        average_heart_rate_bpm=average_heart_rate_from_strava(data),
        maximum_heart_rate_bpm=maximum_heart_rate_from_strava(data),
        cadence_steps_per_minute=running_cadence_from_strava(data),
        elevation_gain_meters=elevation_gain_from_strava(data),
        laps=running_laps_from_strava(data),
    )
