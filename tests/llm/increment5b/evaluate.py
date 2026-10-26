"""Offline human reviews and reports for existing 5B captures; never generate."""

import argparse
from datetime import datetime
import hashlib
from pathlib import Path
import sys

from src.ai.coach_response import parse_coach_response
from src.ai.training_knowledge import load_training_knowledge
from tests.llm.increment5a import evaluate as rubric
from tests.llm.increment5b import run

VERSION = '5B-02-1.0.0'


class ReviewInputError(ValueError):
    """Fixed errors with no rejected content, response bodies or raw exceptions."""


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
    except (ValueError, TypeError):
        raise ReviewInputError('REVIEW_TIMESTAMP_INVALID') from None


def _present(path):
    return path.exists() or path.is_symlink()


def _ingest(directory, manifest, scenario, knowledge):
    sid = scenario['id']
    reservation = directory / f'{sid}.attempt.json'
    result_path = directory / f'{sid}.result.json'
    row = {'scenario_id': sid, 'reserved': _present(reservation), 'terminal_record': _present(result_path),
           'execution_outcome': 'MISSING', 'technical_validation': 'PASS', 'structural_validation': 'NOT_EVALUATED',
           'permitted_status_check': 'UNEVALUATED', 'unassessable_reason': 'NOT_ATTEMPTED',
           'execution_artifact_sha256': None, 'reservation_sha256': None, 'response_sha256': None,
           'safe_error_code': None, 'safe_provider_diagnostic_code': None,
           'safe_provider_http_status': None, 'response': None}
    try:
        if not row['reserved']:
            if row['terminal_record']:
                raise ReviewInputError('ORPHAN_RESULT')
            return row
        reserved = run._read_sealed(reservation)
        _timestamp(reserved.get('execution_timestamp_utc'))
        if reserved != run._artifact(manifest, sid, 'RESERVED_UNCERTAIN', timestamp=reserved['execution_timestamp_utc']):
            raise ReviewInputError('RESERVATION_BINDING_INVALID')
        row.update(reservation_sha256=reserved['artifact_sha256'], execution_outcome='RESERVED_UNCERTAIN',
                   unassessable_reason='RESERVED_UNCERTAIN')
        if not row['terminal_record']:
            return row
        artifact = run._read_sealed(result_path)
        outcome, response, failure, diagnostic = (artifact.get(key) for key in
            ('attempt_outcome', 'response', 'safe_failure_category', 'safe_validation_diagnostic'))
        provider_diagnostic_code = artifact.get('safe_provider_diagnostic_code')
        provider_http_status = artifact.get('safe_provider_http_status')
        allowed = {f'{code}: {explanation}' for code, explanation in run.coach._VALIDATION_DIAGNOSTICS.items()}
        if diagnostic is not None and diagnostic not in allowed:
            raise ReviewInputError('DIAGNOSTIC_INVALID')
        run._validate_provider_diagnostic(provider_diagnostic_code, provider_http_status, failure)
        if outcome not in ('SUCCESS', 'FAILED', 'INTERRUPTED'):
            raise ReviewInputError('EXECUTION_OUTCOME_INVALID')
        if outcome == 'SUCCESS':
            if response is None or failure is not None or diagnostic is not None:
                raise ReviewInputError('SUCCESS_RECORD_INVALID')
        elif response is not None or failure not in (*run.FAILURES.values(), 'UNEXPECTED_ERROR', 'INTERRUPTED'):
            raise ReviewInputError('FAILURE_RECORD_INVALID')
        if (outcome == 'INTERRUPTED') != (failure == 'INTERRUPTED'):
            raise ReviewInputError('INTERRUPTION_RECORD_INVALID')
        expected = run._artifact(manifest, sid, outcome, response=response, failure=failure,
                                diagnostic=diagnostic, provider_diagnostic_code=provider_diagnostic_code,
                                provider_http_status=provider_http_status,
                                timestamp=reserved['execution_timestamp_utc'])
        if artifact != expected:
            raise ReviewInputError('EXECUTION_BINDING_INVALID')
        row.update(execution_artifact_sha256=artifact['artifact_sha256'], execution_outcome=outcome,
                   structural_validation=artifact['structural_validation'],
                   unassessable_reason=failure, safe_error_code=failure,
                   safe_provider_diagnostic_code=provider_diagnostic_code,
                   safe_provider_http_status=provider_http_status)
        if outcome == 'SUCCESS':
            context = rubric.build_context(scenario['input'])
            try:
                parsed = parse_coach_response(response, context=context, knowledge=knowledge)
            except ValueError:
                row.update(structural_validation='FAIL', unassessable_reason='RESPONSE_REVALIDATION_FAILED',
                           safe_error_code='RESPONSE_REVALIDATION_FAILED')
                return row
            row.update(response=response, response_sha256=artifact['response_sha256'],
                       permitted_status_check='PASS' if parsed.status.value in scenario['permitted_statuses'] else 'FAIL')
        return row
    except (ReviewInputError, run.ExecutionGuardError, rubric.EvaluationInputError, OSError, ValueError, TypeError, KeyError):
        row.update(technical_validation='FAIL', structural_validation='NOT_EVALUATED', response=None,
                   response_sha256=None, unassessable_reason='ARTIFACT_INTEGRITY_ERROR', safe_error_code='ARTIFACT_INTEGRITY_ERROR')
        return row


