"""Weekly running analysis data shared by analytics and its consumers."""

from dataclasses import dataclass
from datetime import date

from src.models.training_analysis import TrainingType


@dataclass(frozen=True)
class TrainingTypeSummary:
    """Supplied count, distance and moving time, without calculations.

    Distance is in meters, without rounding; moving time is integer seconds.
    Zero distance or time may accompany a positive count. The caller supplies
    all measurements.
    """

    training_type: TrainingType
    activity_count: int
    distance_meters: float
    moving_time_seconds: int


@dataclass(frozen=True)
class WeeklyAnalysis:
    """Supplied weekly results without calculation or validation behavior.

    week_start_date identifies the Monday in the athlete's local calendar.
    Metrics cover only Run activities supplied for that week; they do not
    guarantee a complete activity history. Zero distance, count and moving
    time are valid results. Zero distance or time may accompany a positive
    activity count. Moving time is supplied in integer seconds.
    The caller supplies all fields, including the local Monday date and one
    summary per TrainingType in enum order, with zero for absent categories.
    Category counts sum to running_activity_count; category distances sum to
    running_distance_meters within floating-point precision. Category moving
    times sum exactly to running_moving_time_seconds. The builder
    guarantees this contract; the model does not validate supplied results.
    """

    week_start_date: date
    running_distance_meters: float
    running_activity_count: int
    running_moving_time_seconds: int
    running_structure_by_type: tuple[TrainingTypeSummary, ...]
