"""Deterministic tooling tests; simulated reviews are NOT actual human verdicts."""

import copy
import json
from pathlib import Path
import socket

import pytest

from tests.llm.increment5a import evaluate as ev


@pytest.fixture
def dataset():
    return ev.read_json(ev.DATASET_PATH)


@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch):
    def prohibited(*args, **kwargs):
        raise AssertionError('Offline evaluation must not access the network.')
    monkeypatch.setattr(socket, 'create_connection', prohibited)
    monkeypatch.setattr(socket.socket, 'connect', prohibited)


def simulated_reviews(dataset):
    """Test data only. Never write these as repository acceptance evidence."""
    reviews = ev.review_template(dataset)
    controls = {c['id']: c for s in dataset['scenarios'] for c in s['controls']}
    for row in reviews['reviews']:
        row['reviewer'] = 'TEST_ONLY_SIMULATED_REVIEWER'
        row['reviewed_at'] = '2026-10-13T12:00:00+00:00'
        for item in row['dimensions'].values():
            item.update(outcome='PASS', explanation='TEST ONLY: simulated dimension assessment.')
        control = controls[row['control_id']]
        if control['expected_semantic_outcome'] == 'FAIL':
            row['dimensions']['factual_correctness'].update(
                outcome='FAIL', explanation='TEST ONLY: simulated defect finding.',
                affected_statement_or_reference='current_state')
            row['critical_failures'] = [dict(condition_id=condition,
                explanation='TEST ONLY: simulated critical finding.',
                affected_statement_or_reference='current_state')
                for condition in control['expected_critical_failures']]
    return reviews


def test_exact_dataset_and_registered_controls(dataset):
    assert ev.validate_dataset(dataset) is dataset
    assert [s['id'] for s in dataset['scenarios']] == [f'5A-{i:02}' for i in range(1, 9)]
    assert len({c['id'] for s in dataset['scenarios'] for c in s['controls']}) == 16
    assert {v for s in dataset['scenarios'] for v in s['quality_characteristics']} == set(ev.CHARACTERISTICS)
    report = ev.generate_report(dataset)
    assert report['metrics']['structural_acceptance'] == dict(numerator=16, denominator=16, rate=1)
    assert all(row['permitted_status_check'] == 'PASS' for row in report['controls'])
    assert all(value['coverage'] == 'partial' and value['scenario_ids'] for value in report['quality_coverage'].values())


def test_no_automatic_semantic_pass_and_totals(dataset):
    report = ev.generate_report(dataset)
    assert report['generated_model_performance'] == 'UNEVALUATED'
    assert report['increment5a_status'] == 'PENDING_HUMAN_REVIEW'
    assert report['evaluation_framework_outcome'] == 'UNEVALUATED'
    assert report['metrics']['overall_outcomes'] == {'PASS': 0, 'FAIL': 0, 'UNEVALUATED': 16}
    assert report['metrics']['human_label_agreement'] == dict(numerator=0, denominator=0, rate=None)
    assert report['metrics']['human_review_coverage'] == dict(numerator=0, denominator=16, rate=0)
    assert report['metrics']['positive_controls_accepted']['numerator'] == 0
    assert report['metrics']['negative_controls_rejected']['numerator'] == 0
    assert report['metrics']['totals_reconcile']
    assert all(row['expectation_comparison'] == 'UNEVALUATED' for row in report['controls'])
    for metric in report['metrics']['rubric_dimensions'].values():
        assert metric['outcomes'] == {'PASS': 0, 'FAIL': 0, 'UNEVALUATED': 16}
        assert metric['pass_rate']['denominator'] == 16


def test_expected_labels_never_supply_reviews(dataset):
    before = ev.generate_report(dataset)
    for scenario in dataset['scenarios']:
        scenario['controls'].reverse()
    after = ev.generate_report(dataset)
    assert before['metrics'] == after['metrics']
    template = ev.review_template(dataset)
    assert 'expected_semantic_outcome' not in json.dumps(template)
    assert ev.generate_report(dataset, template)['metrics'] == after['metrics']


@pytest.mark.parametrize('values,expected', [(['PASS']*6,'PASS'), (['PASS']*5+['UNEVALUATED'],'UNEVALUATED'),
    (['UNEVALUATED']*6,'UNEVALUATED'), (['FAIL']+['UNEVALUATED']*5,'FAIL'), (['FAIL']+['PASS']*5,'FAIL')])
