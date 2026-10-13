"""Bounded offline review workflow for eight authored Increment 5A scenarios.

No provider integration, semantic judge, response capture, or automatic reviews.
Run from the repository root: python -m tests.llm.increment5a.evaluate --help
"""

import argparse
from collections import Counter
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from src.ai.coach_context import build_coach_context
from src.ai.coach_response import parse_coach_response
from src.ai.training_knowledge import load_training_knowledge
from src.models.coach_context import SourceMetadata
from src.models.coach_request import coach_request_from_input
from src.models.training_analysis import TrainingType
from src.models.weekly_analysis import TrainingTypeSummary, WeeklyAnalysis


ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = Path(__file__).with_name("dataset.json")
DIMENSIONS = (
    "factual_correctness", "evidence_grounding", "knowledge_applicability",
    "constraints_and_safety", "guidance_versus_abstention", "transparency",
)
CHARACTERISTICS = (
    "Functional Correctness", "Functional Adaptability", "User Controllability",
    "Transparency", "AI Robustness", "Intervenability", "Ethical Risk Mitigation",
)
OUTCOMES = {"PASS", "FAIL", "UNEVALUATED"}
STATUSES = {"guidance_available", "clarification_required", "insufficient_support"}
REVIEW_FORMAT_VERSION = "1.0.0"


class EvaluationInputError(ValueError):
    """Invalid local evaluation input; messages contain no rejected content."""


