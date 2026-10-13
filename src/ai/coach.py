"""One-shot OpenAI execution behind the approved Increment 3 boundary."""

from dataclasses import asdict
from datetime import date, datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI, OpenAIError

from src.ai.coach_response import parse_coach_response
from src.ai.training_knowledge import load_training_knowledge
from src.models.coach_context import CoachContext
from src.models.coach_response import CoachResponse


_PROMPT_PATH = Path(__file__).parent / "prompts" / "coach_v1.txt"
_SCHEMA_PATH = Path(__file__).parent / "prompts" / "coach_v1.schema.json"

# Diagnostics describe the first rejected rule, never the rejected data.
# This allowlist translates existing errors; it does not validate responses.
_VALIDATION_DIAGNOSTICS = {
    "UNKNOWN_VALIDATION_FAILURE": "The approved parser/validator rejected the response for an unrecognized reason.",
    "JSON_DUPLICATE_FIELD": "The response contains a duplicate JSON field.",
    "JSON_NONSTANDARD_CONSTANT": "The response contains a nonstandard JSON constant.",
    "RESPONSE_STRUCTURE_INVALID": "The response does not have the required fields or types.",
    "STATUS_INVALID": "The response status is not supported.",
    "TEXT_INVALID": "A statement or reference must contain nonblank text.",
    "DATE_FORMAT_INVALID": "Period dates must use YYYY-MM-DD.",
    "DATE_VALUE_INVALID": "A period date is not a valid calendar date.",
    "UNKNOWN_EVIDENCE_REFERENCE": "An evidence reference is absent from the supplied context.",
    "UNKNOWN_KNOWLEDGE_REFERENCE": "A knowledge reference is absent from the approved item revisions.",
    "DUPLICATE_EVIDENCE_REFERENCE": "An evidence reference is repeated within a reference list.",
    "DUPLICATE_KNOWLEDGE_REFERENCE": "A knowledge reference is repeated within a reference list.",
    "STATEMENT_SUPPORT_MISSING": "A statement has no evidence or knowledge references.",
    "KNOWLEDGE_PACKAGE_INVALID": "Validation requires the pinned approved knowledge package.",
    "PERIOD_MISMATCH": "The recommendation period does not match the supplied context.",
    "RECOMMENDATION_AUTHORITY_INVALID": "Recommendations require exclusively actionable approved knowledge.",
    "RECOMMENDATION_EVIDENCE_MISSING": "A recommendation statement lacks supplied evidence references.",
    "RETURN_EVIDENCE_MISSING": "Return guidance requires both a recent qualifying Insight and a RunnerContext reference.",
    "GUIDANCE_SECTIONS_INVALID": "Guidance requires a recommendation and no clarification questions.",
    "CLARIFICATION_SECTIONS_INVALID": "Clarification requires questions and no recommendation.",
    "CLARIFICATION_AUTHORITY_INVALID": "A clarification question must identify actionable knowledge it could enable.",
    "INSUFFICIENT_SUPPORT_SECTIONS_INVALID": "Insufficient support requires a limitation, no recommendation and no questions.",
    "RUNNING_DAY_COUNT_INVALID": "The running-day count has an invalid type, range or availability.",
    "RUNNING_DAY_COUNT_UNSUPPORTED": "The approved knowledge supports no running-day count.",
    "ZERO_AVAILABILITY": "Zero availability precludes actionable running guidance.",
    "EMPTY_RECOMMENDATION": "A recommendation requires a direction or at least one training priority.",
    "EASY_DIRECTION_UNSUPPORTED": "Easy-running knowledge alone cannot authorize an overall direction.",
}

