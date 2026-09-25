"""Unit tests for deterministic activity-name classification."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.analytics.training_type import classify_training_type
from src.models.activity import Activity
from src.models.training_analysis import TrainingType


@pytest.fixture
def activity() -> Activity:
    return Activity(
        id=123,
        name="Carrera de mañana",
        sport_type="Run",
        start_date=datetime(2026, 9, 22, 8, tzinfo=timezone.utc),
        distance_meters=5000.0,
        moving_time_seconds=1500,
    )


@pytest.mark.parametrize("case", ["original", "upper", "lower", "swapcase"])
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Carrera fácil: 9 km", TrainingType.EASY),
        ("Carrera fácil: 7,5 km", TrainingType.EASY),
        ("15km Carrera larga", TrainingType.LONG),
        ("10km Carrera larga progresiva", TrainingType.LONG),
        ("Tempo: 5km", TrainingType.TEMPO),
        ("Tempo: 2-1", TrainingType.TEMPO),
        ("Repeticiones: 1 km", TrainingType.INTERVALS),
        ("Repeticiones: 400 m", TrainingType.INTERVALS),
        ("Variantes de 300 m", TrainingType.INTERVALS),
        ("Variantes de 400 m", TrainingType.INTERVALS),
        ("Serie descendente", TrainingType.INTERVALS),
        ("Millas fragmentadas", TrainingType.INTERVALS),
        ("2 km alternos", TrainingType.INTERVALS),
        ("Contrarreloj: 5 km", TrainingType.RACE),
        ("Carrera de mañana", TrainingType.OTHER),
        ("Carrera matutina de lunes", TrainingType.OTHER),
    ],
)
def test_real_examples_ignore_case(activity, name, expected, case) -> None:
    if case != "original":
        name = getattr(name, case)()

    assert classify_training_type(replace(activity, name=name)) is expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("  Carrera\t fa\u0301cil: 9 km  ", TrainingType.EASY),
        ("Carrera facil: 9 km", TrainingType.EASY),
        ("15km Carrera\u00a0larga", TrainingType.LONG),
        ("🏃 (Tempo): 5km", TrainingType.TEMPO),
        ("Variantes de 300m", TrainingType.INTERVALS),
        ("2km alternos", TrainingType.INTERVALS),
        ("1,5 km alternos", TrainingType.INTERVALS),
        ("Repeticiones / Serie descendente", TrainingType.INTERVALS),
    ],
)
def test_known_naming_variations(activity, name, expected) -> None:
    assert classify_training_type(replace(activity, name=name)) is expected


@pytest.mark.parametrize(
    "name",
    [
        "", "   ", "Carrera", "Carrera de 20 km", "5 km en 18 minutos",
        "Carrera progresiva", "Fácil", "Larga", "Variantes de ruta",
        "Serie de fotos", "Millas", "Días alternos", "Temporada de otoño",
        "Pretempo", "TempoX", "Contrarrelojista", "Carrera fácilmente",
        "Carrera largamente esperada", "Prerrepeticiones", "RepeticionesExtra",
        "Variantes de 300 metros cuadrados", "2 km alternosExtra",
    ],
)
def test_generic_or_partial_indicators_return_other(activity, name) -> None:
    assert classify_training_type(replace(activity, name=name)) is TrainingType.OTHER


@pytest.mark.parametrize(
    "name",
    [
        "Carrera fácil / Carrera larga",
        "Tempo / Carrera larga",
        "Contrarreloj / Repeticiones",
        "Repeticiones / Contrarreloj",
        "Carrera fácil / Tempo / Contrarreloj",
    ],
)
def test_conflicting_categories_return_other(activity, name) -> None:
    assert classify_training_type(replace(activity, name=name)) is TrainingType.OTHER


@pytest.mark.parametrize("sport_type", ["Ride", "Walk", "TrailRun", ""])
def test_non_run_activities_return_other(activity, sport_type) -> None:
    activity = replace(activity, name="Tempo: 5km", sport_type=sport_type)

    assert classify_training_type(activity) is TrainingType.OTHER


@pytest.mark.parametrize(
    ("distance_meters", "moving_time_seconds"), [(0.0, 0), (42000.0, 7200)]
)
@pytest.mark.parametrize(
    ("name", "expected"),
    [("Carrera de mañana", TrainingType.OTHER), ("Tempo: 5km", TrainingType.TEMPO)],
)
def test_measurements_do_not_change_classification(
    activity, distance_meters, moving_time_seconds, name, expected
) -> None:
    activity = replace(
        activity,
        name=name,
        distance_meters=distance_meters,
        moving_time_seconds=moving_time_seconds,
    )

    assert classify_training_type(activity) is expected