def test_aggregation(values, expected):
    assert ev.aggregate(values) == expected


@pytest.mark.parametrize('values', [[], ['PASS']*5, ['PASS']*7, ['PASS']*5+['UNKNOWN']])
def test_invalid_aggregation(values):
    with pytest.raises(ev.EvaluationInputError): ev.aggregate(values)


def test_simulated_completed_reviews_reconcile_only_in_unit_test(dataset):
    report = ev.generate_report(dataset, simulated_reviews(dataset))
    assert report['evaluation_framework_outcome'] == 'PASS'
    assert report['increment5a_status'] == 'COMPLETE'
    assert set(report['acceptance_criteria'].values()) == {'PASS'}
    assert report['metrics']['overall_outcomes'] == {'PASS': 8, 'FAIL': 8, 'UNEVALUATED': 0}
    assert report['metrics']['human_label_agreement'] == dict(numerator=16, denominator=16, rate=1)
    assert report['metrics']['human_review_coverage']['numerator'] == 16
    assert report['metrics']['critical_findings_count'] == 8
    assert report['generated_model_performance'] == 'UNEVALUATED'


def test_partially_failed_review_does_not_finish_all_dimensions(dataset):
    reviews = simulated_reviews(dataset)
    reviews['reviews'][1]['dimensions']['transparency']['outcome'] = 'UNEVALUATED'
    report = ev.generate_report(dataset, reviews)
    assert report['controls'][1]['human_semantic_outcome'] == 'FAIL'
    assert report['acceptance_criteria']['all_six_dimensions_reviewed'] == 'PENDING'
    assert report['metrics']['human_review_coverage']['numerator'] == 15
    assert report['increment5a_status'] == 'PENDING_HUMAN_REVIEW'


def test_missing_reviews_and_explicit_uncertain_adjudication(dataset):
    reviews = ev.review_template(dataset)
    row = reviews['reviews'][0]
    row['reviewer'] = 'TEST_ONLY_SIMULATED_REVIEWER'
    row['reviewed_at'] = '2026-10-13T12:00:00+00:00'
    row['dimensions']['factual_correctness']['explanation'] = 'TEST ONLY: uncertain support.'
    reviews['reviews'] = [row]
    report = ev.generate_report(dataset, reviews)
    assert report['metrics']['human_review_coverage']['numerator'] == 0
    row['review_stage'] = 'adjudication'
    for item in row['dimensions'].values():
        item.update(outcome='PASS', explanation='TEST ONLY: explicitly adjudicated.')
    report = ev.generate_report(dataset, reviews)
    assert report['controls'][0]['human_semantic_outcome'] == 'PASS'
    assert report['controls'][0]['human_review']['review_stage'] == 'adjudication'
    assert report['increment5a_status'] == 'PENDING_HUMAN_REVIEW'


@pytest.mark.parametrize('control_index', [0, 1])
def test_wrong_human_verdict_blocks_evaluator_acceptance(dataset, control_index):
    reviews = simulated_reviews(dataset)
    row = reviews['reviews'][control_index]
    if control_index == 0:
        row['dimensions']['factual_correctness'].update(outcome='FAIL', affected_statement_or_reference='current_state')
    else:
        row['dimensions']['factual_correctness']['outcome'] = 'PASS'
        row['critical_failures'] = []
    report = ev.generate_report(dataset, reviews)
    assert report['evaluation_framework_outcome'] == 'FAIL'
    assert report['increment5a_status'] == 'BLOCKED'
    if control_index == 1:
        assert report['acceptance_criteria']['no_critical_negative_human_pass'] == 'FAIL'


def test_critical_failure_must_be_explicitly_identified(dataset):
    reviews = simulated_reviews(dataset)
    reviews['reviews'][1]['critical_failures'] = []
    report = ev.generate_report(dataset, reviews)
    assert report['acceptance_criteria']['negative_controls_human_fail'] == 'PASS'
    assert report['acceptance_criteria']['critical_negative_controls_identified'] == 'FAIL'
    assert report['metrics']['critical_negatives_identified'] == dict(numerator=7, denominator=8, rate=7/8)


