"""Versioned human semantic assessment; offline only, no text classifier or model judge."""

import argparse
import hashlib
from pathlib import Path
import sys

from tests.llm.increment5a import evaluate as rubric
from tests.llm.increment5b import evaluate as legacy
from tests.llm.increment5b import run

DESIGN_PATH = Path(__file__).with_name('evaluation_design_v2.json')
VERSION = '5B-EVALUATION-2.0.0'
STATES = ('PASS', 'FAIL', 'UNEVALUATED')
SEVERITIES = ('CRITICAL', 'MAJOR', 'MINOR')


def design():
    return rubric.read_json(DESIGN_PATH)


def binding(cohort):
    specification = design()
    return {**legacy._binding(cohort), 'review_format_version': VERSION,
            'evaluation_versions': {k: v for k, v in specification.items() if k.endswith('_version')},
            'evaluation_design_sha256': run.sha(specification),
            'component_sha256': {k: run.sha(specification[k]) for k in
                                 ('scenarios', 'rubric_interpretation', 'usefulness', 'severity')},
            'v2_evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'legacy_evaluator_sha256': hashlib.sha256(Path(legacy.__file__).read_bytes()).hexdigest(),
            'capture_configuration_sha256': run.sha(cohort['manifest']['configuration'])}


def criteria(sid):
    specification = design()
    return {**specification['common_criteria'], **specification['scenarios'][sid]['criteria']}


def review_template(cohort):
    template = legacy.review_template(cohort)
    rows = []
    for source in template['reviews']:
        row = {k: v for k, v in source.items() if k != 'critical_findings'}
        row.update(oracle={key: {'outcome': 'UNEVALUATED', 'explanation': ''}
                           for key in criteria(row['scenario_id'])},
                   accepted_alternative=None,
                   usefulness={'score': 'UNASSESSABLE', 'explanation': '',
                               'sufficient_evidence': None}, findings=[])
        rows.append(row)
    return run._sealed({**binding(cohort), 'reviews': rows})


def _assessment(value):
    rubric._object(value, ('outcome', 'explanation'))
    if value['outcome'] not in STATES or not isinstance(value['explanation'], str):
        raise legacy.ReviewInputError('ASSESSMENT_INVALID')
    if value['outcome'] != 'UNEVALUATED':
        rubric._text(value['explanation'])


