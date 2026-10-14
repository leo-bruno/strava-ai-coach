"""Offline fixtures and TEST-ONLY simulated reviews; no model/human performance evidence."""

import copy
import json
from pathlib import Path
import socket

import pytest

from tests.llm.increment5a import evaluate as rubric
from tests.llm.increment5b import evaluate as ev
from tests.llm.increment5b import run


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(run, 'ARTIFACT_ROOT', tmp_path / 'artifacts')
    def forbidden(*args, **kwargs):
        raise AssertionError('Network or generation forbidden in offline evaluation.')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(run.coach, 'OpenAI', forbidden)
    monkeypatch.setattr(run.coach, 'generate_coach_response', forbidden)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_COACH_MODEL', raising=False)


@pytest.fixture
def directory():
    dataset, scenario, context = run.prepare('5A-01')
    config = run.configuration(dataset, 'TEST_ONLY_MODEL')
    path = run.ARTIFACT_ROOT / 'cohort'
    run.initialize(path, config, 8)
    return path


def capture(directory, sid, *, failure=None, interrupted=False, response=None, reserved_only=False):
    dataset, scenario, context = run.prepare(sid)
    manifest = run._read_sealed(directory / 'manifest.json')
    timestamp = '2026-10-14T12:00:00+00:00'
    reservation = run._artifact(manifest, sid, 'RESERVED_UNCERTAIN', timestamp=timestamp)
    run._write_new(directory / f'{sid}.attempt.json', reservation)
    if reserved_only:
        return
    if failure:
        artifact = run._artifact(manifest, sid, 'INTERRUPTED' if interrupted else 'FAILED', failure=failure, timestamp=timestamp)
    else:
        artifact = run._artifact(manifest, sid, 'SUCCESS', response=response if response is not None else scenario['controls'][0]['response'], timestamp=timestamp)
    run._write_new(directory / f'{sid}.result.json', artifact)


def full(directory):
    for sid in run.SCENARIO_IDS:
        capture(directory, sid)
    return ev.load_cohort(directory)


def simulated_reviews(cohort):
    """Explicit simulated test judgments only; never used as actual acceptance reviews."""
    reviews = ev.review_template(cohort)
    for row in reviews['reviews']:
        row.update(reviewer='TEST_ONLY_SIMULATED_REVIEWER', reviewed_at='2026-10-14T12:00:00+00:00')
        for dimension in row['dimensions'].values():
            dimension.update(outcome='PASS', explanation='TEST ONLY: independently supplied simulated assessment.')
    return ev.seal_reviews(cohort, reviews)


def set_fail(reviews, dimension='factual_correctness', sid='5A-01'):
    row = next(row for row in reviews['reviews'] if row['scenario_id'] == sid)
    row['dimensions'][dimension].update(outcome='FAIL', explanation='TEST ONLY: observed simulated defect.', affected_fields=['current_state.text'])
    return row


def test_valid_ingestion_no_auto_verdict_no_labels(directory):
    cohort = full(directory)
    template = ev.review_template(cohort)
    assert len(template['reviews']) == 8
    assert 'expected_semantic_outcome' not in json.dumps(template)
    report = ev.generate_report(cohort, template)
    assert report['framework_acceptance'] == 'PASS'
    assert report['structural_response_validity'] == 'PASS'
    assert report['study_completeness'] == 'INCOMPLETE'
    assert report['model_acceptance'] == 'UNEVALUATED'
    assert report['metrics']['semantic_pass'] == dict(numerator=0, denominator=8, rate=0)
    assert report['metrics']['fully_reviewed_responses'] == dict(numerator=0, denominator=8, rate=0)
    assert all(r['semantic_outcome'] == 'UNEVALUATED' for r in report['scenarios'])


def test_empty_cohort_accounts_for_all_eight(directory):
    report = ev.generate_report(ev.load_cohort(directory))
    assert len(report['scenarios']) == 8
    assert report['metrics']['reserved_attempts'] == 0
    assert report['metrics']['valid_responses']['denominator'] == 8
    assert report['metrics']['fully_reviewed_responses'] == dict(numerator=0, denominator=0, rate=None)
    assert report['metrics']['semantic_unevaluated']['numerator'] == 8
    assert report['metrics']['unassessable_scenarios'] == 8
    assert report['metrics']['missing_scenarios'] == 8
    assert report['model_acceptance'] == 'UNEVALUATED'


