"""Immutable Coach V1 request data and its explicit text-input boundary."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
import re
from zoneinfo import ZoneInfo


class GoalType(str, Enum):
    HALF_MARATHON = "HALF_MARATHON"


@dataclass(frozen=True)
class RunnerGoal:
    """Supplied goal; temporal validation belongs to the request builder."""

    goal_type: GoalType
    target_date: date


@dataclass(frozen=True)
class RunnerConstraints:
    """Maximum available running days in the recommendation week, not advice."""

    available_training_days_per_week: int


@dataclass(frozen=True)
class RunnerContext:
    """Original, unverified user report for this request only."""

    runner_context: str | None = None


@dataclass(frozen=True)
class CoachRequest:
    """Keep goal, availability and user-reported context conceptually separate."""

    goal: RunnerGoal
    constraints: RunnerConstraints
    context: RunnerContext


def coach_request_from_input(
    data: dict[str, object],
    *,
    reference_datetime: datetime,
    athlete_timezone: ZoneInfo,
) -> CoachRequest:
    """Validate text input without consulting a clock or persisting context.

    Input contains goal and constraints objects, and optional runner_context
    text. Direct dataclass construction is passive, as with existing models;
    application callers must use this boundary to obtain a validated request.
    Length counts Unicode code points, including whitespace, before checking
    whether a context is blank. Nonblank text is preserved exactly.
    """
    if (
        not isinstance(reference_datetime, datetime)
        or reference_datetime.tzinfo is None
        or reference_datetime.utcoffset() is None
    ):
        raise ValueError("Reference datetime must be timezone-aware.")
    if not isinstance(athlete_timezone, ZoneInfo):
        raise ValueError("Athlete timezone must be an explicit ZoneInfo.")
    if not isinstance(data, dict) or set(data) - {"goal", "constraints", "runner_context"}:
        raise ValueError("Request must contain only goal, constraints and runner_context.")

    goal = data.get("goal")
    if not isinstance(goal, dict) or set(goal) != {"goal_type", "target_date"}:
        raise ValueError("Goal requires only goal_type and target_date.")
    if not isinstance(goal["goal_type"], str) or goal["goal_type"] != GoalType.HALF_MARATHON.value:
        raise ValueError("Goal type must be HALF_MARATHON.")
    target_text = goal["target_date"]
    if not isinstance(target_text, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", target_text) is None:
        raise ValueError("Target date must be a valid YYYY-MM-DD date.")
    try:
        target_date = date.fromisoformat(target_text)
    except ValueError:
        raise ValueError("Target date must be a valid YYYY-MM-DD date.") from None
    if target_date <= reference_datetime.astimezone(athlete_timezone).date():
        raise ValueError("Target date must be strictly after the reference local date.")

    constraints = data.get("constraints")
    if not isinstance(constraints, dict) or set(constraints) != {"available_training_days_per_week"}:
        raise ValueError("Constraints require only available_training_days_per_week.")
    availability = constraints["available_training_days_per_week"]
    if type(availability) is not int or not 0 <= availability <= 7:
        raise ValueError("Available training days must be an integer from 0 through 7.")

    context = data.get("runner_context")
    if context is not None:
        if not isinstance(context, str):
            raise ValueError("Runner context must be text or null.")
        if len(context) > 2000:
            raise ValueError("Runner context must not exceed 2,000 Unicode characters.")
        if not context.strip():
            context = None

    return CoachRequest(
        goal=RunnerGoal(GoalType.HALF_MARATHON, target_date),
        constraints=RunnerConstraints(availability),
        context=RunnerContext(context),
    )
