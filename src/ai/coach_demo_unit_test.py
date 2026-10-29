"""Unit tests for the deterministic, synthetic Coach demo fixture."""

import ast
import inspect

from src.ai import coach_demo
from src.ui import coach_request_form
from src.ui.coach_response import render_coach_response


def test_offline_demo_is_fixed_validated_and_explicitly_synthetic():
    context, response, knowledge = coach_demo.build_offline_demo()
    output = render_coach_response(response, context=context, knowledge=knowledge)

    assert context.reference_local_date.isoformat() == "2026-10-08"
    assert context.athlete_timezone.key == "Europe/Madrid"
    assert context.goal.target_date.isoformat() == "2027-04-01"
    assert context.runner_context.runner_context is None
    assert [week.running_distance_meters for week in context.recent_weeks] == [24000, 26000, 28000, 30000]
    assert response.recommendation_period.start.isoformat() == "2026-10-12"
    assert "Synthetic fixture observation" in output
    assert "Synthetic demo goal" in output
    assert "Synthetic demo availability" in output
    assert "user-reported" not in output
    assert "Strava-derived observation" not in output
    assert "pre-recorded" not in output  # The UI carries the provenance warning.


def test_demo_path_has_no_provider_or_strava_dependencies():
    tree = ast.parse(
        inspect.getsource(coach_demo) + "\n" + inspect.getsource(coach_request_form)
    )
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )

    assert not any(module.startswith("src.strava") for module in imported_modules)
    assert "src.ai.coach_manual" not in imported_modules
    assert "openai" not in imported_modules