_VALIDATION_FAILURES = {
    "Unsupported CoachResponse status.": "STATUS_INVALID",
    "Period dates must use YYYY-MM-DD.": "DATE_FORMAT_INVALID",
    "Period dates must be valid YYYY-MM-DD dates.": "DATE_VALUE_INVALID",
    "Duplicate evidence reference.": "DUPLICATE_EVIDENCE_REFERENCE",
    "Duplicate relevant evidence reference.": "DUPLICATE_EVIDENCE_REFERENCE",
    "Duplicate knowledge reference.": "DUPLICATE_KNOWLEDGE_REFERENCE",
    "Statements require explicit evidence or knowledge references.": "STATEMENT_SUPPORT_MISSING",
    "Response validation requires the pinned approved knowledge package.": "KNOWLEDGE_PACKAGE_INVALID",
    "Recommendation period must match CoachContext exactly.": "PERIOD_MISMATCH",
    "Recommendations require actionable knowledge; application limitations are not authority.": "RECOMMENDATION_AUTHORITY_INVALID",
    "Recommendations require supplied evidence references.": "RECOMMENDATION_EVIDENCE_MISSING",
    "Return guidance requires references to a recent qualifying Insight and RunnerContext.": "RETURN_EVIDENCE_MISSING",
    "guidance_available requires a recommendation and no clarification questions.": "GUIDANCE_SECTIONS_INVALID",
    "clarification_required needs questions and withholds recommendations.": "CLARIFICATION_SECTIONS_INVALID",
    "Clarification must identify approved actionable knowledge it could enable.": "CLARIFICATION_AUTHORITY_INVALID",
    "insufficient_support requires a material limitation, no recommendation and no questions.": "INSUFFICIENT_SUPPORT_SECTIONS_INVALID",
    "Running-day count must be an integer within availability (0–7).": "RUNNING_DAY_COUNT_INVALID",
    "The current knowledge package supports no running-day count; leave it unset.": "RUNNING_DAY_COUNT_UNSUPPORTED",
    "Zero availability precludes an actionable running recommendation.": "ZERO_AVAILABILITY",
    "A recommendation needs direction or at least one training priority.": "EMPTY_RECOMMENDATION",
    "Easy-running priority alone does not support an overall direction.": "EASY_DIRECTION_UNSUPPORTED",
    **{f"{label} must contain exactly the expected fields.": "RESPONSE_STRUCTURE_INVALID"
       for label in ("CoachResponse", "Recommendation period", "Recommendation", "Statement")},
    **{f"{label} must be nonblank text.": "TEXT_INVALID"
       for label in ("Statement text", "Evidence references", "Knowledge references", "Relevant evidence",
                     "evidence reference", "knowledge reference", "relevant evidence reference")},
    **{f"{label} must be a list of text references.": "RESPONSE_STRUCTURE_INVALID"
       for label in ("Evidence references", "Knowledge references", "Relevant evidence")},
    **{f"{label} must be an immutable tuple.": "RESPONSE_STRUCTURE_INVALID"
       for label in ("evidence reference", "knowledge reference", "relevant evidence reference")},
    **{message: "RESPONSE_STRUCTURE_INVALID" for message in (
        "Statement sections must be lists.", "Expected a GroundedStatement.",
        "Expected CoachResponse with an allowed status enum.",
        "Statement sections must be immutable tuples.", "Training priorities must be an immutable tuple.",
    )},
}

_VALIDATION_FAILURE_PREFIXES = (
    ("Unknown evidence reference: ", "UNKNOWN_EVIDENCE_REFERENCE"),
    ("Unknown relevant evidence reference: ", "UNKNOWN_EVIDENCE_REFERENCE"),
    ("Unknown knowledge reference: ", "UNKNOWN_KNOWLEDGE_REFERENCE"),
    ("Invalid CoachResponse JSON: Duplicate JSON field: ", "JSON_DUPLICATE_FIELD"),
    ("Invalid CoachResponse JSON: Nonstandard JSON constant: ", "JSON_NONSTANDARD_CONSTANT"),
)


