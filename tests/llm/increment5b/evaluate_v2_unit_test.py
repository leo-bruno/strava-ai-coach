"""Deterministic TEST-ONLY assessments; no real reviewer or model acceptance evidence."""

import copy
import hashlib
from pathlib import Path
import socket

import pytest

from tests.llm.increment5a import evaluate as rubric
from tests.llm.increment5b import evaluate as legacy
from tests.llm.increment5b import evaluate_v2 as ev
from tests.llm.increment5b import run


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No network or generation permitted')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(run.coach, 'OpenAI', forbidden)
    monkeypatch.setattr(run.coach, 'generate_coach_response', forbidden)


@pytest.fixture
def cohort():
    dataset = rubric.validate_dataset(rubric.read_json(rubric.DATASET_PATH))
    scenarios = {s['id']: s for s in dataset['scenarios']}
    rows = []
    for sid, scenario in scenarios.items():
        response = scenario['controls'][0]['response']
        rows.append(dict(scenario_id=sid, response=copy.deepcopy(response), response_sha256=run.sha(response),
                         execution_artifact_sha256=run.sha(sid), reservation_sha256=run.sha([sid]),
                         reserved=True, terminal_record=True, execution_outcome='SUCCESS',
                         technical_validation='PASS', structural_validation='PASS',
                         permitted_status_check='PASS', unassessable_reason=None, safe_error_code=None))
    return dict(dataset=dataset, scenarios=scenarios, rows=rows, budget_integrity=True,
                knowledge=run.load_training_knowledge(), manifest={'cohort_id':'TEST_ONLY',
                'artifact_sha256':run.sha('TEST_ONLY'), 'configuration':{'TEST_ONLY':True}})


def assessed(cohort, score=2):
    reviews = ev.review_template(cohort)
    for row in reviews['reviews']:
        row.update(reviewer='TEST_ONLY', reviewed_at='2026-10-20T12:00:00+02:00',
                   accepted_alternative=ev.design()['scenarios'][row['scenario_id']]['accepted_alternatives'][0])
        for assessment in [*row['dimensions'].values(), *row['oracle'].values()]:
            assessment.update(outcome='PASS', explanation='TEST ONLY supplied assessment')
        row['usefulness'].update(score=score, sufficient_evidence=True, explanation='TEST ONLY contextual assessment')
    return reviews


def finding(row, severity='MAJOR', relation='unsupported', defect='one_defect'):
    dimensions = ['factual_correctness', 'evidence_grounding']
    for d in dimensions:
        row['dimensions'][d].update(outcome='FAIL', explanation='TEST ONLY defect', affected_fields=['current_state.text'])
    row['findings'].append(dict(finding_id=defect, defect_id=defect, severity=severity,
        claim_relation=relation, affected_dimensions=dimensions, affected_fields=['current_state.text'],
        description='TEST ONLY observed defect', justification='TEST ONLY severity justification'))


def test_blank_reviews_do_not_infer_acceptance(cohort):
    template = ev.review_template(cohort)
    report = ev.generate_report(cohort, template)
    assert report['model_acceptance'] == 'UNEVALUATED'
    assert report['metrics']['usefulness_counts']['UNASSESSABLE'] == 8
    assert len(template['reviews'][0]['dimensions']) == 6
    assert 'expected_semantic_outcome' not in str(template)


@pytest.mark.parametrize('sid,alternative', [(sid, alternative) for sid, oracle in ev.design()['scenarios'].items() for alternative in oracle['accepted_alternatives']])
def test_scenario_acceptance_alternatives(cohort, sid, alternative):
    reviews = assessed(cohort)
    next(r for r in reviews['reviews'] if r['scenario_id'] == sid)['accepted_alternative'] = alternative
    report = ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))
    assert report['model_acceptance'] == 'PASS'


@pytest.mark.parametrize('score,outcome,opportunities', [(2,'PASS',0), (1,'PASS',8), (0,'FAIL',0), ('UNASSESSABLE','UNEVALUATED',0)])
def test_usefulness_independent_acceptance(cohort, score, outcome, opportunities):
    reviews = ev.seal_reviews(cohort, assessed(cohort, score))
    report = ev.generate_report(cohort, reviews)
    assert report['model_acceptance'] == outcome
    assert report['metrics']['improvement_opportunities'] == opportunities


@pytest.mark.parametrize('severity', ev.SEVERITIES)
@pytest.mark.parametrize('relation', ['unsupported','contradicted','other'])
def test_unique_finding_count_and_no_usefulness_compensation(cohort, severity, relation):
    reviews = assessed(cohort)
    finding(reviews['reviews'][0], severity, relation)
    report = ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))
    assert report['metrics']['unique_findings'] == 1
    assert report['metrics']['severity_counts'][severity] == 1
    assert report['model_acceptance'] == 'FAIL'
    assert report['scenarios'][0]['usefulness'] == 2
    assert report['findings'][0]['claim_relation'] == relation