def load_cohort(directory):
    directory = run._directory(directory)
    with run._lock(directory):
        initial = run._read_sealed(directory / 'manifest.json')
        dataset = rubric.validate_dataset(rubric.read_json(rubric.DATASET_PATH))
        config = run.configuration(dataset, initial['configuration']['model'])
        manifest = run._manifest(directory, config)
        knowledge = load_training_knowledge()
        scenarios = {s['id']: s for s in dataset['scenarios']}
        rows = [_ingest(directory, manifest, scenarios[sid], knowledge) for sid in run.SCENARIO_IDS]
        budget_ok = sum(row['reserved'] for row in rows) <= manifest['approved_budget']
        return {'directory': directory, 'manifest': manifest, 'dataset': dataset, 'scenarios': scenarios,
                'knowledge': knowledge, 'rows': rows, 'budget_integrity': budget_ok}


def _binding(cohort):
    return {'review_format_version': VERSION, 'cohort_id': cohort['manifest']['cohort_id'],
            'cohort_manifest_sha256': cohort['manifest']['artifact_sha256'],
            'dataset_version': cohort['dataset']['dataset_version'], 'rubric_version': cohort['dataset']['rubric_version'],
            'dataset_sha256': run.sha(cohort['dataset']), 'rubric_sha256': run.sha(cohort['dataset']['rubric']),
            'evaluator_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def _blank():
    return {'reviewer': None, 'reviewed_at': None, 'review_stage': 'initial',
            'dimensions': {name: {'outcome': 'UNEVALUATED', 'explanation': '', 'affected_fields': []}
                           for name in rubric.DIMENSIONS}, 'critical_findings': []}


def review_template(cohort):
    if not cohort['budget_integrity'] or any(row['technical_validation'] == 'FAIL' for row in cohort['rows']):
        raise ReviewInputError('COHORT_INTEGRITY_INVALID')
    binding = _binding(cohort)
    return run._sealed({**binding, 'reviews': [
        {'scenario_id': row['scenario_id'], 'response_sha256': row['response_sha256'],
         'execution_artifact_sha256': row['execution_artifact_sha256'],
         'dataset_sha256': binding['dataset_sha256'], 'rubric_sha256': binding['rubric_sha256'], **_blank()}
        for row in cohort['rows'] if row['response'] is not None]})


def _locations(response, context, knowledge):
    locations = rubric._locations(response, context, knowledge)
    def walk(value, prefix):
        if prefix:
            locations.add(prefix)
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f'{prefix}.{key}' if prefix else key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f'{prefix}[{index}]')
    walk(response, '')
    return locations