def _object(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise EvaluationInputError("Evaluation input must contain exactly the documented fields.")
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise EvaluationInputError("Evaluation input requires nonblank text.")
    return value


def _texts(value):
    if not isinstance(value, list) or not value:
        raise EvaluationInputError("Evaluation input requires a nonempty list of text.")
    return [_text(item) for item in value]


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise EvaluationInputError("Evaluation JSON contains duplicate fields.")
        value[key] = item
    return value


def _constant(value):
    raise EvaluationInputError("Evaluation JSON contains a nonstandard constant.")


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
    except (OSError, UnicodeError, ValueError):
        raise EvaluationInputError("Cannot read valid evaluation JSON.") from None


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def fingerprints():
    files = sorted(path for path in (ROOT / "src").rglob("*.py")
                   if not (path.name.startswith("test_") or path.name.endswith(("_test.py", ".test.py"))))
    production = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    knowledge = load_training_knowledge()
    return {
        "production_code_sha256": _sha(production),
        "production_files_sha256": production,
        "evaluator_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256((ROOT / "src/ai/prompts/coach_v1.txt").read_bytes()).hexdigest(),
        "transport_template_sha256": hashlib.sha256((ROOT / "src/ai/prompts/coach_v1.schema.json").read_bytes()).hexdigest(),
        "knowledge_reference": knowledge.reference,
        "knowledge_content_sha256": knowledge.content_sha256,
    }


def build_context(data):
    """Translate only this dataset's explicit synthetic weekly input format."""
    _object(data, ("reference_datetime", "athlete_timezone", "request", "weeks", "source_metadata"))
    reference = datetime.fromisoformat(data["reference_datetime"])
    zone = ZoneInfo(data["athlete_timezone"])
    request = coach_request_from_input(data["request"], reference_datetime=reference, athlete_timezone=zone)
    if not isinstance(data["weeks"], list):
        raise EvaluationInputError("Synthetic weeks must be a list.")
    weeks = []
    for row in data["weeks"]:
        _object(row, ("week_start_date", "distance_meters", "activity_count", "moving_time_seconds"))
        if (type(row["activity_count"]) is not int or row["activity_count"] < 0
            or type(row["moving_time_seconds"]) is not int or row["moving_time_seconds"] < 0
            or type(row["distance_meters"]) not in (int, float) or row["distance_meters"] < 0):
            raise EvaluationInputError("Synthetic weekly measurements have invalid types or values.")
        count, distance, moving = row["activity_count"], row["distance_meters"], row["moving_time_seconds"]
        if count == 0 and (distance != 0 or moving != 0):
            raise EvaluationInputError("Synthetic zero-activity rows require zero totals.")
        weeks.append(WeeklyAnalysis(
            date.fromisoformat(row["week_start_date"]), distance, count, moving,
            tuple(TrainingTypeSummary(kind, count if kind is TrainingType.OTHER else 0,
                                      distance if kind is TrainingType.OTHER else 0,
                                      moving if kind is TrainingType.OTHER else 0) for kind in TrainingType),
        ))
    metadata = _object(data["source_metadata"], ("source_name", "data_as_of", "coverage", "partial_week_dates"))
    return build_coach_context(
        request, weeks, reference_datetime=reference, athlete_timezone=zone,
        source_metadata=SourceMetadata(metadata["source_name"], datetime.fromisoformat(metadata["data_as_of"]),
                                       metadata["coverage"], tuple(date.fromisoformat(day) for day in metadata["partial_week_dates"])),
    )


def validate_dataset(dataset):
    _object(dataset, ("dataset_version", "rubric_version", "provenance", "rubric", "quality_coverage", "scenarios"))
    _text(dataset["dataset_version"])
    _text(dataset["rubric_version"])
    if dataset["provenance"] != "synthetic_authored_controls_not_model_outputs":
        raise EvaluationInputError("Increment 5A accepts only authored synthetic controls.")
    _object(dataset["rubric"], DIMENSIONS)
    for description in dataset["rubric"].values():
        _text(description)
    _object(dataset["quality_coverage"], CHARACTERISTICS)
    for coverage in dataset["quality_coverage"].values():
        _object(coverage, ("coverage", "limitations"))
        if coverage["coverage"] != "partial":
            raise EvaluationInputError("Increment 5A quality coverage must be marked partial.")
        _text(coverage["limitations"])
    scenarios = dataset["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 8:
        raise EvaluationInputError("Increment 5A requires exactly eight scenarios.")
    ids, controls, mapped = set(), set(), set()
    knowledge = load_training_knowledge()
    knowledge_refs = {f"{item.id}@{item.revision}" for item in (*knowledge.actionable_items, *knowledge.application_limitations)}
    for scenario in scenarios:
        _object(scenario, ("id", "title", "input_conditions", "input", "known_facts", "unknown_facts",
                           "approved_knowledge", "expected_behavior", "permitted_statuses",
                           "critical_failure_conditions", "quality_characteristics", "evaluation_method", "controls"))
        if _text(scenario["id"]) in ids:
            raise EvaluationInputError("Scenario identifiers must be unique.")
        ids.add(_text(scenario["id"]))
        _text(scenario["title"])
        for key in ("input_conditions", "known_facts", "unknown_facts", "expected_behavior", "evaluation_method"):
            _texts(scenario[key])
        statuses = _texts(scenario["permitted_statuses"])
        if not set(statuses) <= STATUSES or len(set(statuses)) != len(statuses):
            raise EvaluationInputError("Scenario permitted statuses are invalid.")
        characteristics = _texts(scenario["quality_characteristics"])
        if not set(characteristics) <= set(CHARACTERISTICS) or len(set(characteristics)) != len(characteristics):
            raise EvaluationInputError("Scenario quality mappings are invalid.")
        mapped.update(characteristics)
        if not isinstance(scenario["approved_knowledge"], dict) or not scenario["approved_knowledge"]:
            raise EvaluationInputError("Scenario knowledge applicability must be documented.")
        if not set(scenario["approved_knowledge"]) <= knowledge_refs:
            raise EvaluationInputError("Scenario knowledge references must be approved pairs.")
        for description in scenario["approved_knowledge"].values():
            _text(description)
        conditions = scenario["critical_failure_conditions"]
        if not isinstance(conditions, dict) or not conditions:
            raise EvaluationInputError("Scenario critical failure conditions must be documented.")
        for key, description in conditions.items():
            _text(key)
            _text(description)
        rows = scenario["controls"]
        if not isinstance(rows, list) or len(rows) != 2:
            raise EvaluationInputError("Each scenario requires exactly two controls.")
        labels = []
        for control in rows:
            _object(control, ("id", "expected_semantic_outcome", "author_expectation_explanation", "expected_critical_failures", "response"))
            control_id = _text(control["id"])
            if control_id in controls or not control_id.startswith(scenario["id"] + "-"):
                raise EvaluationInputError("Control identifiers must be unique and match their scenario.")
            controls.add(control_id)
            label = control["expected_semantic_outcome"]
            if label not in ("PASS", "FAIL"):
                raise EvaluationInputError("Authored control labels must be PASS or FAIL.")
            labels.append(label)
            _text(control["author_expectation_explanation"])
            expected = control["expected_critical_failures"]
            if not isinstance(expected, list) or any(not isinstance(item, str) for item in expected) or len(set(expected)) != len(expected) or not set(expected) <= set(conditions):
                raise EvaluationInputError("Expected critical failures must resolve to scenario conditions.")
            if (label == "PASS" and expected) or (label == "FAIL" and not expected):
                raise EvaluationInputError("Control critical expectations contradict the authored label.")
            if not isinstance(control["response"], dict):
                raise EvaluationInputError("Authored responses must be JSON objects.")
        if sorted(labels) != ["FAIL", "PASS"]:
            raise EvaluationInputError("Each scenario needs one positive and one negative control.")
        try:
            build_context(scenario["input"])
        except (ValueError, TypeError, KeyError):
            raise EvaluationInputError("Cannot build a valid synthetic CoachContext.") from None
    if ids != {f"5A-{number:02d}" for number in range(1, 9)}:
        raise EvaluationInputError("Scenario identifiers must be exactly 5A-01 through 5A-08.")
    if mapped != set(CHARACTERISTICS):
        raise EvaluationInputError("All seven quality characteristics must be mapped.")
    return dataset


def aggregate(outcomes):
    values = list(outcomes)
    if len(values) != 6 or not set(values) <= OUTCOMES:
        raise EvaluationInputError("A review requires six valid rubric outcomes.")
    if "FAIL" in values:
        return "FAIL"
    if "UNEVALUATED" in values:
        return "UNEVALUATED"
    return "PASS"


def _unreviewed():
    return {"reviewer": None, "reviewed_at": None, "review_stage": "initial",
            "dimensions": {name: {"outcome": "UNEVALUATED", "explanation": "", "affected_statement_or_reference": None}
                           for name in DIMENSIONS}, "critical_failures": []}


def review_template(dataset):
    validate_dataset(dataset)
    return {"review_format_version": REVIEW_FORMAT_VERSION,
            "dataset_version": dataset["dataset_version"], "rubric_version": dataset["rubric_version"],
            "dataset_sha256": _sha(dataset), "fingerprints": fingerprints(),
            "reviews": [{"scenario_id": scenario["id"], "control_id": control["id"],
                         "response_sha256": _sha(control["response"]), **_unreviewed()}
                        for scenario in dataset["scenarios"] for control in scenario["controls"]]}


def _locations(response, context, knowledge):
    locations = {"response", "status", "recommendation_period", "relevant_evidence"}
    for key in ("current_state", "recent_evolution"):
        locations.add(key)
    for key in ("limitations", "clarification_questions"):
        if isinstance(response.get(key), list):
            locations.update(f"{key}[{index}]" for index in range(len(response[key])))
    recommendation = response.get("next_week_recommendation")
    if isinstance(recommendation, dict):
        locations.update(f"next_week_recommendation.{key}" for key in ("overall_direction", "reasoning", "recommended_running_days"))
        if isinstance(recommendation.get("training_priorities"), list):
            locations.update(f"next_week_recommendation.training_priorities[{index}]" for index in range(len(recommendation["training_priorities"])))
    locations.update(entry.reference for entry in context.evidence_references)
    locations.update(f"{item.id}@{item.revision}" for item in (*knowledge.actionable_items, *knowledge.application_limitations))
    return locations


def _review_index(dataset, reviews, current_fingerprints):
    if reviews is None:
        return {}
    _object(reviews, ("review_format_version", "dataset_version", "rubric_version", "dataset_sha256", "fingerprints", "reviews"))
    if (reviews["review_format_version"] != REVIEW_FORMAT_VERSION or reviews["dataset_version"] != dataset["dataset_version"]
        or reviews["rubric_version"] != dataset["rubric_version"] or reviews["dataset_sha256"] != _sha(dataset)
        or reviews["fingerprints"] != current_fingerprints):
        raise EvaluationInputError("Human reviews do not match the current dataset, rubric or implementation fingerprints.")
    if not isinstance(reviews["reviews"], list):
        raise EvaluationInputError("Human reviews must be a list.")
    controls = {control["id"]: (scenario, control) for scenario in dataset["scenarios"] for control in scenario["controls"]}
    indexed = {}
    knowledge = load_training_knowledge()
    for row in reviews["reviews"]:
        _object(row, ("scenario_id", "control_id", "response_sha256", "reviewer", "reviewed_at", "review_stage", "dimensions", "critical_failures"))
        key = _text(row["control_id"])
        if key not in controls or key in indexed:
            raise EvaluationInputError("Human review identifiers are unknown or duplicated.")
        scenario, control = controls[key]
        if row["scenario_id"] != scenario["id"] or row["response_sha256"] != _sha(control["response"]):
            raise EvaluationInputError("Human review does not match its scenario/control fingerprint.")
        if row["review_stage"] not in ("initial", "adjudication"):
            raise EvaluationInputError("Review stage must be initial or adjudication.")
        _object(row["dimensions"], DIMENSIONS)
        locations = _locations(control["response"], build_context(scenario["input"]), knowledge)
        has_assessment = False
        for assessment in row["dimensions"].values():
            _object(assessment, ("outcome", "explanation", "affected_statement_or_reference"))
            outcome = assessment["outcome"]
            if not isinstance(outcome, str) or outcome not in OUTCOMES:
                raise EvaluationInputError("Human review outcome is invalid.")
            explanation = assessment["explanation"]
            if not isinstance(explanation, str):
                raise EvaluationInputError("Review explanations must be text.")
            affected = assessment["affected_statement_or_reference"]
            if affected is not None and (not isinstance(affected, str) or affected not in locations):
                raise EvaluationInputError("Review affected location does not resolve to the control or supplied references.")
            if outcome != "UNEVALUATED":
                _text(explanation)
            if outcome == "FAIL" and affected is None:
                raise EvaluationInputError("A failed dimension requires an affected statement or reference.")
            has_assessment |= outcome != "UNEVALUATED" or bool(explanation.strip()) or affected is not None
        failures = row["critical_failures"]
        if not isinstance(failures, list):
            raise EvaluationInputError("Critical findings must be a list.")
        failure_ids = set()
        for failure in failures:
            _object(failure, ("condition_id", "explanation", "affected_statement_or_reference"))
            condition = _text(failure["condition_id"])
            if condition not in scenario["critical_failure_conditions"] or condition in failure_ids:
                raise EvaluationInputError("Critical finding identifiers are unknown or duplicated.")
            failure_ids.add(condition)
            _text(failure["explanation"])
            if not isinstance(failure["affected_statement_or_reference"], str) or failure["affected_statement_or_reference"] not in locations:
                raise EvaluationInputError("Critical finding requires a resolvable affected location.")
        if failures and aggregate(item["outcome"] for item in row["dimensions"].values()) != "FAIL":
            raise EvaluationInputError("A critical finding requires a human FAIL outcome.")
        if has_assessment or failures or row["reviewer"] is not None or row["reviewed_at"] is not None:
            _text(row["reviewer"])
            try:
                reviewed_at = datetime.fromisoformat(row["reviewed_at"])
                if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
                    raise ValueError
            except (ValueError, TypeError):
                raise EvaluationInputError("Human assessments require a timezone-aware review timestamp.") from None
        indexed[key] = row
    return indexed


def _rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def _criterion(rows, predicate):
    if any(row["human_semantic_outcome"] != "UNEVALUATED" and not predicate(row) for row in rows):
        return "FAIL"
    if any(row["human_semantic_outcome"] == "UNEVALUATED" for row in rows):
        return "PENDING"
    return "PASS"


def generate_report(dataset, reviews=None):
    validate_dataset(dataset)
    current = fingerprints()
    indexed = _review_index(dataset, reviews, current)
    knowledge = load_training_knowledge()
    rows = []
    for scenario in dataset["scenarios"]:
        context = build_context(scenario["input"])
        for control in scenario["controls"]:
            try:
                parsed = parse_coach_response(control["response"], context=context, knowledge=knowledge)
                structural = "PASS"
                status_check = "PASS" if parsed.status.value in scenario["permitted_statuses"] else "FAIL"
            except ValueError:
                structural, status_check = "FAIL", "UNEVALUATED"
            review = indexed.get(control["id"], _unreviewed())
            human = aggregate(item["outcome"] for item in review["dimensions"].values())
            overall = "FAIL" if structural == "FAIL" or status_check == "FAIL" else human
            comparison = "UNEVALUATED" if human == "UNEVALUATED" else ("PASS" if human == control["expected_semantic_outcome"] else "FAIL")
            rows.append({"scenario_id": scenario["id"], "control_id": control["id"],
                         "response_sha256": _sha(control["response"]), "expected_semantic_outcome": control["expected_semantic_outcome"],
                         "expected_critical_failures": control["expected_critical_failures"],
                         "structural_validation": structural, "structural_error_code": None if structural == "PASS" else "DOMAIN_VALIDATION_REJECTED",
                         "permitted_status_check": status_check, "human_review": review,
                         "human_semantic_outcome": human, "overall_outcome": overall, "expectation_comparison": comparison})
    positives = [row for row in rows if row["expected_semantic_outcome"] == "PASS"]
    negatives = [row for row in rows if row["expected_semantic_outcome"] == "FAIL"]
    def identified(row):
        actual = {finding["condition_id"] for finding in row["human_review"]["critical_failures"]}
        return row["human_semantic_outcome"] == "FAIL" and set(row["expected_critical_failures"]) <= actual
    criteria = {
        "dataset_completeness": "PASS", "seven_characteristics_mapped_with_partial_coverage": "PASS",
        "expected_labels_documented": "PASS",
        "all_six_dimensions_reviewed": "PASS" if all(
            item["outcome"] != "UNEVALUATED" for row in rows
            for item in row["human_review"]["dimensions"].values()) else "PENDING",
        "positive_controls_human_pass": _criterion(positives, lambda row: row["human_semantic_outcome"] == "PASS"),
        "negative_controls_human_fail": _criterion(negatives, lambda row: row["human_semantic_outcome"] == "FAIL"),
        "critical_negative_controls_identified": _criterion(negatives, identified),
        "no_critical_negative_human_pass": _criterion(negatives, lambda row: row["human_semantic_outcome"] != "PASS"),
        "structural_gate": "PASS" if all(row["structural_validation"] == "PASS" for row in rows) else "FAIL",
        "positive_permitted_statuses": "PASS" if all(row["permitted_status_check"] == "PASS" for row in positives) else "FAIL",
    }
    counts = Counter(row["overall_outcome"] for row in rows)
    human_counts = Counter(row["human_semantic_outcome"] for row in rows)
    reviewed = sum(value for key, value in human_counts.items() if key != "UNEVALUATED")
    completed_reviews = sum(all(item["outcome"] != "UNEVALUATED"
                                for item in row["human_review"]["dimensions"].values()) for row in rows)
    agreement = sum(row["expectation_comparison"] == "PASS" for row in rows)
    findings = [{"scenario_id": row["scenario_id"], "control_id": row["control_id"], **finding}
                for row in rows for finding in row["human_review"]["critical_failures"]]
    readiness = "FAIL" if "FAIL" in criteria.values() else ("UNEVALUATED" if "PENDING" in criteria.values() else "PASS")
    return {"report_version": "1.0.0", "dataset_version": dataset["dataset_version"], "rubric_version": dataset["rubric_version"],
            "dataset_sha256": _sha(dataset), "reviews_sha256": _sha(reviews) if reviews is not None else None,
            "fingerprints": current, "generated_model_performance": "UNEVALUATED",
            "evaluation_framework_outcome": readiness,
            "increment5a_status": "COMPLETE" if readiness == "PASS" else ("BLOCKED" if readiness == "FAIL" else "PENDING_HUMAN_REVIEW"),
            "acceptance_criteria": criteria, "controls": rows,
            "metrics": {"scenario_count": len(dataset["scenarios"]), "control_count": len(rows),
                        "overall_outcomes": {value: counts[value] for value in ("PASS", "FAIL", "UNEVALUATED")},
                        "human_outcomes": {value: human_counts[value] for value in ("PASS", "FAIL", "UNEVALUATED")},
                        "structural_acceptance": _rate(sum(row["structural_validation"] == "PASS" for row in rows), len(rows)),
                        "human_review_coverage": _rate(completed_reviews, len(rows)),
                        "human_verdict_coverage": _rate(reviewed, len(rows)),
                        "human_label_agreement": _rate(agreement, reviewed),
                        "rubric_dimensions": {name: {
                            "outcomes": {value: sum(row["human_review"]["dimensions"][name]["outcome"] == value for row in rows)
                                         for value in ("PASS", "FAIL", "UNEVALUATED")},
                            "pass_rate": _rate(sum(row["human_review"]["dimensions"][name]["outcome"] == "PASS" for row in rows), len(rows)),
                        } for name in DIMENSIONS},
                        "positive_controls_accepted": _rate(sum(row["human_semantic_outcome"] == "PASS" for row in positives), len(positives)),
                        "negative_controls_rejected": _rate(sum(row["human_semantic_outcome"] == "FAIL" for row in negatives), len(negatives)),
                        "critical_negatives_identified": _rate(sum(identified(row) for row in negatives), len(negatives)),
                        "critical_findings_count": len(findings), "critical_findings_review_denominator": reviewed,
                        "totals_reconcile": sum(counts.values()) == len(rows)},
            "critical_failures": findings,
            "quality_coverage": {name: {**dataset["quality_coverage"][name],
                                        "scenario_ids": [scenario["id"] for scenario in dataset["scenarios"] if name in scenario["quality_characteristics"]]}
                                 for name in CHARACTERISTICS},
            "limitations": ["Authored synthetic controls only; no generated-model performance measurement.",
                            "Structural acceptance does not establish semantic correctness or knowledge applicability.",
                            "Human labels are assertions supplied by the reviewer, not independently authenticated identities.",
                            "Uncertain judgments remain UNEVALUATED until explicit human adjudication; no automatic resolution.",
                            "Eight scenarios provide partial coverage; no statistical generalization, fairness study, runtime veto or cancellation.",
                            "No raw responses or RunnerContext are included in this report."]}


def _write_artifact(path, payload, protected):
    destination = Path(path).resolve()
    if destination in {Path(item).resolve() for item in protected} or destination.is_relative_to(ROOT / "src"):
        raise EvaluationInputError("Output must not overwrite inputs or production files.")
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--reviews", type=Path, help="Explicit human-review JSON; omitted means UNEVALUATED.")
    parser.add_argument("--report", type=Path, help="Write metadata/review report; otherwise print it to stdout.")
    parser.add_argument("--review-template", type=Path, help="Write an entirely UNEVALUATED human-review template.")
    args = parser.parse_args(argv)
    try:
        dataset = validate_dataset(read_json(args.dataset))
        reviews = read_json(args.reviews) if args.reviews else None
        report = generate_report(dataset, reviews)
        protected = [args.dataset, Path(__file__)] + ([args.reviews] if args.reviews else [])
        if args.report and args.review_template and args.report.resolve() == args.review_template.resolve():
            raise EvaluationInputError("Report and review template must have different destinations.")
        if args.review_template:
            _write_artifact(args.review_template, review_template(dataset), protected)
        if args.report:
            _write_artifact(args.report, report, protected)
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    except (EvaluationInputError, OSError):
        print("Evaluation input or output is invalid; check the documented local file formats.", file=sys.stderr)
        return 2
    return 1 if report["evaluation_framework_outcome"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