@pytest.mark.parametrize('defect', ['unknown_evidence','unknown_knowledge','malformed','unauthorized_count'])
def test_structural_gate_stays_separate(dataset, defect):
    control = dataset['scenarios'][0]['controls'][0]['response']
    if defect == 'unknown_evidence': control['current_state']['evidence_references'] = ['SYNTHETIC_PRIVATE_SENTINEL']
    elif defect == 'unknown_knowledge': control['current_state']['knowledge_references'] = ['UNKNOWN@1']
    elif defect == 'malformed': del control['current_state']['text']
    else: control['next_week_recommendation']['recommended_running_days'] = 2
    reviews = simulated_reviews(dataset)
    report = ev.generate_report(dataset, reviews)
    row = report['controls'][0]
    assert row['human_semantic_outcome'] == 'PASS'
    assert row['structural_validation'] == 'FAIL'
    assert row['overall_outcome'] == 'FAIL'
    assert row['structural_error_code'] == 'DOMAIN_VALIDATION_REJECTED'
    assert report['increment5a_status'] == 'BLOCKED'
    assert 'SYNTHETIC_PRIVATE_SENTINEL' not in json.dumps(report)


def test_permitted_status_is_independent_of_domain_parser(dataset):
    dataset['scenarios'][0]['permitted_statuses'] = ['insufficient_support']
    report = ev.generate_report(dataset)
    assert report['controls'][0]['structural_validation'] == 'PASS'
    assert report['controls'][0]['permitted_status_check'] == 'FAIL'
    assert report['controls'][0]['human_semantic_outcome'] == 'UNEVALUATED'
    assert report['controls'][0]['overall_outcome'] == 'FAIL'
    assert report['evaluation_framework_outcome'] == 'FAIL'


def test_unrealistic_scenario_has_explicit_authored_oracle_not_runtime_threshold(dataset):
    scenario = dataset['scenarios'][4]
    assert scenario['permitted_statuses'] == ['insufficient_support','clarification_required']
    assert [w['distance_meters'] for w in scenario['input']['weeks']] == [8000,9000,10000,11000]
    assert {w['moving_time_seconds'] for w in scenario['input']['weeks']} == {300}
    assert 'unrealistic' in scenario['controls'][0]['response']['current_state']['text']
    assert 'race readiness' in scenario['controls'][1]['response']['current_state']['text']
    assert all(c['response']['next_week_recommendation'] is None for c in scenario['controls'])


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(provenance='model_output'),
    lambda d: d.update(scenarios=d['scenarios'][:-1]),
    lambda d: d.update(dataset_version=''),
    lambda d: d['rubric'].pop('transparency'),
    lambda d: d['quality_coverage']['Transparency'].update(coverage='complete'),
    lambda d: d['scenarios'][0].update(id='5A-09'),
    lambda d: d['scenarios'][1].update(id='5A-01'),
    lambda d: d['scenarios'][0].update(known_facts=[]),
    lambda d: d['scenarios'][0].update(permitted_statuses=['unknown']),
    lambda d: d['scenarios'][0].update(quality_characteristics=['unknown']),
    lambda d: d['scenarios'][0].update(approved_knowledge={}),
    lambda d: d['scenarios'][0].update(approved_knowledge={'UNKNOWN@1':'not authorized'}),
    lambda d: d['scenarios'][0].update(critical_failure_conditions={}),
    lambda d: d['scenarios'][0].update(controls=[]),
    lambda d: d['scenarios'][0]['controls'][0].update(id='BAD'),
    lambda d: d['scenarios'][0]['controls'][0].update(expected_semantic_outcome='UNEVALUATED'),
    lambda d: d['scenarios'][0]['controls'][0].update(response=[]),
    lambda d: d['scenarios'][0]['controls'][1].update(expected_critical_failures=['unknown']),
    lambda d: d['scenarios'][0]['controls'][1].update(expected_critical_failures=[]),
    lambda d: d['scenarios'][0]['controls'][1].update(expected_semantic_outcome='PASS',expected_critical_failures=[]),
    lambda d: d['scenarios'][0]['input'].update(weeks='invalid'),
    lambda d: d['scenarios'][0]['input']['weeks'][0].update(activity_count=-1),
    lambda d: d['scenarios'][0]['input']['weeks'][0].update(activity_count=0),
    lambda d: d['scenarios'][0]['input'].update(reference_datetime='invalid'),
])
def test_dataset_defects_rejected(dataset, mutation):
    mutation(dataset)
    with pytest.raises(ev.EvaluationInputError): ev.validate_dataset(dataset)


def test_missing_quality_mapping_rejected(dataset):
    for scenario in dataset['scenarios']:
        scenario['quality_characteristics'] = [v for v in scenario['quality_characteristics'] if v != 'Intervenability']
    with pytest.raises(ev.EvaluationInputError): ev.validate_dataset(dataset)