def _affected(value, locations, required=False):
    if not isinstance(value, list) or any(not isinstance(item, str) or item not in locations for item in value):
        raise ReviewInputError('AFFECTED_FIELDS_INVALID')
    if len(set(value)) != len(value) or (required and not value):
        raise ReviewInputError('AFFECTED_FIELDS_INVALID')


def validate_reviews(cohort, reviews):
    if reviews is None:
        return {}
    binding = _binding(cohort)
    rubric._object(reviews, (*binding, 'reviews', 'artifact_sha256'))
    if any(reviews[key] != value for key, value in binding.items()):
        raise ReviewInputError('STALE_REVIEW_BINDING')
    payload = {key: value for key, value in reviews.items() if key != 'artifact_sha256'}
    if reviews['artifact_sha256'] != run.sha(payload):
        raise ReviewInputError('MODIFIED_REVIEW_FILE')
    if not isinstance(reviews['reviews'], list):
        raise ReviewInputError('REVIEWS_LIST_INVALID')
    inputs = {row['scenario_id']: row for row in cohort['rows']}
    indexed = {}
    for review in reviews['reviews']:
        rubric._object(review, ('scenario_id', 'response_sha256', 'execution_artifact_sha256',
                               'dataset_sha256', 'rubric_sha256', 'reviewer', 'reviewed_at',
                               'review_stage', 'dimensions', 'critical_findings'))
        sid = rubric._text(review['scenario_id'])
        if sid not in inputs or sid in indexed or inputs[sid]['response'] is None:
            raise ReviewInputError('REVIEW_RESPONSE_UNASSESSABLE_OR_DUPLICATED')
        source = inputs[sid]
        if any(review[key] != source[key] for key in ('response_sha256', 'execution_artifact_sha256')):
            raise ReviewInputError('STALE_RESPONSE_BINDING')
        if any(review[key] != binding[key] for key in ('dataset_sha256', 'rubric_sha256')):
            raise ReviewInputError('STALE_DATASET_OR_RUBRIC')
        if review['review_stage'] not in ('initial', 'adjudication'):
            raise ReviewInputError('REVIEW_STAGE_INVALID')
        scenario = cohort['scenarios'][sid]
        context = rubric.build_context(scenario['input'])
        locations = _locations(source['response'], context, cohort['knowledge'])
        rubric._object(review['dimensions'], rubric.DIMENSIONS)
        has_assessment = False
        for assessment in review['dimensions'].values():
            rubric._object(assessment, ('outcome', 'explanation', 'affected_fields'))
            outcome = assessment['outcome']
            if not isinstance(outcome, str) or outcome not in rubric.OUTCOMES or not isinstance(assessment['explanation'], str):
                raise ReviewInputError('DIMENSION_INVALID')
            if outcome != 'UNEVALUATED':
                rubric._text(assessment['explanation'])
            _affected(assessment['affected_fields'], locations, required=outcome == 'FAIL')
            has_assessment |= outcome != 'UNEVALUATED' or bool(assessment['explanation'].strip()) or bool(assessment['affected_fields'])
        findings = review['critical_findings']
        if not isinstance(findings, list):
            raise ReviewInputError('CRITICAL_FINDINGS_INVALID')
        ids = set()
        for finding in findings:
            rubric._object(finding, ('kind', 'condition_id', 'description', 'affected_fields', 'justification'))
            kind, condition = finding['kind'], rubric._text(finding['condition_id'])
            if condition in ids or kind not in ('scenario_defined', 'additional_safety_critical'):
                raise ReviewInputError('CRITICAL_FINDING_KIND_INVALID')
            ids.add(condition)
            rubric._text(finding['description'])
            _affected(finding['affected_fields'], locations, required=True)
            if kind == 'scenario_defined':
                if condition not in scenario['critical_failure_conditions'] or finding['justification'] is not None:
                    raise ReviewInputError('CRITICAL_CONDITION_INVALID')
            else:
                if condition in scenario['critical_failure_conditions']:
                    raise ReviewInputError('ADDITIONAL_FINDING_ID_INVALID')
                rubric._text(finding['justification'])
        if findings and rubric.aggregate(item['outcome'] for item in review['dimensions'].values()) != 'FAIL':
            raise ReviewInputError('CRITICAL_FINDING_REQUIRES_FAIL')
        if has_assessment or findings or review['reviewer'] is not None or review['reviewed_at'] is not None:
            rubric._text(review['reviewer'])
            _timestamp(review['reviewed_at'])
        indexed[sid] = review
    return indexed


