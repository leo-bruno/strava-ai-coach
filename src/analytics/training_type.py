"""Conservative, deterministic classification using known activity-name labels."""

import re
import unicodedata

from src.models.activity import Activity
from src.models.training_analysis import TrainingType


# Whole words/phrases prevent accidental substring matches. Distance labels
# identify named interval sessions, not distance thresholds.
_NAME_RULES = (
    (TrainingType.EASY, r"\bcarrera f[aá]cil\b"),
    (TrainingType.LONG, r"\bcarrera larga\b"),
    (TrainingType.TEMPO, r"\btempo\b"),
    (
        TrainingType.INTERVALS,
        r"\brepeticiones\b"
        r"|\bvariantes de \d+(?:[.,]\d+)?\s*(?:km|m)\b"
        r"|\bserie descendente\b"
        r"|\bmillas fragmentadas\b"
        r"|\b\d+(?:[.,]\d+)?\s*(?:km|m) alternos\b",
    ),
    (TrainingType.RACE, r"\bcontrarreloj\b"),
)


def classify_training_type(activity: Activity) -> TrainingType:
    """Return the sole category explicitly indicated by a running activity name.

    Normalize Unicode, case and whitespace before matching known labels.
    Missing evidence or conflicting categories return Other; no rule takes
    precedence over another. Multiple indicators of the same category agree.
    Generic 'carrera' does not indicate a race. Measurements are not consulted.
    This is label matching, not interpretation of free-form prose or negation.
    """
    if activity.sport_type != "Run":
        return TrainingType.OTHER

    name = " ".join(unicodedata.normalize("NFC", activity.name).casefold().split())
    matches = {
        training_type
        for training_type, pattern in _NAME_RULES
        if re.search(pattern, name)
    }
    if len(matches) == 1:
        return matches.pop()
    return TrainingType.OTHER