def test_duplicate_defect_rejected_across_dimensions(cohort):
    reviews = assessed(cohort)
    row = reviews['reviews'][0]
    finding(row)
    duplicate = copy.deepcopy(row['findings'][0])
    duplicate['finding_id'] = 'different_identifier_same_defect'
    row['findings'].append(duplicate)
    with pytest.raises(ValueError, match='DUPLICATE_UNDERLYING_DEFECT'):
        ev.seal_reviews(cohort, reviews)


@pytest.mark.parametrize('sid', ['5A-03','5A-04','5A-08'])
def test_blanket_abstention_fails_partial_guidance_oracle(cohort, sid):
    reviews = assessed(cohort)
    row = next(r for r in reviews['reviews'] if r['scenario_id'] == sid)
    row['oracle']['partial_guidance'].update(outcome='FAIL', explanation='TEST ONLY blanket abstention')
    row['usefulness'].update(score=0)
    finding(row)
    report = ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))
    assert report['model_acceptance'] == 'FAIL'


@pytest.mark.parametrize('sid', ['5A-05','5A-06','5A-07'])
def test_justified_boundary_explanation_is_useful(cohort, sid):
    reviews = assessed(cohort)
    row = next(r for r in reviews['reviews'] if r['scenario_id'] == sid)
    row['usefulness']['sufficient_evidence'] = False
    assert ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))['model_acceptance'] == 'PASS'


@pytest.mark.parametrize('severity', ['CRITICAL','MAJOR','MINOR'])
def test_zero_availability_severity_requires_explicit_judgment(cohort, severity):
    reviews = assessed(cohort)
    row = reviews['reviews'][5]
    finding(row, severity)
    # No automatic escalation based on incidental wording or scenario identity.
    assert ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))['findings'][0]['severity'] == severity


def test_independent_medical_findings_counted_once_each(cohort):
    reviews = assessed(cohort)
    row = reviews['reviews'][6]
    for defect in ('diagnosis', 'clearance', 'unsupported_continuation'):
        finding(row, 'CRITICAL', defect=defect)
    assert ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))['metrics']['unique_findings'] == 3


def test_independent_injection_findings_and_canary_definition(cohort):
    reviews = assessed(cohort)
    row = reviews['reviews'][7]
    for defect in ('constraint_override', 'fabricated_authority'):
        finding(row, 'CRITICAL', defect=defect)
    report = ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))
    assert report['metrics']['unique_findings'] == 2
    assert 'not demonstrated secret exfiltration' in ev.criteria('5A-08')['canary']


def test_missing_retained_response_is_unassessable_not_semantic_failure(cohort):
    cohort['rows'][0].update(response=None, response_sha256=None, execution_outcome='FAILED',
                             structural_validation='FAIL', safe_error_code='DOMAIN_VALIDATION_FAILURE')
    report = ev.generate_report(cohort)
    assert report['scenarios'][0]['semantic_outcome'] == 'UNASSESSABLE'
    assert report['scenarios'][0]['technical_contract_state'] == 'TECHNICAL_CONTRACT_VIOLATION'
    assert report['technical_integrity'] == 'PASS'
    assert report['model_acceptance'] == 'FAIL'


def test_integrity_failure_does_not_establish_model_success(cohort):
    cohort['rows'][0]['technical_validation'] = 'FAIL'
    report = ev.generate_report(cohort)
    assert report['technical_integrity'] == 'FAIL'
    assert report['model_acceptance'] == 'UNEVALUATED'


@pytest.mark.parametrize('key', ['evaluation_design_sha256','v2_evaluator_sha256','capture_configuration_sha256','dataset_sha256','rubric_sha256'])
def test_fingerprint_isolation(cohort, key):
    reviews = ev.review_template(cohort)
    reviews[key] = 'STALE'
    with pytest.raises(ValueError, match='STALE_V2_BINDING'):
        ev.seal_reviews(cohort, reviews)


def test_no_automatic_historical_review_migration(cohort):
    with pytest.raises(ValueError):
        ev.validate_reviews(cohort, legacy.review_template(cohort))
    with pytest.raises(ValueError):
        legacy.validate_reviews(cohort, ev.review_template(cohort))


@pytest.mark.parametrize('mutation', [
    lambda r: r['usefulness'].update(score=True),
    lambda r: r['usefulness'].update(score=0, sufficient_evidence=False),
    lambda r: r.update(accepted_alternative='invented_schedule'),
    lambda r: r.update(accepted_alternative=None),
    lambda r: r.update(reviewer=None),
    lambda r: r['dimensions']['factual_correctness'].update(outcome='FAIL',affected_fields=['response']),
])
def test_invalid_review_contracts(cohort, mutation):
    reviews = assessed(cohort)
    mutation(reviews['reviews'][0])
    with pytest.raises(ValueError):
        ev.seal_reviews(cohort, reviews)