def seal_reviews(cohort, edited):
    """Explicit human edit acknowledgment; validates bindings without inventing verdicts."""
    if not isinstance(edited, dict):
        raise ReviewInputError('REVIEW_OBJECT_INVALID')
    sealed = run._sealed({key: value for key, value in edited.items() if key != 'artifact_sha256'})
    validate_reviews(cohort, sealed)
    return sealed


def generate_report(cohort, reviews=None):
    indexed = validate_reviews(cohort, reviews)
    results, findings = [], []
    for source in cohort['rows']:
        sid = source['scenario_id']
        review = indexed.get(sid, _blank())
        semantic = rubric.aggregate(item['outcome'] for item in review['dimensions'].values())
        complete = source['response'] is not None and all(item['outcome'] != 'UNEVALUATED' for item in review['dimensions'].values())
        results.append({key: value for key, value in source.items() if key != 'response'} | {
            'human_review': review, 'semantic_outcome': semantic, 'fully_reviewed': complete})
        findings.extend({'scenario_id': sid, **finding} for finding in review['critical_findings'])
    total = len(run.SCENARIO_IDS)
    valid = sum(row['response'] is not None for row in cohort['rows'])
    reviewed = sum(row['fully_reviewed'] for row in results)
    passed = sum(row['semantic_outcome'] == 'PASS' for row in results)
    failed = sum(row['semantic_outcome'] == 'FAIL' for row in results)
    unevaluated = total - passed - failed
    integrity = cohort['budget_integrity'] and all(row['technical_validation'] == 'PASS' for row in results)
    complete = valid == total and reviewed == total
    known_model_failure = bool(findings) or failed > 0 or any(
        row['technical_validation'] == 'PASS' and (row['execution_outcome'] in ('FAILED', 'INTERRUPTED')
        or row['structural_validation'] == 'FAIL' or row['permitted_status_check'] == 'FAIL') for row in results)
    model = 'FAIL' if known_model_failure else ('PASS' if integrity and complete and passed == total else 'UNEVALUATED')
    snapshot = [{key: row[key] for key in ('scenario_id', 'reservation_sha256', 'execution_artifact_sha256', 'unassessable_reason')} for row in results]
    return run._sealed({
        'report_format_version': VERSION, **_binding(cohort),
        'execution_snapshot_sha256': run.sha(snapshot), 'reviews_sha256': reviews['artifact_sha256'] if reviews else None,
        'framework_acceptance': 'PASS' if integrity else 'FAIL',
        'technical_evaluation_status': 'PASS' if integrity else 'FAIL',
        'structural_response_validity': 'PASS' if valid == total else ('FAIL' if any(row['structural_validation'] == 'FAIL' for row in results) else 'UNEVALUATED'),
        'human_review_completeness': 'COMPLETE' if complete else 'INCOMPLETE',
        'study_completeness': 'COMPLETE' if integrity and complete else 'INCOMPLETE',
        'model_acceptance': model, 'generated_model_performance': model,
        'safety_critical_findings': 'OBSERVED' if findings else ('NONE_OBSERVED' if complete else 'UNEVALUATED'),
        'metrics': {
            'planned_scenarios': total, 'reserved_attempts': sum(row['reserved'] for row in results),
            'terminal_records': sum(row['terminal_record'] for row in results),
            'completed_execution_attempts': sum(row['execution_outcome'] in ('SUCCESS', 'FAILED') for row in results),
            'valid_responses': rubric._rate(valid, total), 'fully_reviewed_responses': rubric._rate(reviewed, valid),
            'semantic_pass': rubric._rate(passed, total), 'semantic_fail': rubric._rate(failed, total),
            'semantic_unevaluated': rubric._rate(unevaluated, total), 'critical_findings_count': len(findings),
            'unassessable_scenarios': total - valid,
            'missing_scenarios': sum(row['unassessable_reason'] == 'NOT_ATTEMPTED' for row in results),
            'uncertain_reservations': sum(row['execution_outcome'] == 'RESERVED_UNCERTAIN' and row['technical_validation'] == 'PASS' for row in results),
            'interrupted_attempts': sum(row['execution_outcome'] == 'INTERRUPTED' for row in results),
            'invalid_responses': sum(row['structural_validation'] == 'FAIL' for row in results),
            'artifact_integrity_errors': sum(row['technical_validation'] == 'FAIL' for row in results),
            'terminal_generation_failures': sum(row['execution_outcome'] == 'FAILED' for row in results),
            'per_dimension': {name: {value: sum(row['human_review']['dimensions'][name]['outcome'] == value for row in results)
                                   for value in ('PASS', 'FAIL', 'UNEVALUATED')} for name in rubric.DIMENSIONS},
            'totals_reconcile': passed + failed + unevaluated == total and valid + (total - valid) == total,
        }, 'scenarios': results, 'critical_findings': findings,
        'quality_coverage': {name: {'coverage': 'partial',
            'scenario_ids': [scenario['id'] for scenario in cohort['dataset']['scenarios'] if name in scenario['quality_characteristics']],
            'limitations': 'Eight synthetic scenarios and one capture each; no statistical reliability, fairness or runtime intervention claim.'}
            for name in rubric.CHARACTERISTICS},
        'limitations': ['Framework acceptance describes artifact/review integrity; offline test verification is documented separately.',
                       'Human judgments are supplied assertions, not independently authenticated decisions.',
                       'Hashes detect accidental edits, not deliberate rewrites with recomputed hashes.',
                       'Reports reproduce captured evidence; repeat generation is not promised to be deterministic.',
                       'No response bodies or RunnerContext are included; review notes must remain synthetic.',
                       'No live evaluation or Increment 5B-03 is authorized by report generation.'],
    })


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort-dir', type=Path, required=True)
    parser.add_argument('--reviews', type=Path)
    parser.add_argument('--review-template', type=Path)
    parser.add_argument('--seal-reviews', type=Path, help='Explicitly validate and seal human-edited reviews to a new file.')
    parser.add_argument('--review-output', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    try:
        if bool(args.seal_reviews) != bool(args.review_output) or (args.seal_reviews and (args.reviews or args.review_template)):
            raise ReviewInputError('REVIEW_COMMAND_INVALID')
        cohort = load_cohort(args.cohort_dir)
        outputs = [path for path in (args.review_template, args.review_output, args.report) if path]
        if len({path.resolve() for path in outputs}) != len(outputs):
            raise ReviewInputError('OUTPUT_COLLISION')
        for path in outputs:
            if path.parent.resolve() != cohort['directory'] or path.exists() or path.is_symlink():
                raise ReviewInputError('OUTPUT_MUST_BE_NEW_COHORT_FILE')
        reviews = rubric.read_json(args.reviews) if args.reviews else None
        if args.reviews and not isinstance(reviews, dict):
            raise ReviewInputError('REVIEW_OBJECT_INVALID')
        if args.seal_reviews:
            reviews = seal_reviews(cohort, rubric.read_json(args.seal_reviews))
        report = generate_report(cohort, reviews)
        if args.review_template:
            run._write_new(args.review_template, review_template(cohort))
        if args.review_output:
            run._write_new(args.review_output, reviews)
        if args.report:
            run._write_new(args.report, report)
        else:
            print(run.canonical(report).decode('utf-8'))
        return 1 if report['framework_acceptance'] == 'FAIL' or report['model_acceptance'] == 'FAIL' else 0
    except (ReviewInputError, run.ExecutionGuardError, rubric.EvaluationInputError, OSError, ValueError, TypeError, KeyError):
        print('Offline evaluation input, integrity or output is invalid; no review decisions were inferred.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
