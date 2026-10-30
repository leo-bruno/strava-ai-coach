"""Run the real form logic against a narrow mock of Streamlit's widget API."""

from contextlib import nullcontext
from datetime import date, datetime, timedelta
import builtins
from zoneinfo import ZoneInfo

import pytest

from src.models.coach_request import CoachRequest, coach_request_from_input
from src.ui.coach_request_form import FORM_WIDGET_KEYS, REQUEST_SESSION_KEY, render_request_page
from src.ui.timezone_preference import ATHLETE_TIMEZONE_LAST_APPLIED_KEY, ATHLETE_TIMEZONE_KEY


class MockStreamlit:
    """Widget values and output capture only; request behavior stays in the page."""

    def __init__(self, *, values=None, submitted=True, clear_clicked=False, session_state=None):
        self.values = values or {}
        self.submitted = submitted
        self.authorization_submitted = False
        self.weekly_submitted = False
        self.evidence_submitted = False
        self.clear_clicked = clear_clicked
        self.session_state = session_state if session_state is not None else {}
        self.output = []
        self.errors = []
        self.widget_options = {}

    def form(self, _key):
        return nullcontext()

    def title(self, value):
        self.output.append(value)

    def subheader(self, value):
        self.output.append(value)

    def write(self, value):
        self.output.append(value)

    def info(self, value):
        self.output.append(value)

    def warning(self, value):
        self.output.append(value)

    def success(self, value):
        self.output.append(value)

    def error(self, value):
        self.errors.append(value)
        self.output.append(value)

    def text_input(self, _label, *, key=None, value="", **_kwargs):
        return self.values.get(key, value)

    def selectbox(self, _label, options, *, key, index=None, **kwargs):
        self.widget_options[key] = {"options": options, "index": index, **kwargs}
        if key in self.values:
            selected = self.values[key]
        else:
            selected = None if index is None else options[index]
        self.session_state[key] = selected
        return selected

    def date_input(self, _label, *, key, value, **_kwargs):
        self.widget_options[key] = _kwargs
        return self.values.get(key, value)

    def number_input(self, _label, *, key, value, **_kwargs):
        return self.values.get(key, value)

    def text_area(self, _label, *, key, **_kwargs):
        return self.values.get(key, "")

    def form_submit_button(self, _label, *, key=None):
        return {
            "validate_coach_request": self.submitted,
            "prepare_strava_authorization": self.authorization_submitted,
            "load_weekly_strava_overview": self.weekly_submitted,
            "prepare_coach_evidence_context": self.evidence_submitted,
        }.get(key, False)

    def button(self, _label, *, key=None, on_click=None, args=(), **_kwargs):
        if self.clear_clicked and key == "clear_request_form" and on_click is not None:
            on_click(*args)
        return self.clear_clicked and key == "clear_request_form"

    def link_button(self, _label, _url, **_kwargs):
        return None


def form_values(**overrides):
    values = {
        "target_date": date.today() + timedelta(days=30),
        "available_training_days": 4,
        "athlete_timezone": "Europe/Madrid",
        "runner_context": "",
    }
    values.update(overrides)
    return values


def valid_request():
    values = form_values()
    return coach_request_from_input(
        {
            "goal": {
                "goal_type": "HALF_MARATHON",
                "target_date": values["target_date"].isoformat(),
            },
            "constraints": {"available_training_days_per_week": values["available_training_days"]},
            "runner_context": None,
        },
        reference_datetime=datetime.now(ZoneInfo("UTC")),
        athlete_timezone=ZoneInfo("Europe/Madrid"),
    )