def _validation_diagnostic_code(error: ValueError) -> str:
    """Inspect in memory only; never return raw messages or dynamic suffixes."""
    message = str(error)
    code = _VALIDATION_FAILURES.get(message)
    if code is not None:
        return code
    for prefix, code in _VALIDATION_FAILURE_PREFIXES:
        if message.startswith(prefix):
            return code
    return "UNKNOWN_VALIDATION_FAILURE"


class CoachError(RuntimeError):
    """Execution failed; no coaching fallback is produced."""


class CoachConfigurationError(CoachError):
    """Required environment configuration or local resources are missing."""


class CoachProviderError(CoachError):
    """The OpenAI SDK/API failed."""


class CoachRefusalError(CoachError):
    """The provider refused the request."""


class CoachMalformedOutputError(CoachError):
    """The provider returned missing, incomplete, or non-JSON output."""


class CoachInvalidResponseError(CoachError):
    """The existing response parser/validator rejected the output."""

    diagnostic_code: str = "UNKNOWN_VALIDATION_FAILURE"

    @property
    def validation_diagnostic(self) -> str:
        """Only allowlisted codes and fixed explanations may be displayed."""
        code = self.diagnostic_code
        if code not in _VALIDATION_DIAGNOSTICS:
            code = "UNKNOWN_VALIDATION_FAILURE"
        return f"{code}: {_VALIDATION_DIAGNOSTICS[code]}"


def _json_value(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, ZoneInfo):
        return value.key
    raise TypeError(f"Unsupported serialization type: {type(value).__name__}")


def generate_coach_response(context: CoachContext) -> CoachResponse:
    """Receive an already built context; call once and return only validated output.

    All dataclass fields are serialized without interpreting RunnerContext.
    Dates/timestamps use ISO 8601, enums their values, zones their IANA keys,
    and tuples JSON arrays. Provider errors/output are never logged or echoed.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_COACH_MODEL")
    if not api_key or not api_key.strip():
        raise CoachConfigurationError("Set OPENAI_API_KEY before executing Coach.")
    if not model or not model.strip():
        raise CoachConfigurationError("Set OPENAI_COACH_MODEL to a structured-output capable model.")
    knowledge = load_training_knowledge()
    try:
        prompt = _PROMPT_PATH.read_text(encoding="utf-8")
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CoachConfigurationError("Coach V1 prompt/schema could not be loaded.") from None
    payload = json.dumps(
        {"coach_context": asdict(context), "training_knowledge": asdict(knowledge)},
        default=_json_value, ensure_ascii=False, allow_nan=False,
    )
    try:
        with OpenAI(api_key=api_key, max_retries=0) as client:
            completion = client.chat.completions.create(
                model=model,
                store=False,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": payload},
                ],
                response_format={"type": "json_schema", "json_schema": {
                    "name": "coach_response_v1", "strict": True, "schema": schema,
                }},
            )
    except OpenAIError:
        raise CoachProviderError("OpenAI request failed; check configuration, access and connectivity.") from None
    if not completion.choices:
        raise CoachMalformedOutputError("OpenAI returned no response choice.")
    choice = completion.choices[0]
    if choice.message.refusal:
        raise CoachRefusalError("OpenAI refused the Coach request.")
    if choice.finish_reason != "stop":
        raise CoachMalformedOutputError("OpenAI returned an incomplete response.")
    content = choice.message.content
    if not isinstance(content, str) or not content.strip():
        raise CoachMalformedOutputError("OpenAI returned no response content.")
    try:
        json.loads(content)
    except ValueError:
        raise CoachMalformedOutputError("OpenAI returned malformed JSON.") from None
    try:
        # Pass the original JSON to preserve strict duplicate/nonstandard checks.
        return parse_coach_response(content, context=context, knowledge=knowledge)
    except ValueError as error:
        failure = CoachInvalidResponseError("CoachResponse failed the approved parser/validator.")
        failure.diagnostic_code = _validation_diagnostic_code(error)
        raise failure from None