def validate_reviews(cohort, reviews):
    if reviews is None:
        return {}
    expected = binding(cohort)
    rubric._object(reviews, (*expected, 'reviews', 'artifact_sha256'))
    if any(reviews[k] != v for k, v in expected.items()):
        raise legacy.ReviewInputError('STALE_V2_BINDING')
    if reviews['artifact_sha256'] != run.sha({k: v for k, v in reviews.items() if k != 'artifact_sha256'}):
        raise legacy.ReviewInputError('MODIFIED_REVIEW_FILE')
    if not isinstance(reviews['reviews'], list):
        raise legacy.ReviewInputError('REVIEWS_LIST_INVALID')
    historical = {**legacy._binding(cohort), 'reviews': []}
    for row in reviews['reviews']:
        rubric._object(row, ('scenario_id', 'response_sha256', 'execution_artifact_sha256',
                            'dataset_sha256', 'rubric_sha256', 'reviewer', 'reviewed_at',
                            'review_stage', 'dimensions', 'oracle', 'accepted_alternative',
                            'usefulness', 'findings'))
        sid = row['scenario_id']
        if sid not in cohort['scenarios']:
            raise legacy.ReviewInputError('SCENARIO_INVALID')
        rubric._object(row['oracle'], criteria(sid))
        for assessment in row['oracle'].values():
            _assessment(assessment)
        alternative = row['accepted_alternative']
        if alternative is not None and alternative not in design()['scenarios'][sid]['accepted_alternatives']:
            raise legacy.ReviewInputError('ALTERNATIVE_INVALID')
        if all(a['outcome'] == 'PASS' for a in row['oracle'].values()) and alternative is None:
            raise legacy.ReviewInputError('ACCEPTED_ALTERNATIVE_REQUIRED')
        usefulness = row['usefulness']
        rubric._object(usefulness, ('score', 'explanation', 'sufficient_evidence'))
        score = usefulness['score']
        if not (type(score) is int and score in (0, 1, 2)) and score != 'UNASSESSABLE':
            raise legacy.ReviewInputError('USEFULNESS_INVALID')
        if usefulness['sufficient_evidence'] is not None and type(usefulness['sufficient_evidence']) is not bool:
            raise legacy.ReviewInputError('EVIDENCE_STATE_INVALID')
        if not isinstance(usefulness['explanation'], str):
            raise legacy.ReviewInputError('USEFULNESS_EXPLANATION_INVALID')
        if score != 'UNASSESSABLE':
            rubric._text(usefulness['explanation'])
            if usefulness['sufficient_evidence'] is None or (score == 0 and not usefulness['sufficient_evidence']):
                raise legacy.ReviewInputError('USEFULNESS_EVIDENCE_REQUIRED')
        source = next((r for r in cohort['rows'] if r['scenario_id'] == sid), None)
        if source is None or source['response'] is None:
            raise legacy.ReviewInputError('REVIEW_RESPONSE_UNASSESSABLE')
        locations = legacy._locations(source['response'], rubric.build_context(cohort['scenarios'][sid]['input']), cohort['knowledge'])
        findings = row['findings']
        if not isinstance(findings, list):
            raise legacy.ReviewInputError('FINDINGS_INVALID')
        ids, defects = set(), set()
        for finding in findings:
            rubric._object(finding, ('finding_id', 'defect_id', 'severity', 'claim_relation',
                                    'affected_dimensions', 'affected_fields', 'description', 'justification'))
            for key in ('finding_id', 'defect_id', 'description', 'justification'):
                rubric._text(finding[key])
            if finding['finding_id'] in ids or finding['defect_id'] in defects:
                raise legacy.ReviewInputError('DUPLICATE_UNDERLYING_DEFECT')
            ids.add(finding['finding_id'])
            defects.add(finding['defect_id'])
            if finding['severity'] not in SEVERITIES or finding['claim_relation'] not in ('unsupported', 'contradicted', 'other'):
                raise legacy.ReviewInputError('FINDING_CLASSIFICATION_INVALID')
            dimensions = finding['affected_dimensions']
            if not isinstance(dimensions, list) or not dimensions or any(d not in rubric.DIMENSIONS for d in dimensions) or len(set(dimensions)) != len(dimensions):
                raise legacy.ReviewInputError('FINDING_DIMENSIONS_INVALID')
            if any(row['dimensions'][d]['outcome'] != 'FAIL' for d in dimensions):
                raise legacy.ReviewInputError('FINDING_REQUIRES_LINKED_FAIL')
            legacy._affected(finding['affected_fields'], locations, required=True)
        if any(a['outcome'] == 'FAIL' for a in row['oracle'].values()) and not findings:
            raise legacy.ReviewInputError('ORACLE_FAIL_REQUIRES_FINDING')
        failed_dimensions = {d for d, a in row['dimensions'].items() if a['outcome'] == 'FAIL'}
        if failed_dimensions - {d for f in findings for d in f['affected_dimensions']}:
            raise legacy.ReviewInputError('FAIL_REQUIRES_UNIQUE_FINDING')
        # Reuse strict identity, timestamp, locations and response/dataset binding validation.
        historical['reviews'].append({k: v for k, v in row.items()
                                      if k not in ('oracle', 'accepted_alternative', 'usefulness', 'findings')} | {'critical_findings': []})
        if findings or score != 'UNASSESSABLE' or usefulness['explanation'].strip() or any(
                a['outcome'] != 'UNEVALUATED' or a['explanation'].strip() for a in row['oracle'].values()) or alternative is not None:
            rubric._text(row['reviewer'])
            legacy._timestamp(row['reviewed_at'])
    legacy.validate_reviews(cohort, run._sealed(historical))
    return {row['scenario_id']: row for row in reviews['reviews']}


def seal_reviews(cohort, edited):
    if not isinstance(edited, dict):
        raise legacy.ReviewInputError('REVIEW_OBJECT_INVALID')
    sealed = run._sealed({k: v for k, v in edited.items() if k != 'artifact_sha256'})
    validate_reviews(cohort, sealed)
    return sealed


def _aggregate(values):
    values = list(values)
    return 'FAIL' if 'FAIL' in values else ('UNEVALUATED' if 'UNEVALUATED' in values else 'PASS')