@pytest.mark.parametrize('failure', [*run.FAILURES.values(), 'UNEXPECTED_ERROR', 'INTERRUPTED'])
def test_failure_visible_unassessable_not_reviewed(directory, failure):
    capture(directory, '5A-01', failure=failure, interrupted=failure == 'INTERRUPTED')
    cohort = ev.load_cohort(directory)
    assert ev.review_template(cohort)['reviews'] == []
    report = ev.generate_report(cohort)
    row = report['scenarios'][0]
    assert row['unassessable_reason'] == failure
    assert row['semantic_outcome'] == 'UNEVALUATED'
    assert report['framework_acceptance'] == 'PASS'
    assert report['model_acceptance'] == 'FAIL'
    assert report['study_completeness'] == 'INCOMPLETE'
    assert report['metrics']['terminal_records'] == 1
    assert report['metrics']['completed_execution_attempts'] == (0 if failure == 'INTERRUPTED' else 1)


def test_crash_uncertainty_keeps_denominators(directory):
    capture(directory, '5A-01', reserved_only=True)
    report = ev.generate_report(ev.load_cohort(directory))
    assert report['metrics']['reserved_attempts'] == 1
    assert report['metrics']['terminal_records'] == 0
    assert report['scenarios'][0]['unassessable_reason'] == 'RESERVED_UNCERTAIN'
    assert report['metrics']['uncertain_reservations'] == 1
    assert report['model_acceptance'] == 'UNEVALUATED'


def test_partial_denominators_and_six_dimension_counts(directory):
    capture(directory, '5A-01')
    capture(directory, '5A-02', failure='PROVIDER_ERROR')
    cohort = ev.load_cohort(directory)
    report = ev.generate_report(cohort, simulated_reviews(cohort))
    assert report['metrics']['valid_responses'] == dict(numerator=1, denominator=8, rate=1/8)
    assert report['metrics']['fully_reviewed_responses'] == dict(numerator=1, denominator=1, rate=1)
    assert report['metrics']['semantic_pass'] == dict(numerator=1, denominator=8, rate=1/8)
    assert report['metrics']['semantic_unevaluated']['numerator'] == 7
    assert report['metrics']['totals_reconcile']
    assert all(counts == {'PASS':1, 'FAIL':0, 'UNEVALUATED':7} for counts in report['metrics']['per_dimension'].values())
    assert report['model_acceptance'] == 'FAIL'


def test_eight_of_eight_semantic_acceptance_test_only(directory):
    cohort = full(directory)
    report = ev.generate_report(cohort, simulated_reviews(cohort))
    assert report['framework_acceptance'] == 'PASS'
    assert report['study_completeness'] == 'COMPLETE'
    assert report['model_acceptance'] == 'PASS'
    assert report['metrics']['semantic_pass']['numerator'] == 8
    assert report['safety_critical_findings'] == 'NONE_OBSERVED'
    assert all(v['coverage'] == 'partial' and v['scenario_ids'] for v in report['quality_coverage'].values())


@pytest.mark.parametrize('dimension', rubric.DIMENSIONS)
def test_independent_dimension_failure_not_propagated(directory, dimension):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    set_fail(reviews, dimension)
    report = ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))
    assert report['framework_acceptance'] == 'PASS'
    assert report['study_completeness'] == 'COMPLETE'
    assert report['model_acceptance'] == 'FAIL'
    assert report['metrics']['semantic_fail']['numerator'] == 1
    assert sum(a['outcome']=='PASS' for a in report['scenarios'][0]['human_review']['dimensions'].values()) == 5


def test_uncertainty_adjudication_explicit(directory):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    row = reviews['reviews'][0]
    row['dimensions']['transparency'].update(outcome='UNEVALUATED', explanation='TEST ONLY: uncertain.')
    reviews = ev.seal_reviews(cohort, reviews)
    report = ev.generate_report(cohort, reviews)
    assert report['model_acceptance'] == 'UNEVALUATED'
    assert report['metrics']['fully_reviewed_responses']['numerator'] == 7
    row = reviews['reviews'][0]
    row['review_stage'] = 'adjudication'
    row['dimensions']['transparency'].update(outcome='PASS', explanation='TEST ONLY: explicitly adjudicated.')
    assert ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))['model_acceptance'] == 'PASS'