def test_deterministic_reports_do_not_modify_evidence(cohort):
    before = copy.deepcopy(cohort)
    reviews = ev.seal_reviews(cohort, assessed(cohort))
    assert run.canonical(ev.generate_report(cohort,reviews)) == run.canonical(ev.generate_report(cohort,reviews))
    assert cohort == before
    assert ev.design()['rubric_interpretation'].keys() == dict.fromkeys(rubric.DIMENSIONS).keys()


def test_historical_files_unchanged_by_workflow(cohort):
    paths = [p for root in (rubric.DATASET_PATH.parent, run.ARTIFACT_ROOT) if root.exists()
             for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    ev.generate_report(cohort, ev.seal_reviews(cohort, assessed(cohort)))
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_cli_template_seal_report_and_protected_outputs(cohort, monkeypatch, tmp_path):
    cohort['directory'] = tmp_path
    monkeypatch.setattr(legacy, 'load_cohort', lambda _: cohort)
    template = tmp_path / 'v2-template.json'
    report = tmp_path / 'v2-initial.json'
    base = ['--cohort-dir', str(tmp_path)]
    assert ev.main(base + ['--review-template', str(template), '--report', str(report)]) == 0
    edited = tmp_path / 'v2-edited.json'
    edited.write_bytes(run.canonical(assessed(cohort)))
    sealed = tmp_path / 'v2-confirmed.json'
    assert ev.main(base + ['--seal-reviews',str(edited),'--review-output',str(sealed)]) == 0
    final = tmp_path / 'v2-final.json'
    assert ev.main(base + ['--reviews', str(sealed), '--report', str(final)]) == 0
    assert rubric.read_json(final)['model_acceptance'] == 'PASS'
    assert ev.main(base + ['--report', str(final)]) == 2
    assert ev.main(base + ['--report',str(tmp_path.parent / 'outside.json')]) == 2
    assert ev.main(base + ['--report',str(tmp_path/'collision.json'),'--review-template',str(tmp_path/'collision.json')]) == 2
    assert ev.main(base + ['--seal-reviews',str(edited)]) == 2


def test_cli_failure_exit(cohort, monkeypatch, tmp_path):
    cohort['directory'] = tmp_path
    monkeypatch.setattr(legacy, 'load_cohort', lambda _: cohort)
    cohort['rows'][0].update(execution_outcome='FAILED', response=None)
    assert ev.main(['--cohort-dir',str(tmp_path)]) == 1


@pytest.mark.parametrize('mutation', [
    lambda r: r.update(findings='invalid'),
    lambda r: r['usefulness'].update(sufficient_evidence='yes'),
    lambda r: r['usefulness'].update(explanation=3),
    lambda r: r['oracle']['authority'].update(outcome='INVALID'),
    lambda r: r.update(scenario_id='UNKNOWN'),
])
def test_additional_malformed_reviews(cohort, mutation):
    reviews = assessed(cohort)
    mutation(reviews['reviews'][0])
    with pytest.raises(ValueError):
        ev.seal_reviews(cohort, reviews)


@pytest.mark.parametrize('mutation', [
    lambda f: f.update(severity='TECHNICAL_CONTRACT_VIOLATION'),
    lambda f: f.update(claim_relation='unknown'),
    lambda f: f.update(affected_dimensions=[]),
    lambda f: f.update(affected_dimensions=['constraints_and_safety']),
    lambda f: f.update(affected_fields=['nonexistent']),
])
def test_invalid_finding_contract(cohort, mutation):
    reviews = assessed(cohort)
    finding(reviews['reviews'][0])
    mutation(reviews['reviews'][0]['findings'][0])
    with pytest.raises(ValueError):
        ev.seal_reviews(cohort,reviews)


def test_oracle_fail_requires_finding(cohort):
    reviews = assessed(cohort)
    reviews['reviews'][0]['oracle']['authority'].update(outcome='FAIL')
    with pytest.raises(ValueError, match='ORACLE_FAIL_REQUIRES_FINDING'):
        ev.seal_reviews(cohort,reviews)


def test_tampered_hash_and_missing_evidence(cohort):
    reviews = ev.review_template(cohort)
    reviews['artifact_sha256'] = 'tampered'
    with pytest.raises(ValueError, match='MODIFIED_REVIEW_FILE'):
        ev.validate_reviews(cohort,reviews)
    reviews = assessed(cohort)
    cohort['rows'][0]['response'] = None
    with pytest.raises(ValueError, match='REVIEW_RESPONSE_UNASSESSABLE'):
        ev.seal_reviews(cohort,reviews)
    with pytest.raises(ValueError):
        ev.seal_reviews(cohort, [])
