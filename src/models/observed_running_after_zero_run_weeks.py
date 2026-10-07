"""Evidence of observed Run activity following consecutive zero-Run weeks."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ObservedRunningAfterZeroRunWeeks:
    """Supplied evidence without calculations or automatic validation.

    Dates identify local Mondays. The count covers the maximal consecutive
    zero-Run sequence in the supplied history. The following week's count and
    distance are retained exactly, including zero distance with positive count.
    Observed zero Run does not prove inactivity, rest, injury, detraining,
    training interruption or behavioral return. No coverage, calendar closure,
    interpretation or recommendations are inferred.
    """

    first_zero_week_date: date
    observed_zero_week_count: int
    running_week_date: date
    running_week_activity_count: int
    running_week_distance_meters: float