@pytest.mark.parametrize('field', ['review_format_version','dataset_version','rubric_version','dataset_sha256','fingerprints'])
def test_stale_reviews_rejected(dataset, field):
    reviews = ev.review_template(dataset)
    reviews[field] = 'STALE'
    with pytest.raises(ev.EvaluationInputError): ev.generate_report(dataset, reviews)


@pytest.mark.parametrize('defect', ['duplicate','unknown','scenario','response_hash','stage','missing_dimension',
    'bad_outcome','no_explanation','no_location','invalid_location','nontext_explanation','no_reviewer',
    'naive_timestamp','bad_timestamp','unknown_critical','duplicate_critical','critical_no_fail','critical_bad_location',
    'dimensions_list','reviews_list','findings_list'])
def test_invalid_human_review_rejected(dataset, defect):
    reviews = simulated_reviews(dataset)
    row = reviews['reviews'][1]
    item = row['dimensions']['factual_correctness']
    if defect == 'duplicate': reviews['reviews'].append(copy.deepcopy(row))
    elif defect == 'unknown': row['control_id'] = 'unknown'
    elif defect == 'scenario': row['scenario_id'] = '5A-08'
    elif defect == 'response_hash': row['response_sha256'] = 'stale'
    elif defect == 'stage': row['review_stage'] = 'automatic'
    elif defect == 'missing_dimension': row['dimensions'].pop('transparency')
    elif defect == 'bad_outcome': item['outcome'] = 'YES'
    elif defect == 'no_explanation': item['explanation'] = ''
    elif defect == 'no_location': item['affected_statement_or_reference'] = None
    elif defect == 'invalid_location': item['affected_statement_or_reference'] = 'unknown'
    elif defect == 'nontext_explanation': item['explanation'] = 42
    elif defect == 'no_reviewer': row['reviewer'] = None
    elif defect == 'naive_timestamp': row['reviewed_at'] = '2026-10-13T12:00:00'
    elif defect == 'bad_timestamp': row['reviewed_at'] = 'yesterday'
    elif defect == 'unknown_critical': row['critical_failures'][0]['condition_id'] = 'unknown'
    elif defect == 'duplicate_critical': row['critical_failures'] *= 2
    elif defect == 'critical_no_fail': item['outcome'] = 'PASS'
    elif defect == 'critical_bad_location': row['critical_failures'][0]['affected_statement_or_reference'] = 'unknown'
    elif defect == 'dimensions_list': row['dimensions'] = []
    elif defect == 'reviews_list': reviews['reviews'] = {}
    else: row['critical_failures'] = {}
    with pytest.raises(ev.EvaluationInputError): ev.generate_report(dataset, reviews)


def test_fingerprints_bind_changes_and_inputs_unchanged(dataset):
    original = copy.deepcopy(dataset)
    reviews = ev.review_template(dataset)
    context_before = ev.build_context(dataset['scenarios'][0]['input'])
    report = ev.generate_report(dataset, reviews)
    assert dataset == original
    assert context_before == ev.build_context(dataset['scenarios'][0]['input'])
    assert reviews == ev.review_template(dataset)
    assert report['fingerprints']['knowledge_reference'] == 'AI_COACH_V1_KNOWLEDGE@1.0.0'
    assert len(report['fingerprints']['prompt_sha256']) == 64
    dataset['scenarios'][0]['controls'][0]['response']['current_state']['text'] += ' changed'
    with pytest.raises(ev.EvaluationInputError): ev.generate_report(dataset, reviews)


def test_metadata_report_omits_authored_responses_and_context(dataset):
    report = json.dumps(ev.generate_report(dataset))
    for scenario in dataset['scenarios']:
        context = scenario['input']['request']['runner_context']
        if context: assert context not in report
        for control in scenario['controls']:
            assert control['response']['current_state']['text'] not in report
    assert 'SYNTHETIC_SECRET_5A08' not in report
    assert 'runner_context' not in report


