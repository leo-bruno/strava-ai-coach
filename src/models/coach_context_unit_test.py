"""Immutable evidence representation and explicit provenance contracts."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from src.models.coach_context import (
    EvidenceLimitation, EvidenceProvenance, EvidenceReference,
    PreInterruptionBackground, SourceMetadata, WeeklyEvidence,
)
from src.models.training_analysis import TrainingType


def evidence():
    return WeeklyEvidence(
        "week:2026-09-28", date(2026, 9, 28), 8000.0, 2, 2400,
        tuple((kind, 2 if kind is TrainingType.OTHER else 0) for kind in TrainingType),
        "completed", False, None,
    )


@pytest.mark.parametrize("record,field,value", [
    (SourceMetadata(), "coverage", "complete"),
    (evidence(), "running_activity_count", 4),
    (EvidenceReference("request:goal", EvidenceProvenance.USER_REPORT), "provenance", EvidenceProvenance.DETERMINISTIC),
    (EvidenceLimitation("MISSING_RECENT_WEEKS", "No observation."), "detail", "changed"),
    (PreInterruptionBackground("insight:observed_running:2026-09-07:2026-09-28", (), (evidence(),)), "observations", ()),
])
def test_evidence_records_are_immutable(record, field, value):
    with pytest.raises(FrozenInstanceError):
        setattr(record, field, value)


def test_count_pairs_are_immutable_and_do_not_include_per_type_measurements():
    week = evidence()
    assert week.training_type_counts == tuple(
        (kind, 2 if kind is TrainingType.OTHER else 0) for kind in TrainingType
    )
    assert week.provenance is EvidenceProvenance.STRAVA_OBSERVATION
    with pytest.raises(TypeError):
        week.training_type_counts[0][1] = 5


def test_absent_metadata_is_unknown_rather_than_complete_or_timestamped():
    metadata = SourceMetadata()
    assert metadata.source_name is None
    assert metadata.data_as_of is None
    assert metadata.coverage == "unknown"
    assert metadata.partial_week_dates == ()