@pytest.mark.parametrize('kind', ['scenario_defined','additional_safety_critical'])
def test_critical_findings_preserve_exact_description_and_fields(directory, kind):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    row = set_fail(reviews, sid='5A-07')
    description = 'TEST ONLY: exact human finding ñ\nwith original spacing.  '
    fields = ['current_state.text','limitations[0].text','TK_EASY_RUNNING_PRIORITY@1.0.0']
    row['critical_findings'] = [dict(kind=kind, condition_id='medical_clearance' if kind=='scenario_defined' else 'additional-test-risk',
        description=description, affected_fields=fields, justification=None if kind=='scenario_defined' else 'TEST ONLY: explicit additional safety justification.')]
    report = ev.generate_report(cohort, ev.seal_reviews(cohort, reviews))
    assert report['model_acceptance'] == 'FAIL'
    assert report['critical_findings'][0]['description'] == description
    assert report['critical_findings'][0]['affected_fields'] == fields
    assert report['safety_critical_findings'] == 'OBSERVED'


@pytest.mark.parametrize('defect', ['missing_justification','unknown_condition','duplicate','no_fail','no_affected','wrong_kind'])
def test_invalid_critical_finding_rejected(directory, defect):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    row = set_fail(reviews)
    finding = dict(kind='scenario_defined',condition_id='incorrect_latest_distance',description='TEST ONLY: finding.',affected_fields=['current_state.text'],justification=None)
    row['critical_findings'] = [finding]
    if defect=='missing_justification':finding.update(kind='additional_safety_critical',condition_id='new')
    elif defect=='unknown_condition':finding['condition_id']='unknown'
    elif defect=='duplicate':row['critical_findings'] *= 2
    elif defect=='no_fail':row['dimensions']['factual_correctness']['outcome']='PASS'
    elif defect=='no_affected':finding['affected_fields']=[]
    else:finding['kind']='automatic'
    with pytest.raises((ev.ReviewInputError,rubric.EvaluationInputError)):
        ev.seal_reviews(cohort, reviews)


@pytest.mark.parametrize('field', ['cohort_id','cohort_manifest_sha256','dataset_version','rubric_version','dataset_sha256','rubric_sha256','evaluator_code_sha256'])
def test_stale_review_root_bindings_rejected(directory, field):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    reviews[field] = 'STALE'
    with pytest.raises(ev.ReviewInputError): ev.seal_reviews(cohort, reviews)


@pytest.mark.parametrize('field', ['response_sha256','execution_artifact_sha256','dataset_sha256','rubric_sha256'])
def test_stale_response_review_bindings_rejected(directory, field):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    reviews['reviews'][0][field] = 'STALE'
    with pytest.raises(ev.ReviewInputError): ev.seal_reviews(cohort, reviews)


def test_modified_review_file_detected_and_explicit_sealing_preserves_decisions(directory):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    reviews['reviews'][0]['dimensions']['transparency']['explanation'] = 'TEST ONLY: edited human note.'
    with pytest.raises(ev.ReviewInputError,match='MODIFIED_REVIEW_FILE'):
        ev.generate_report(cohort, reviews)
    sealed = ev.seal_reviews(cohort, reviews)
    assert sealed['reviews'] == reviews['reviews']
    assert ev.generate_report(cohort, sealed)['model_acceptance'] == 'PASS'


@pytest.mark.parametrize('defect', ['duplicate','unknown','missing_dimension','bad_outcome','blank_explanation','affected','no_reviewer','bad_time','naive_time','stage'])
def test_review_format_errors_rejected(directory, defect):
    cohort = full(directory)
    reviews = simulated_reviews(cohort)
    row = reviews['reviews'][0]
    if defect=='duplicate':reviews['reviews'].append(copy.deepcopy(row))
    elif defect=='unknown':row['scenario_id']='UNKNOWN'
    elif defect=='missing_dimension':row['dimensions'].pop('transparency')
    elif defect=='bad_outcome':row['dimensions']['transparency']['outcome']='YES'
    elif defect=='blank_explanation':row['dimensions']['transparency']['explanation']=''
    elif defect=='affected':row['dimensions']['transparency']['affected_fields']=['not_a_field']
    elif defect=='no_reviewer':row['reviewer']=None
    elif defect=='bad_time':row['reviewed_at']='yesterday'
    elif defect=='naive_time':row['reviewed_at']='2026-10-14T12:00:00'
    else:row['review_stage']='automatic'
    with pytest.raises((ev.ReviewInputError,rubric.EvaluationInputError)):ev.seal_reviews(cohort,reviews)


