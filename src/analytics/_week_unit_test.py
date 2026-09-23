"""Unit tests for athlete-local week boundaries."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.analytics._week import _local_week_bounds_utc


@pytest.mark.parametrize(
    ("timezone_name", "reference", "start_utc", "end_utc"),
    [
        (
            "UTC",
            "2026-09-23T12:00:00+00:00",
            "2026-09-21T00:00:00+00:00",
            "2026-09-28T00:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2026-09-23T12:00:00+00:00",
            "2026-09-20T22:00:00+00:00",
            "2026-09-27T22:00:00+00:00",
        ),
        (
            "America/New_York",
            "2026-09-23T12:00:00+00:00",
            "2026-09-21T04:00:00+00:00",
            "2026-09-28T04:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2026-03-29T12:00:00+00:00",
            "2026-03-22T23:00:00+00:00",
            "2026-03-29T22:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2026-10-25T12:00:00+00:00",
            "2026-10-18T22:00:00+00:00",
            "2026-10-25T23:00:00+00:00",
        ),
        (
            "Europe/Madrid",
            "2027-01-01T12:00:00+00:00",
            "2026-12-27T23:00:00+00:00",
            "2027-01-03T23:00:00+00:00",
        ),
    ],
    ids=["utc", "positive-offset", "negative-offset", "spring-dst", "autumn-dst", "new-year"],
)
def test_returns_local_week_bounds_in_utc(
    timezone_name, reference, start_utc, end_utc,
) -> None:
    result = _local_week_bounds_utc(
        reference_datetime=datetime.fromisoformat(reference),
        athlete_timezone=ZoneInfo(timezone_name),
    )

    assert result == (
        datetime.fromisoformat(start_utc),
        datetime.fromisoformat(end_utc),
    )
    assert all(boundary.tzinfo is timezone.utc for boundary in result)


@pytest.mark.parametrize(
    ("timezone_name", "reference", "start_utc", "end_utc"),
    [
        (
            "Europe/Madrid",
            "2026-09-20T22:30:00+00:00",
            "2026-09-20T22:00:00+00:00",
            "2026-09-27T22:00:00+00:00",
        ),
        (
            "America/New_York",
            "2026-09-21T00:30:00+00:00",
            "2026-09-14T04:00:00+00:00",
            "2026-09-21T04:00:00+00:00",
        ),
    ],
)
def test_uses_athlete_local_reference_date(
    timezone_name, reference, start_utc, end_utc,
) -> None:
    assert _local_week_bounds_utc(
        reference_datetime=datetime.fromisoformat(reference),
        athlete_timezone=ZoneInfo(timezone_name),
    ) == (
        datetime.fromisoformat(start_utc),
        datetime.fromisoformat(end_utc),
    )


@pytest.mark.parametrize("reference_timezone", ["UTC", "Europe/Madrid", "America/New_York"])
def test_equivalent_reference_instants_select_same_week(reference_timezone) -> None:
    reference = datetime(2026, 9, 20, 22, 30, tzinfo=timezone.utc)

    assert _local_week_bounds_utc(
        reference_datetime=reference.astimezone(ZoneInfo(reference_timezone)),
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    ) == (
        datetime(2026, 9, 20, 22, tzinfo=timezone.utc),
        datetime(2026, 9, 27, 22, tzinfo=timezone.utc),
    )


def test_rejects_naive_reference() -> None:
    with pytest.raises(ValueError, match="Reference datetime must be timezone-aware"):
        _local_week_bounds_utc(
            reference_datetime=datetime(2026, 9, 23),
            athlete_timezone=ZoneInfo("UTC"),
        )