def generate_report(cohort, reviews=None):
    indexed = validate_reviews(cohort, reviews)
    rows, findings = [], []
    for source in cohort['rows']:
        review = indexed.get(source['scenario_id'])
        retained = source['response'] is not None
        semantic = 'UNASSESSABLE' if not retained else 'UNEVALUATED'
        safety = correctness = semantic
        useful = 'UNASSESSABLE'
        opportunity = False
        if review:
            correctness = _aggregate(review['dimensions'][d]['outcome'] for d in rubric.DIMENSIONS if d != 'constraints_and_safety')
            safety = review['dimensions']['constraints_and_safety']['outcome']
            useful = review['usefulness']['score']
            opportunity = useful == 1
            semantic = _aggregate([correctness, safety, *[a['outcome'] for a in review['oracle'].values()]])
            if useful == 0:
                semantic = 'FAIL'
            elif useful == 'UNASSESSABLE' and semantic == 'PASS':
                semantic = 'UNEVALUATED'
            findings.extend({'scenario_id': source['scenario_id'], **f} for f in review['findings'])
        rows.append({k: v for k, v in source.items() if k != 'response'} | {
            'semantic_outcome': semantic, 'correctness': correctness, 'safety': safety,
            'usefulness': useful, 'improvement_opportunity': opportunity, 'human_review': review,
            'technical_contract_state': 'TECHNICAL_CONTRACT_VIOLATION' if source['structural_validation'] == 'FAIL' or source['safe_error_code'] == 'DOMAIN_VALIDATION_FAILURE' else source['structural_validation']})
    integrity = cohort['budget_integrity'] and all(r['technical_validation'] == 'PASS' for r in rows)
    semantic = _aggregate('UNEVALUATED' if r['semantic_outcome'] == 'UNASSESSABLE' else r['semantic_outcome'] for r in rows)
    technical_failure = any(r['execution_outcome'] in ('FAILED', 'INTERRUPTED') or r['structural_validation'] == 'FAIL' for r in rows)
    acceptance = 'FAIL' if semantic == 'FAIL' or technical_failure else ('PASS' if integrity and semantic == 'PASS' else 'UNEVALUATED')
    return run._sealed({**binding(cohort), 'report_format_version': VERSION,
        'reviews_sha256': reviews['artifact_sha256'] if reviews else None,
        'execution_snapshot_sha256': run.sha([{k: v for k, v in r.items() if k != 'response'} for r in cohort['rows']]),
        'technical_integrity': 'PASS' if integrity else 'FAIL', 'semantic_outcome': semantic,
        'model_acceptance': acceptance, 'scenarios': rows, 'findings': findings,
        'metrics': {'planned_scenarios': len(rows), 'unique_findings': len(findings),
            'severity_counts': {s: sum(f['severity'] == s for f in findings) for s in SEVERITIES},
            'semantic_counts': {s: sum(r['semantic_outcome'] == s for r in rows) for s in (*STATES, 'UNASSESSABLE')},
            'usefulness_counts': {str(s): sum(r['usefulness'] == s for r in rows) for s in (0, 1, 2, 'UNASSESSABLE')},
            'improvement_opportunities': sum(r['improvement_opportunity'] for r in rows)},
        'limitations': ['Human assertions, not an automated semantic judge or authenticated reviewer identity.',
            'Eight synthetic scenarios; offline tests establish tooling behavior, not real-model reliability.',
            'No historical verdict migration; v1 results retain their original interpretation.',
            'Current frozen configuration guards apply; stale cohorts require their matching source snapshot.']})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort-dir', type=Path, required=True)
    parser.add_argument('--reviews', type=Path)
    parser.add_argument('--review-template', type=Path)
    parser.add_argument('--seal-reviews', type=Path)
    parser.add_argument('--review-output', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    try:
        if bool(args.seal_reviews) != bool(args.review_output) or (args.seal_reviews and (args.reviews or args.review_template)):
            raise legacy.ReviewInputError('REVIEW_COMMAND_INVALID')
        cohort = legacy.load_cohort(args.cohort_dir)
        outputs = [p for p in (args.review_template, args.review_output, args.report) if p]
        if len({p.resolve() for p in outputs}) != len(outputs):
            raise legacy.ReviewInputError('OUTPUT_COLLISION')
        for path in outputs:
            if path.parent.resolve() != cohort['directory'] or path.exists() or path.is_symlink():
                raise legacy.ReviewInputError('OUTPUT_MUST_BE_NEW_COHORT_FILE')
        reviews = rubric.read_json(args.reviews) if args.reviews else None
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
        return 1 if report['technical_integrity'] == 'FAIL' or report['model_acceptance'] == 'FAIL' else 0
    except (ValueError, OSError, TypeError, KeyError):
        print('Offline v2 evaluation input, integrity or output is invalid; no decisions inferred.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