@pytest.mark.parametrize('field', ['dataset_version','rubric_version','dataset_sha256','scenario_id','response_sha256'])
def test_capture_binding_change_visible_as_integrity_failure(directory, field):
    capture(directory,'5A-01')
    path=directory/'5A-01.result.json'
    artifact=run._read_sealed(path)
    artifact[field]='WRONG'
    artifact=run._sealed({k:v for k,v in artifact.items() if k!='artifact_sha256'})
    path.write_bytes(run.canonical(artifact))
    report=ev.generate_report(ev.load_cohort(directory))
    assert report['framework_acceptance']=='FAIL'
    assert report['metrics']['unassessable_scenarios']==8
    assert report['scenarios'][0]['safe_error_code']=='ARTIFACT_INTEGRITY_ERROR'


def test_modified_artifact_untrusted_text_not_reported(directory):
    capture(directory,'5A-01')
    path=directory/'5A-01.result.json'
    artifact=json.loads(path.read_text())
    artifact['response']['current_state']['text']='PRIVATE_SENTINEL'
    path.write_text(json.dumps(artifact))
    report=ev.generate_report(ev.load_cohort(directory))
    assert report['framework_acceptance']=='FAIL'
    assert 'PRIVATE_SENTINEL' not in json.dumps(report)


def test_structural_revalidation_rejects_even_resealed_output(directory):
    dataset,scenario,context=run.prepare('5A-01')
    response=copy.deepcopy(scenario['controls'][0]['response'])
    response['current_state']['evidence_references']=['PRIVATE_INVALID_REFERENCE']
    capture(directory,'5A-01',response=response)
    cohort=ev.load_cohort(directory)
    report=ev.generate_report(cohort)
    assert report['framework_acceptance']=='PASS'
    assert report['structural_response_validity']=='FAIL'
    assert report['model_acceptance']=='FAIL'
    assert not ev.review_template(cohort)['reviews']
    assert 'PRIVATE_INVALID_REFERENCE' not in json.dumps(report)


def test_unassessable_cannot_receive_review(directory):
    capture(directory,'5A-01')
    cohort=ev.load_cohort(directory)
    reviews=simulated_reviews(cohort)
    path=directory/'5A-01.result.json'
    path.unlink()
    with pytest.raises(ev.ReviewInputError):ev.seal_reviews(ev.load_cohort(directory),reviews)


def test_model_status_gate_independent_of_human_pass(directory):
    dataset,scenario,context=run.prepare('5A-01')
    response=copy.deepcopy(scenario['controls'][0]['response'])
    response.update(status='insufficient_support',next_week_recommendation=None)
    capture(directory,'5A-01',response=response)
    cohort=ev.load_cohort(directory)
    report=ev.generate_report(cohort,simulated_reviews(cohort))
    assert report['scenarios'][0]['semantic_outcome']=='PASS'
    assert report['scenarios'][0]['permitted_status_check']=='FAIL'
    assert report['model_acceptance']=='FAIL'


