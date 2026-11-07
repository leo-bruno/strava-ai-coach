"""Session-only Coach request, evidence and experimental response UI."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.ai.coach_demo import build_offline_demo
from src.models.coach_request import coach_request_from_input
from src.ui.coach_evidence_context import (
    COACH_EVIDENCE_CONTEXT_KEY,
    coach_evidence_context_guidance,
    clear_coach_evidence_context,
    prepare_coach_evidence_context,
    render_coach_evidence_context,
)
from src.ui.coach_response import render_coach_response
from src.ui.dashboard import set_dashboard_view
from src.ui.strava_connection import ACCESS_TOKEN_KEY
from src.ui.strava_weekly_overview import WEEKLY_ANALYSES_KEY
from src.ui.timezone_preference import (
    ATHLETE_TIMEZONE_KEY,
    ATHLETE_TIMEZONE_LAST_APPLIED_KEY,
    IANA_TIMEZONE_OPTIONS,
    is_valid_iana_timezone_name,
)


REQUEST_SESSION_KEY = "validated_coach_request"
DEMO_SESSION_KEY = "offline_coach_demo_output"
GENERATED_COACH_OUTPUT_KEY = "experimental_coach_output"
FORM_WIDGET_KEYS = (
    "target_date",
    "available_training_days",
    "runner_context",
)


def _resolve_coach_timezone(timezone_name: object) -> ZoneInfo:
    if not isinstance(timezone_name, str) or not timezone_name:
        raise ValueError("Select an IANA time zone before validating the request.")
    if not is_valid_iana_timezone_name(timezone_name):
        raise ValueError("Select a valid IANA time zone before validating the request.")
    try:
        return ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError("Select a valid IANA time zone before validating the request.") from None


def _clear_request_form(session_state) -> None:
    session_state.pop(REQUEST_SESSION_KEY, None)
    session_state.pop(DEMO_SESSION_KEY, None)
    session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
    clear_coach_evidence_context(session_state)
    for key in FORM_WIDGET_KEYS:
        session_state.pop(key, None)


def _request_data(target_date, available_days, runner_context) -> dict[str, object]:
    return {
        "goal": {"goal_type": "HALF_MARATHON", "target_date": target_date.isoformat()},
        "constraints": {"available_training_days_per_week": available_days},
        "runner_context": runner_context,
    }


def _offline_demo_output() -> str:
    context, response, knowledge = build_offline_demo()
    return render_coach_response(response, context=context, knowledge=knowledge)


def _generate_experimental_coach_output(context) -> str:
    """Run the existing one-shot Coach boundary and render only validated output."""
    from src.ai.coach import generate_coach_response
    from src.ai.training_knowledge import load_training_knowledge

    knowledge = load_training_knowledge()
    response = generate_coach_response(context)
    return render_coach_response(response, context=context, knowledge=knowledge)


def _coach_styles(ui) -> None:
    ui.markdown(
        """<style>
        @import url("https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap");
        .st-key-coach-panel, .st-key-coach-response-panel {
            font-family: "Manrope", "Helvetica Neue", system-ui, sans-serif;
            background: radial-gradient(ellipse at 96% 95%, #8f3037, #351719 56%, #180f10);
            border: 1px solid #593437; border-radius: 20px; padding: 1rem 1.2rem;
            margin: .4rem 0 1rem;
        }
        .st-key-coach-panel [data-testid="stMarkdownContainer"] p,
        .st-key-coach-panel [data-testid="stCaptionContainer"] p,
        .st-key-coach-panel label,
        .st-key-coach-response-panel [data-testid="stMarkdownContainer"] p {
            color: #f2e9e9 !important; font-family: inherit;
        }
        .st-key-coach-panel [data-testid="stTextArea"] textarea {
            min-height: 4.5rem; background: #251819; color: #fff; border-color: #76575a;
        }
        .st-key-coach-panel button { background: #ffffff24; color: #fff; border: 1px solid #ffffff55; }
        .st-key-coach-panel button:focus-visible, .st-key-coach-panel textarea:focus-visible {
            outline: 2px solid #57d5dc; outline-offset: 2px;
        }
        @media(max-width: 680px) {
            .st-key-coach-panel, .st-key-coach-response-panel { padding: .8rem; }
            .st-key-coach-panel button { width: 100%; }
        }
        </style>""",
        unsafe_allow_html=True,
    )


def render_request_page(ui=None) -> None:
    """Render Coach controls; Strava connection and fetching live in Estadísticas."""
    if ui is None:
        import streamlit as ui

    _coach_styles(ui)
    ui.title("Coach")
    ui.caption(
        "Valida una solicitud o prepara una respuesta experimental tras una acción explícita. "
        "No se consulta Strava desde esta pantalla."
    )
    if not ui.session_state.get(ACCESS_TOKEN_KEY):
        ui.info("Conecta Strava y carga un resumen semanal desde Estadísticas para preparar evidencia y generar una respuesta.")
    elif ui.session_state.get(WEEKLY_ANALYSES_KEY) is None:
        ui.info("Carga el resumen de siete semanas desde Estadísticas para habilitar el contexto de evidencia del Coach.")
    if ui.button("Abrir Estadísticas", key="open-stats-from-coach"):
        set_dashboard_view(ui.session_state, "Estadísticas")
        ui.rerun()

    generation_error = False
    evidence_error = None
    timezone_name = ui.session_state.get(ATHLETE_TIMEZONE_KEY)
    with ui.form("coach_request_form"):
        ui.text_input("Goal", value="Half marathon", disabled=True)
        timezone_name = ui.selectbox(
            "Your time zone",
            options=IANA_TIMEZONE_OPTIONS,
            index=(IANA_TIMEZONE_OPTIONS.index(timezone_name) if timezone_name in IANA_TIMEZONE_OPTIONS else None),
            placeholder="Select an IANA time zone",
            key=ATHLETE_TIMEZONE_KEY,
        )
        ui.session_state.setdefault(ATHLETE_TIMEZONE_LAST_APPLIED_KEY, timezone_name)
        target_date = ui.date_input(
            "Target date",
            value=date.today() + timedelta(days=30),
            key="target_date",
        )
        available_days = ui.number_input(
            "Available training days per week",
            min_value=0,
            max_value=7,
            value=0,
            step=1,
            key="available_training_days",
        )
        runner_context = ui.text_area(
            "Optional context for the Coach",
            max_chars=2000,
            height=80,
            help="Up to 2,000 characters. This text is not shown in the confirmation.",
            key="runner_context",
        )
        coach_submitted = ui.form_submit_button(
            "Validate request", key="validate_coach_request", type="primary"
        )
        evidence_guidance = coach_evidence_context_guidance(
            ui.session_state, timezone_name, datetime.now(timezone.utc)
        )
        evidence_available = evidence_guidance is None
        if not evidence_available:
            clear_coach_evidence_context(ui.session_state)
            ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
        with ui.container(key="coach-panel"):
            ui.subheader("Evidence context")
            ui.caption(
                "Prepare deterministic evidence or generate a response. Both actions use the current request and loaded weekly summary."
            )
            if evidence_available:
                evidence_submitted = ui.form_submit_button(
                    "Prepare Coach evidence context",
                    key="prepare_coach_evidence_context",
                    type="secondary",
                )
                ui.warning(
                    "Experimental: the model has not been accepted and its latest semantic evaluation failed. "
                    "Generating sends your request (including optional context) and Strava-derived weekly evidence "
                    "to OpenAI; provider charges may apply. This is not a verified training plan."
                )
                generation_submitted = ui.form_submit_button(
                    "Generate experimental Coach response",
                    key="generate_experimental_coach_response",
                    type="secondary",
                )
            else:
                evidence_submitted = False
                generation_submitted = False
                ui.caption(evidence_guidance)

    if coach_submitted:
        clear_coach_evidence_context(ui.session_state)
        ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
        ui.session_state.pop(REQUEST_SESSION_KEY, None)
        try:
            request = coach_request_from_input(
                _request_data(target_date, available_days, runner_context),
                reference_datetime=datetime.now(timezone.utc),
                athlete_timezone=_resolve_coach_timezone(timezone_name),
            )
        except (ValueError, ZoneInfoNotFoundError) as error:
            ui.error(str(error))
        else:
            ui.session_state[REQUEST_SESSION_KEY] = request
            ui.success("Request validated and kept in this session.")
    elif evidence_submitted:
        clear_coach_evidence_context(ui.session_state)
        ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
        ui.session_state.pop(REQUEST_SESSION_KEY, None)
        try:
            request, context = prepare_coach_evidence_context(
                ui.session_state,
                _request_data(target_date, available_days, runner_context),
                timezone_name,
                datetime.now(timezone.utc),
            )
        except ValueError as error:
            evidence_error = str(error)
        except Exception:
            evidence_error = "Could not prepare the Coach evidence context from the current request and weekly data."
        else:
            ui.session_state[REQUEST_SESSION_KEY] = request
            ui.session_state[COACH_EVIDENCE_CONTEXT_KEY] = context
    elif generation_submitted:
        clear_coach_evidence_context(ui.session_state)
        ui.session_state.pop(GENERATED_COACH_OUTPUT_KEY, None)
        ui.session_state.pop(REQUEST_SESSION_KEY, None)
        try:
            request, context = prepare_coach_evidence_context(
                ui.session_state,
                _request_data(target_date, available_days, runner_context),
                timezone_name,
                datetime.now(timezone.utc),
            )
            rendered_response = _generate_experimental_coach_output(context)
        except Exception:
            generation_error = True
        else:
            ui.session_state[REQUEST_SESSION_KEY] = request
            ui.session_state[COACH_EVIDENCE_CONTEXT_KEY] = context
            ui.session_state[GENERATED_COACH_OUTPUT_KEY] = rendered_response

    ui.button(
        "Clear Coach request, evidence and demo",
        key="clear_request_form",
        on_click=_clear_request_form,
        args=(ui.session_state,),
    )
    if evidence_error is not None:
        ui.error(evidence_error)
    if generation_error:
        ui.error("Coach generation failed or its response could not be validated. No response was displayed; select the button to try again.")

    request = ui.session_state.get(REQUEST_SESSION_KEY)
    if request is not None:
        ui.subheader("Request summary")
        ui.write(f"Goal: {request.goal.goal_type.value.replace('_', ' ').title()}")
        ui.write(f"Target date: {request.goal.target_date.isoformat()}")
        ui.write("Available training days per week: " f"{request.constraints.available_training_days_per_week}")
        if ui.session_state.get(COACH_EVIDENCE_CONTEXT_KEY) is not None:
            if ui.session_state.get(GENERATED_COACH_OUTPUT_KEY) is not None:
                ui.info(
                    "The experimental response below was generated from this request and the already-loaded "
                    "weekly Strava summary. The evidence view adds no interpretation and remains separate "
                    "from the offline demo."
                )
            else:
                ui.info(
                    "This deterministic evidence context uses only the already-loaded weekly Strava summary. "
                    "No experimental response has been generated for this context yet. It remains separate "
                    "from the offline demo."
                )
        else:
            ui.info(
                "This request is validated in the current session. Request validation does not access Strava "
                "or generate a Coach response. It remains separate from the offline demo."
            )

    evidence_context = ui.session_state.get(COACH_EVIDENCE_CONTEXT_KEY)
    if evidence_context is not None:
        loaded_weeks = ui.session_state.get(WEEKLY_ANALYSES_KEY)
        if isinstance(loaded_weeks, (tuple, list)) and len(loaded_weeks) == 7:
            render_coach_evidence_context(ui, evidence_context, tuple(loaded_weeks))
        else:
            clear_coach_evidence_context(ui.session_state)
    generated_output = ui.session_state.get(GENERATED_COACH_OUTPUT_KEY)
    if generated_output is not None:
        with ui.container(key="coach-response-panel"):
            ui.subheader("Experimental Coach response")
            ui.warning(
                "This model is not accepted. This response was generated from your request and Strava-derived "
                "evidence; it may be unsupported or unsuitable."
            )
            ui.text(generated_output)

    with ui.expander("Demo offline sintética", expanded=False):
        ui.info(
            "Synthetic fixture and pre-recorded response only; no athlete data, Strava or OpenAI calls, or advice. "
            "This does not evaluate model quality."
        )
        if ui.button("Show pre-recorded offline demo", key="show_offline_demo", type="secondary"):
            ui.session_state.pop(DEMO_SESSION_KEY, None)
            try:
                rendered_demo = _offline_demo_output()
            except ValueError:
                ui.error("The offline demo response could not be validated. No response was displayed.")
            else:
                ui.session_state[DEMO_SESSION_KEY] = rendered_demo
        demo_output = ui.session_state.get(DEMO_SESSION_KEY)
        if demo_output is not None:
            ui.subheader("Pre-recorded result")
            ui.text(demo_output)