@pytest.fixture
def forbid_coach_and_strava_imports(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "src.ai.coach" or name.startswith("src.strava"):
            raise AssertionError(f"Unexpected product integration import: {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)


def test_valid_submission_stores_request_and_hides_runner_context(forbid_coach_and_strava_imports):
    private_context = "PRIVATE RUNNER CONTEXT 7f92a"
    ui = MockStreamlit(values=form_values(runner_context=private_context))

    render_request_page(ui)

    request = ui.session_state[REQUEST_SESSION_KEY]
    assert isinstance(request, CoachRequest)
    assert request.goal.target_date == ui.values["target_date"]
    assert request.constraints.available_training_days_per_week == 4
    assert request.context.runner_context == private_context
    visible_output = " ".join(map(str, ui.output))
    assert private_context not in visible_output
    assert "Request validated and kept in this session." in visible_output
    assert "No training advice has been generated" in visible_output
    assert "Request validation itself does not access Strava" in visible_output
    assert set(ui.session_state) == {
        REQUEST_SESSION_KEY,
        ATHLETE_TIMEZONE_KEY,
        ATHLETE_TIMEZONE_LAST_APPLIED_KEY,
    }


def test_target_picker_does_not_block_date_valid_in_selected_timezone():
    athlete_timezone = ZoneInfo("Pacific/Honolulu")
    local_tomorrow = datetime.now(athlete_timezone).date() + timedelta(days=1)
    ui = MockStreamlit(values=form_values(
        target_date=local_tomorrow,
        athlete_timezone=athlete_timezone.key,
    ))

    render_request_page(ui)

    assert REQUEST_SESSION_KEY in ui.session_state
    assert ui.session_state[REQUEST_SESSION_KEY].goal.target_date == local_tomorrow
    assert "min_value" not in ui.widget_options["target_date"]


@pytest.mark.parametrize("timezone_name", [None, "", 17, "Not/A_Timezone"])
def test_timezone_resolver_defensively_rejects_missing_or_malformed_values(timezone_name):
    from src.ui.coach_request_form import _resolve_coach_timezone

    with pytest.raises(ValueError):
        _resolve_coach_timezone(timezone_name)


@pytest.mark.parametrize(
    "overrides,error_fragment",
    [
        ({"athlete_timezone": "Not/A_Timezone"}, "Select a valid IANA time zone"),
        ({"target_date": datetime.now(ZoneInfo("Europe/Madrid")).date() - timedelta(days=1)}, "strictly after"),
        ({"target_date": datetime.now(ZoneInfo("Europe/Madrid")).date()}, "strictly after"),
    ],
)
def test_invalid_timezone_or_target_date_clears_old_request(overrides, error_fragment):
    previous_request = object()
    ui = MockStreamlit(
        values=form_values(**overrides),
        session_state={REQUEST_SESSION_KEY: previous_request},
    )

    render_request_page(ui)

    assert REQUEST_SESSION_KEY not in ui.session_state
    assert len(ui.errors) == 1
    assert error_fragment in ui.errors[0]


def test_unsubmitted_form_keeps_only_existing_session_request():
    previous_request = valid_request()
    ui = MockStreamlit(
        values=form_values(),
        submitted=False,
        session_state={REQUEST_SESSION_KEY: previous_request},
    )

    render_request_page(ui)

    assert ui.session_state == {
        REQUEST_SESSION_KEY: previous_request,
        ATHLETE_TIMEZONE_KEY: "Europe/Madrid",
        ATHLETE_TIMEZONE_LAST_APPLIED_KEY: "Europe/Madrid",
    }
    assert "Request summary" in ui.output
    assert not ui.errors


def test_clear_form_removes_draft_values_and_suppresses_request_output():
    draft_values = form_values(runner_context="private draft")
    state = {key: draft_values[key] for key in FORM_WIDGET_KEYS}
    state["athlete_timezone"] = draft_values["athlete_timezone"]
    ui = MockStreamlit(
        values=form_values(runner_context="private draft"),
        submitted=False,
        clear_clicked=True,
        session_state=state,
    )

    render_request_page(ui)

    assert ui.session_state == {
        ATHLETE_TIMEZONE_KEY: "Europe/Madrid",
        ATHLETE_TIMEZONE_LAST_APPLIED_KEY: "Europe/Madrid",
    }
    assert not ui.errors
    assert "Request summary" not in ui.output
    assert "Request validated and kept in this session." not in ui.output
    assert "private draft" not in " ".join(map(str, ui.output))


def test_clear_form_removes_a_previously_validated_request():
    state = {REQUEST_SESSION_KEY: valid_request()}
    validated_values = form_values(runner_context="private validated context")
    state.update({key: validated_values[key] for key in FORM_WIDGET_KEYS})
    state["athlete_timezone"] = validated_values["athlete_timezone"]
    ui = MockStreamlit(
        values=form_values(runner_context="private validated context"),
        submitted=False,
        clear_clicked=True,
        session_state=state,
    )

    render_request_page(ui)

    assert ui.session_state == {
        ATHLETE_TIMEZONE_KEY: "Europe/Madrid",
        ATHLETE_TIMEZONE_LAST_APPLIED_KEY: "Europe/Madrid",
    }
    assert "Request summary" not in ui.output
    assert "private validated context" not in " ".join(map(str, ui.output))