@pytest.mark.parametrize('defect', ['orphan','partial_reservation','reservation_binding','bad_outcome','unsafe_diagnostic','invalid_failure','interruption_mismatch'])
def test_bad_execution_files_remain_visible(directory, defect):
    if defect=='orphan':
        (directory/'5A-01.result.json').write_text('{}')
    elif defect=='partial_reservation':
        (directory/'5A-01.attempt.json').write_text('{')
    else:
        capture(directory,'5A-01')
        path=directory/('5A-01.attempt.json' if defect=='reservation_binding' else '5A-01.result.json')
        artifact=run._read_sealed(path)
        if defect=='reservation_binding':artifact['scenario_id']='5A-02'
        elif defect=='bad_outcome':artifact['attempt_outcome']='WRONG'
        elif defect=='unsafe_diagnostic':artifact['safe_validation_diagnostic']='PRIVATE_SENTINEL'
        elif defect=='invalid_failure':artifact.update(attempt_outcome='FAILED',safe_failure_category='UNKNOWN',response=None)
        else:artifact.update(attempt_outcome='INTERRUPTED',safe_failure_category='PROVIDER_ERROR',response=None)
        path.write_bytes(run.canonical(run._sealed({k:v for k,v in artifact.items() if k!='artifact_sha256'})))
    report=ev.generate_report(ev.load_cohort(directory))
    assert len(report['scenarios'])==8
    assert report['framework_acceptance']=='FAIL'
    assert 'PRIVATE_SENTINEL' not in json.dumps(report)


def test_deterministic_report_without_response_bodies(directory):
    cohort=full(directory)
    reviews=simulated_reviews(cohort)
    before=run.canonical(ev.generate_report(cohort,reviews))
    after=run.canonical(ev.generate_report(ev.load_cohort(directory),reviews))
    assert before==after
    for row in cohort['rows']:
        assert row['response']['current_state']['text'].encode() not in before
    assert b'RunnerContext' in before  # only a fixed limitation, never the actual input
    assert b'SYNTHETIC_SECRET_5A08' not in before


def test_cli_template_review_seal_report_no_overwrite(directory,capsys):
    full(directory)
    template_path=directory/'template.json'
    report_path=directory/'initial-report.json'
    args=['--cohort-dir',str(directory)]
    assert ev.main(args+['--review-template',str(template_path),'--report',str(report_path)])==0
    assert run._read_sealed(report_path)['model_acceptance']=='UNEVALUATED'
    edited=simulated_reviews(ev.load_cohort(directory))
    edited_path=directory/'human-edited.json'
    edited_path.write_bytes(run.canonical(edited))
    sealed_path=directory/'reviews.json'
    final_path=directory/'reviewed-report.json'
    assert ev.main(args+['--seal-reviews',str(edited_path),'--review-output',str(sealed_path),'--report',str(final_path)])==0
    assert run._read_sealed(final_path)['model_acceptance']=='PASS'
    before=final_path.read_bytes()
    assert ev.main(args+['--reviews',str(sealed_path),'--report',str(final_path)])==2
    assert final_path.read_bytes()==before
    assert ev.main(args+['--reviews',str(sealed_path)])==0
    assert json.loads(capsys.readouterr().out)['model_acceptance']=='PASS'


@pytest.mark.parametrize('defect', ['missing_seal_output','collision','outside','bad_reviews'])
def test_cli_bad_input_safe_error(directory,tmp_path,capsys,defect):
    args=['--cohort-dir',str(directory)]
    if defect=='missing_seal_output':args+=['--seal-reviews',str(directory/'missing')]
    elif defect=='collision':args+=['--review-template',str(directory/'same'),'--report',str(directory/'same')]
    elif defect=='outside':args+=['--report',str(tmp_path/'outside.json')]
    else:
        path=directory/'bad.json';path.write_text('PRIVATE_SENTINEL')
        args+=['--reviews',str(path)]
    assert ev.main(args)==2
    assert 'PRIVATE_SENTINEL' not in capsys.readouterr().err


def test_cli_known_failure_exit_one(directory,capsys):
    capture(directory,'5A-01',failure='REFUSAL')
    assert ev.main(['--cohort-dir',str(directory)])==1
    assert json.loads(capsys.readouterr().out)['model_acceptance']=='FAIL'


def test_known_failure_dominates_inconclusive_dimensions(directory):
    cohort=full(directory)
    reviews=simulated_reviews(cohort)
    row=set_fail(reviews)
    row['dimensions']['transparency'].update(outcome='UNEVALUATED',explanation='TEST ONLY: uncertain disclosure.')
    report=ev.generate_report(cohort,ev.seal_reviews(cohort,reviews))
    assert report['model_acceptance']=='FAIL'
    assert report['study_completeness']=='INCOMPLETE'
    assert report['metrics']['fully_reviewed_responses']['numerator']==7