@pytest.mark.parametrize('payload', ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', 'not json'])
def test_bad_json_safe_error(tmp_path, payload):
    path = tmp_path / 'input.json'; path.write_text(payload)
    with pytest.raises(ev.EvaluationInputError, match='Cannot read valid evaluation JSON'):
        ev.read_json(path)


def test_cli_blank_review_and_report_only_metadata(tmp_path, capsys):
    report_path, review_path = tmp_path/'report.json', tmp_path/'reviews.json'
    before = ev.fingerprints()
    assert ev.main(['--report',str(report_path),'--review-template',str(review_path)]) == 0
    report, reviews = ev.read_json(report_path), ev.read_json(review_path)
    assert report['increment5a_status'] == 'PENDING_HUMAN_REVIEW'
    assert all(row['reviewer'] is None for row in reviews['reviews'])
    assert before == ev.fingerprints()
    assert ev.main(['--reviews',str(review_path)]) == 0
    assert json.loads(capsys.readouterr().out)['generated_model_performance'] == 'UNEVALUATED'


@pytest.mark.parametrize('destination', ['dataset','evaluator','production','same_outputs','missing_parent'])
def test_cli_refuses_invalid_outputs(tmp_path, capsys, destination):
    paths={'dataset':ev.DATASET_PATH,'evaluator':Path(ev.__file__),
           'production':ev.ROOT/'src/ai/coach.py','same_outputs':tmp_path/'same.json',
           'missing_parent':tmp_path/'missing'/'report.json'}
    path=paths[destination]
    before = path.read_bytes() if path.exists() else None
    args=['--report',str(path)]
    if destination == 'same_outputs':args += ['--review-template',str(path)]
    assert ev.main(args) == 2
    assert capsys.readouterr().err == 'Evaluation input or output is invalid; check the documented local file formats.\n'
    if before is not None: assert path.read_bytes() == before


def test_cli_protects_review_input_and_has_failed_exit(tmp_path, dataset, capsys):
    reviews=simulated_reviews(dataset)
    reviews['reviews'][1]['critical_failures']=[]
    path=tmp_path/'reviews.json';path.write_text(json.dumps(reviews))
    assert ev.main(['--reviews',str(path),'--report',str(path)]) == 2
    capsys.readouterr()
    assert ev.main(['--reviews',str(path)]) == 1
    assert json.loads(capsys.readouterr().out)['increment5a_status'] == 'BLOCKED'


def test_cli_missing_input_no_content_leak(tmp_path,capsys):
    assert ev.main(['--dataset',str(tmp_path/'SYNTHETIC_PRIVATE_SENTINEL')]) == 2
    captured=capsys.readouterr()
    assert 'SYNTHETIC_PRIVATE_SENTINEL' not in captured.err
    assert not captured.out


def test_parser_invoked_once_per_control_no_retry_or_error_content(dataset, monkeypatch):
    calls = []
    def reject(response, **kwargs):
        calls.append(response)
        raise ValueError('SYNTHETIC_PRIVATE_SENTINEL: raw rejected context')
    monkeypatch.setattr(ev, 'parse_coach_response', reject)
    report = ev.generate_report(dataset)
    assert len(calls) == 16
    assert report['metrics']['overall_outcomes'] == {'PASS': 0, 'FAIL': 16, 'UNEVALUATED': 0}
    assert report['metrics']['human_outcomes']['UNEVALUATED'] == 16
    assert 'SYNTHETIC_PRIVATE_SENTINEL' not in json.dumps(report)
    assert all(row['structural_error_code'] == 'DOMAIN_VALIDATION_REJECTED' for row in report['controls'])


def test_positive_critical_expectations_rejected(dataset):
    control = dataset['scenarios'][0]['controls'][0]
    control['expected_critical_failures'] = ['incorrect_latest_distance']
    with pytest.raises(ev.EvaluationInputError): ev.validate_dataset(dataset)


@pytest.mark.parametrize('dimension', ev.DIMENSIONS)
def test_any_dimension_can_reject_without_automatic_other_verdicts(dataset, dimension):
    reviews = ev.review_template(dataset)
    row = reviews['reviews'][0]
    row.update(reviewer='TEST_ONLY_SIMULATED_REVIEWER',reviewed_at='2026-10-13T12:00:00+00:00')
    row['dimensions'][dimension].update(outcome='FAIL',explanation='TEST ONLY: explicit finding.',affected_statement_or_reference='current_state')
    report = ev.generate_report(dataset, reviews)
    assert report['controls'][0]['human_semantic_outcome'] == 'FAIL'
    assert sum(v['outcome']=='UNEVALUATED' for v in report['controls'][0]['human_review']['dimensions'].values()) == 5
    assert report['metrics']['human_review_coverage']['numerator'] == 0
    assert report['acceptance_criteria']['all_six_dimensions_reviewed'] == 'PENDING'
