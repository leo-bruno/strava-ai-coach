"""Weekly category metrics follow the Run and local-week contracts."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import call, patch
from zoneinfo import ZoneInfo

import pytest

from src.analytics.activity_count import weekly_running_activity_count
from src.analytics.distance import weekly_running_distance
from src.analytics.moving_time import weekly_running_moving_time
from src.analytics.training_type import classify_training_type
from src.analytics.weekly_structure import weekly_running_structure
from src.models.activity import Activity
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary


@pytest.fixture
def activity() -> Activity:
    return Activity(123, "Carrera fácil", "Run",
                    datetime(2026, 9, 23, 8, tzinfo=timezone.utc), 5000.0, 1500)


def analyze(activities, reference):
    options = dict(reference_datetime=reference, athlete_timezone=ZoneInfo("Europe/Madrid"))
    result = weekly_running_structure(activities, **options)
    assert isinstance(result, tuple)
    assert tuple(item.training_type for item in result) == tuple(TrainingType)
    assert all(type(item.activity_count) is int for item in result)
    assert sum(item.activity_count for item in result) == weekly_running_activity_count(activities, **options)
    assert all(type(item.distance_meters) is float for item in result)
    assert sum(item.distance_meters for item in result) == pytest.approx(
        weekly_running_distance(activities, **options), rel=1e-12, abs=1e-9,
    )
    assert all(type(item.moving_time_seconds) is int for item in result)
    assert sum(item.moving_time_seconds for item in result) == weekly_running_moving_time(activities, **options)
    return (
        {item.training_type: item.activity_count for item in result},
        {item.training_type: item.distance_meters for item in result},
        {item.training_type: item.moving_time_seconds for item in result},
    )


@pytest.mark.parametrize("name,kind", [
    ("Carrera fácil", TrainingType.EASY),
    ("Carrera larga", TrainingType.LONG),
    ("Tempo", TrainingType.TEMPO),
    ("Repeticiones: 400 m", TrainingType.INTERVALS),
    ("Contrarreloj", TrainingType.RACE),
    ("Carrera de mañana", TrainingType.OTHER),
    ("Carrera fácil / Tempo", TrainingType.OTHER),
    ("", TrainingType.OTHER),
])
def test_categories_and_absent_categories(activity, name, kind) -> None:
    counts, distances, moving_times = analyze([replace(activity, name=name)], activity.start_date)
    assert counts == {category: int(category is kind) for category in TrainingType}
    assert moving_times == {category: 1500 if category is kind else 0 for category in TrainingType}
    assert distances == {
        category: activity.distance_meters if category is kind else 0.0
        for category in TrainingType
    }


@pytest.mark.parametrize("sport", [None, "Ride", "Walk", "TrailRun", "VirtualRun"])
def test_no_runs_returns_all_six_zero_counts(activity, sport) -> None:
    activities = [] if sport is None else [replace(activity, sport_type=sport)]
    counts, distances, moving_times = analyze(activities, activity.start_date)
    assert counts == dict.fromkeys(TrainingType, 0)
    assert moving_times == dict.fromkeys(TrainingType, 0)
    assert distances == dict.fromkeys(TrainingType, 0.0)


@pytest.mark.parametrize("reference,start,end", [
    ("2026-09-23T12:00:00+00:00", "2026-09-20T22:00:00+00:00", "2026-09-27T22:00:00+00:00"),
    ("2026-03-29T12:00:00+00:00", "2026-03-22T23:00:00+00:00", "2026-03-29T22:00:00+00:00"),
    ("2026-10-25T12:00:00+00:00", "2026-10-18T22:00:00+00:00", "2026-10-25T23:00:00+00:00"),
    ("2027-01-01T12:00:00+00:00", "2026-12-27T23:00:00+00:00", "2027-01-03T23:00:00+00:00"),
], ids=["ordinary", "spring-dst", "autumn-dst", "new-year"])
def test_local_boundaries_select_only_inclusive_start_to_exclusive_end(activity, reference, start, end) -> None:
    start, end = datetime.fromisoformat(start), datetime.fromisoformat(end)
    activities = [
        replace(activity, name="Contrarreloj", start_date=start - timedelta(microseconds=1)),
        replace(activity, name="Carrera larga", start_date=start),
        replace(activity, name="Tempo", start_date=end - timedelta(microseconds=1)),
        replace(activity, name="Repeticiones", start_date=end),
    ]
    counts, distances, moving_times = analyze(activities, datetime.fromisoformat(reference))
    assert counts == {
        TrainingType.EASY: 0, TrainingType.LONG: 1, TrainingType.TEMPO: 1,
        TrainingType.INTERVALS: 0, TrainingType.RACE: 0, TrainingType.OTHER: 0,
    }
    assert distances == {
        TrainingType.EASY: 0.0, TrainingType.LONG: 5000.0, TrainingType.TEMPO: 5000.0,
        TrainingType.INTERVALS: 0.0, TrainingType.RACE: 0.0, TrainingType.OTHER: 0.0,
    }

    assert moving_times == {
        TrainingType.EASY: 0, TrainingType.LONG: 1500, TrainingType.TEMPO: 1500,
        TrainingType.INTERVALS: 0, TrainingType.RACE: 0, TrainingType.OTHER: 0,
    }


def test_each_selected_entry_is_classified_once_without_mutation_or_deduplication(activity) -> None:
    tempo = replace(activity, name="Tempo", distance_meters=0.0, moving_time_seconds=0)
    activities = [tempo, activity, activity, replace(activity),
                  replace(activity, sport_type="Ride"),
                  replace(activity, start_date=activity.start_date + timedelta(days=7))]
    original = [replace(item) for item in activities]
    with patch("src.analytics.weekly_structure.classify_training_type", wraps=classify_training_type) as classifier:
        counts, distances, moving_times = analyze(activities, activity.start_date)
    assert classifier.call_args_list == [call(tempo), call(activity), call(activity), call(activity)]
    assert counts == {
        TrainingType.EASY: 3, TrainingType.LONG: 0, TrainingType.TEMPO: 1,
        TrainingType.INTERVALS: 0, TrainingType.RACE: 0, TrainingType.OTHER: 0,
    }
    assert distances == {
        TrainingType.EASY: 15000.0, TrainingType.LONG: 0.0, TrainingType.TEMPO: 0.0,
        TrainingType.INTERVALS: 0.0, TrainingType.RACE: 0.0, TrainingType.OTHER: 0.0,
    }
    assert moving_times == {
        TrainingType.EASY: 4500, TrainingType.LONG: 0, TrainingType.TEMPO: 0,
        TrainingType.INTERVALS: 0, TrainingType.RACE: 0, TrainingType.OTHER: 0,
    }
    assert activities == original


@pytest.mark.parametrize("empty", [True, False])
def test_naive_reference_is_rejected_even_without_activities(activity, empty) -> None:
    with pytest.raises(ValueError, match="Reference datetime must be timezone-aware"):
        analyze([] if empty else [activity], datetime(2026, 9, 23))


def test_results_are_independent_between_calls(activity) -> None:
    options = dict(reference_datetime=activity.start_date, athlete_timezone=ZoneInfo("Europe/Madrid"))
    first = weekly_running_structure([activity], **options)
    assert weekly_running_structure([], **options) == tuple(TrainingTypeSummary(kind, 0, 0.0, 0) for kind in TrainingType)
    assert first[0] == TrainingTypeSummary(TrainingType.EASY, 1, 5000.0, 1500)
    assert weekly_running_structure([activity], **options) == first


def test_distributes_fractional_meters_without_rounding(activity) -> None:
    activities = [
        replace(activity, distance_meters=1000.1234),
        replace(activity, distance_meters=0.0007),
        replace(activity, name="Carrera larga", distance_meters=15000.2),
        replace(activity, name="Tempo", distance_meters=3000.03),
        replace(activity, name="Repeticiones", distance_meters=4000.004),
        replace(activity, name="Contrarreloj", distance_meters=5000.0005),
        replace(activity, name="Carrera de mañana", distance_meters=600.6789),
    ]
    counts, distances, moving_times = analyze(activities, activity.start_date)
    assert counts == {
        TrainingType.EASY: 2, TrainingType.LONG: 1, TrainingType.TEMPO: 1,
        TrainingType.INTERVALS: 1, TrainingType.RACE: 1, TrainingType.OTHER: 1,
    }
    assert distances == pytest.approx({
        TrainingType.EASY: 1000.1241, TrainingType.LONG: 15000.2,
        TrainingType.TEMPO: 3000.03, TrainingType.INTERVALS: 4000.004,
        TrainingType.RACE: 5000.0005, TrainingType.OTHER: 600.6789,
    }, rel=1e-12, abs=1e-9)


@pytest.mark.parametrize("name,kind", [
    ("Carrera fácil", TrainingType.EASY), ("Carrera de mañana", TrainingType.OTHER),
])
def test_zero_distance_counts_without_changing_category_distance(activity, name, kind) -> None:
    counts, distances, moving_times = analyze([replace(activity, name=name, distance_meters=0.0)], activity.start_date)
    assert counts == {category: int(category is kind) for category in TrainingType}
    assert moving_times == {category: 1500 if category is kind else 0 for category in TrainingType}
    assert distances == dict.fromkeys(TrainingType, 0.0)


@pytest.mark.parametrize("seconds", [0, 91])
def test_distributes_integer_seconds_with_same_counts_and_distances(activity, seconds) -> None:
    activities = [
        replace(activity, moving_time_seconds=seconds),
        replace(activity, moving_time_seconds=17),
        replace(activity, name="Carrera larga", moving_time_seconds=3601),
        replace(activity, name="Tempo", moving_time_seconds=1201),
        replace(activity, name="Repeticiones", moving_time_seconds=1801),
        replace(activity, name="Contrarreloj", moving_time_seconds=901),
        replace(activity, name="Carrera de mañana", moving_time_seconds=61),
    ]
    counts, distances, moving_times = analyze(activities, activity.start_date)
    assert counts == {
        TrainingType.EASY: 2, TrainingType.LONG: 1, TrainingType.TEMPO: 1,
        TrainingType.INTERVALS: 1, TrainingType.RACE: 1, TrainingType.OTHER: 1,
    }
    assert distances == {kind: 5000.0 * count for kind, count in counts.items()}
    assert moving_times == {
        TrainingType.EASY: seconds + 17, TrainingType.LONG: 3601,
        TrainingType.TEMPO: 1201, TrainingType.INTERVALS: 1801,
        TrainingType.RACE: 901, TrainingType.OTHER: 61,
    }