@pytest.mark.parametrize('defect', ['review_list','finding_list','duplicate_fields','missing_fail_fields','nontext_note','new_existing_id'])
def test_additional_review_contract_errors(directory,defect):
    cohort=full(directory)
    reviews=simulated_reviews(cohort)
    row=set_fail(reviews)
    if defect=='review_list':reviews['reviews']={}
    elif defect=='finding_list':row['critical_findings']={}
    elif defect=='duplicate_fields':row['dimensions']['factual_correctness']['affected_fields']*=2
    elif defect=='missing_fail_fields':row['dimensions']['factual_correctness']['affected_fields']=[]
    elif defect=='nontext_note':row['dimensions']['transparency']['explanation']=42
    else:row['critical_findings']=[dict(kind='additional_safety_critical',condition_id='incorrect_latest_distance',description='TEST ONLY: risk.',affected_fields=['current_state.text'],justification='TEST ONLY: justification.')]
    with pytest.raises((ev.ReviewInputError,rubric.EvaluationInputError)):ev.seal_reviews(cohort,reviews)


def test_over_budget_artifacts_prevent_acceptance(directory):
    cohort=full(directory)
    path=directory/'manifest.json'
    manifest=run._read_sealed(path)
    manifest['approved_budget']=7
    manifest=run._sealed({k:v for k,v in manifest.items() if k!='artifact_sha256'})
    path.write_bytes(run.canonical(manifest))
    cohort=ev.load_cohort(directory)
    assert not cohort['budget_integrity']
    assert ev.generate_report(cohort)['framework_acceptance']=='FAIL'
    with pytest.raises(ev.ReviewInputError):ev.review_template(cohort)


def test_manifest_configuration_drift_rejected(directory):
    path=directory/'manifest.json'
    manifest=run._read_sealed(path)
    manifest['configuration']['rubric_version']='STALE'
    path.write_bytes(run.canonical(run._sealed({k:v for k,v in manifest.items() if k!='artifact_sha256'})))
    with pytest.raises(run.ExecutionGuardError):ev.load_cohort(directory)


def test_success_without_response_rejected(directory):
    capture(directory,'5A-01')
    path=directory/'5A-01.result.json'
    artifact=run._read_sealed(path)
    artifact['response']=None
    path.write_bytes(run.canonical(run._sealed({k:v for k,v in artifact.items() if k!='artifact_sha256'})))
    assert ev.generate_report(ev.load_cohort(directory))['framework_acceptance']=='FAIL'


def test_missing_review_and_uncertain_note_require_human_identity(directory):
    cohort=full(directory)
    reviews=ev.review_template(cohort)
    row=reviews['reviews'][0]
    row['dimensions']['transparency']['explanation']='TEST ONLY: human uncertainty note.'
    with pytest.raises(rubric.EvaluationInputError):ev.seal_reviews(cohort,reviews)
    row.update(reviewer='TEST_ONLY_SIMULATED_REVIEWER',reviewed_at='2026-10-14T12:00:00+00:00')
    reviews=ev.seal_reviews(cohort,reviews)
    reviews['reviews']=reviews['reviews'][:1]
    report=ev.generate_report(cohort,ev.seal_reviews(cohort,reviews))
    assert report['metrics']['semantic_unevaluated']['numerator']==8
    assert report['model_acceptance']=='UNEVALUATED'


@pytest.mark.parametrize('content', ['null','[]'])
def test_nonobject_review_files_rejected_safely(directory,content,capsys):
    path=directory/'invalid-review.json';path.write_text(content)
    for args in (['--reviews',str(path)],['--seal-reviews',str(path),'--review-output',str(directory/'new.json')]):
        assert ev.main(['--cohort-dir',str(directory),*args])==2
    assert 'Traceback' not in capsys.readouterr().err


def test_module_cli_entry_is_offline_and_incomplete(directory,monkeypatch,capsys):
    import runpy
    import sys
    monkeypatch.delitem(sys.modules,'tests.llm.increment5b.evaluate')
    monkeypatch.setattr(sys,'argv',['evaluate','--cohort-dir',str(directory)])
    with pytest.raises(SystemExit) as result:
        runpy.run_module('tests.llm.increment5b.evaluate',run_name='__main__')
    assert result.value.code==0
    assert json.loads(capsys.readouterr().out)['model_acceptance']=='UNEVALUATED'
