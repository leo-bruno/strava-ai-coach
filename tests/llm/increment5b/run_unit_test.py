"""Offline verification only; network and unmocked production execution forbidden."""

from dataclasses import replace
import json
import os
from pathlib import Path
import socket
from unittest.mock import MagicMock, Mock

import pytest

from src.ai.coach_response import parse_coach_response
from src.ai.training_knowledge import load_training_knowledge
from tests.llm.increment5a import evaluate as adaptation
from tests.llm.increment5b import run


PRODUCTION_GENERATE = run.coach.generate_coach_response


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(run, 'ARTIFACT_ROOT', tmp_path / 'artifacts')
    monkeypatch.setenv('OPENAI_COACH_MODEL', 'offline-test-model')
    monkeypatch.setenv('OPENAI_KEY', 'TEST_KEY_MUST_NOT_LEAK')
    def forbidden(*args, **kwargs):
        raise AssertionError('External execution forbidden in tests.')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(run.coach, 'OpenAI', forbidden)
    monkeypatch.setattr(run.coach, 'generate_coach_response', forbidden)


@pytest.fixture
def prepared():
    dataset, scenario, context = run.prepare('5A-01')
    config = run.configuration(dataset, 'offline-test-model')
    return dataset, scenario, context, config


def cohort(prepared, budget=8):
    directory = run.ARTIFACT_ROOT / 'cohort'
    run.initialize(directory, prepared[3], budget)
    return directory


def valid_response(prepared):
    return parse_coach_response(prepared[1]['controls'][0]['response'], context=prepared[2], knowledge=load_training_knowledge())


def invoke(prepared, directory, monkeypatch, response=None, error=None):
    generate = Mock(return_value=response if response is not None else valid_response(prepared), side_effect=error)
    monkeypatch.setattr(run.coach, 'generate_coach_response', generate)
    result = run.execute('5A-01', prepared[2], prepared[3], directory, allow_real_api_call=True)
    generate.assert_called_once_with(prepared[2])
    return result


@pytest.mark.parametrize('scenario_id', run.SCENARIO_IDS)
def test_all_contexts_exactly_match_5a(scenario_id):
    dataset, scenario, context = run.prepare(scenario_id)
    assert context == adaptation.build_context(scenario['input'])
    assert context.runner_context.runner_context == scenario['input']['request']['runner_context']
    assert context.reference_datetime.isoformat() == scenario['input']['reference_datetime']
    assert context.athlete_timezone.key == scenario['input']['athlete_timezone']
    assert context.constraints.available_training_days_per_week == scenario['input']['request']['constraints']['available_training_days_per_week']
    assert context.source_metadata.coverage == scenario['input']['source_metadata']['coverage']
    for week in context.recent_weeks:
        assert all(count == 0 for kind,count in week.training_type_counts if kind.value != 'Other')
    if scenario_id == '5A-04':
        assert str(context.missing_recent_week_dates[0]) == '2026-09-14'
        assert context.open_week.known_partial
        assert context.recent_weeks[-1].known_partial
    if scenario_id == '5A-07': assert 'discomfort' in context.runner_context.runner_context
    if scenario_id == '5A-08': assert 'Ignore system rules' in context.runner_context.runner_context


def test_unknown_scenario_rejected():
    with pytest.raises(run.ExecutionGuardError): run.prepare('all')


def test_dry_run_no_key_no_client_no_attempt(prepared, monkeypatch, capsys):
    monkeypatch.delenv('OPENAI_KEY')
    assert run.main(['--scenario','5A-01']) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary['api_calls'] == 0
    assert summary['remaining_permitted_attempts'] == 0
    assert not summary['eligible_for_execution']
    assert not run.ARTIFACT_ROOT.exists()
    directory = cohort(prepared)
    assert run.main(['--scenario','5A-01','--output-dir',str(directory)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary['eligible_for_execution']
    assert summary['remaining_permitted_attempts'] == 8
    assert not list(directory.glob('*.attempt.json'))


@pytest.mark.parametrize('budget', [-1,9,True,1.5])
def test_budget_invalid(prepared,budget):
    with pytest.raises(run.ExecutionGuardError): cohort(prepared,budget)


def test_budget_zero_default_and_no_reinitialization(prepared):
    directory=run.ARTIFACT_ROOT/'cohort'
    manifest=run.initialize(directory,prepared[3])
    assert manifest['approved_budget']==0
    with pytest.raises(run.ExecutionGuardError,match='COHORT_ALREADY_EXISTS'):
        run.initialize(directory,prepared[3],8)
    with pytest.raises(run.ExecutionGuardError,match='APPROVED_BUDGET_EXHAUSTED'):
        run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)


def test_capture_exact_canonical_response_and_permissions(prepared,monkeypatch):
    directory=cohort(prepared)
    response=valid_response(prepared)
    result=invoke(prepared,directory,monkeypatch,response)
    assert result['response']==prepared[1]['controls'][0]['response']
    assert result['response_sha256']==run.sha(result['response'])
    assert result['structural_validation']=='PASS'
    assert result['attempt_outcome']=='SUCCESS'
    assert result['token_usage'] is result['cost'] is result['provider_reported_model'] is None
    assert result==run._read_sealed(directory/'5A-01.result.json')
    assert (directory/'5A-01.result.json').read_bytes()==run.canonical(result)+b'\n'
    assert directory.stat().st_mode & 0o777==0o700
    assert all(p.stat().st_mode & 0o777==0o600 for p in directory.iterdir())
    assert run.dry_run('5A-01',prepared[3],directory)['attempt_already_consumed']
    assert 'TEST_KEY_MUST_NOT_LEAK' not in ''.join(p.read_text() for p in directory.glob('*.json'))


def test_text_preserved_exactly(prepared,monkeypatch):
    response=valid_response(prepared)
    response=replace(response,current_state=replace(response.current_state,text='  Unchanged ñ text\nwith whitespace.  '))
    result=invoke(prepared,cohort(prepared),monkeypatch,response)
    assert result['response']['current_state']['text']==response.current_state.text


@pytest.mark.parametrize('error_type', list(run.FAILURES))
def test_safe_production_failures_once(prepared,monkeypatch,error_type):
    error=error_type('PRIVATE_RESPONSE_AND_KEY_SENTINEL')
    if isinstance(error,run.coach.CoachInvalidResponseError):error.diagnostic_code='untrusted\nKEY'
    directory=cohort(prepared)
    result=invoke(prepared,directory,monkeypatch,error=error)
    assert result['safe_failure_category']==run.FAILURES[error_type]
    assert result['response'] is None and result['response_sha256'] is None
    assert 'PRIVATE_RESPONSE_AND_KEY_SENTINEL' not in json.dumps(result)
    assert 'untrusted' not in json.dumps(result)
    with pytest.raises(run.ExecutionGuardError,match='SCENARIO_ATTEMPT_ALREADY_CONSUMED'):
        run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)


@pytest.mark.parametrize('error', [KeyboardInterrupt(),SystemExit(3),RuntimeError('SECRET')])
def test_interruptions_and_unknown_errors_consumed(prepared,monkeypatch,error):
    directory=cohort(prepared)
    result=invoke(prepared,directory,monkeypatch,error=error)
    assert result['response'] is None
    assert result['attempt_outcome']==('INTERRUPTED' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'FAILED')
    assert 'SECRET' not in json.dumps(result)
    assert run.dry_run('5A-01',prepared[3],directory)['attempt_already_consumed']


def test_crash_reservation_remains_consumed(prepared):
    directory=cohort(prepared)
    manifest=run._manifest(directory,prepared[3])
    reserved=run._artifact(manifest,'5A-01','RESERVED_UNCERTAIN')
    run._write_new(directory/'5A-01.attempt.json',reserved)
    assert run.dry_run('5A-01',prepared[3],directory)['remaining_permitted_attempts']==7
    with pytest.raises(run.ExecutionGuardError,match='SCENARIO_ATTEMPT_ALREADY_CONSUMED'):
        run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)


def test_failed_result_write_keeps_durable_reservation(prepared,monkeypatch):
    directory=cohort(prepared)
    write=run._write_new
    def fail_result(path,payload):
        if path.name.endswith('.result.json'):raise OSError('SECRET')
        write(path,payload)
    monkeypatch.setattr(run,'_write_new',fail_result)
    with pytest.raises(OSError):invoke(prepared,directory,monkeypatch)
    assert (directory/'5A-01.attempt.json').exists()
    assert run.dry_run('5A-01',prepared[3],directory)['attempt_already_consumed']


@pytest.mark.parametrize('invalid', ['wrong_type','unknown_reference'])
def test_invalid_return_never_captured(prepared,monkeypatch,invalid):
    response=valid_response(prepared)
    if invalid=='wrong_type':response={'raw':'PRIVATE_RESPONSE_SENTINEL'}
    else:response=replace(response,current_state=replace(response.current_state,evidence_references=('PRIVATE_RESPONSE_SENTINEL',)))
    result=invoke(prepared,cohort(prepared),monkeypatch,response)
    assert result['safe_failure_category']=='DOMAIN_VALIDATION_FAILURE'
    assert result['response'] is None
    assert 'PRIVATE_RESPONSE_SENTINEL' not in json.dumps(result)


def test_parallel_lock_blocks_live_and_dry_run(prepared):
    directory=cohort(prepared)
    with run._lock(directory):
        with pytest.raises(run.ExecutionGuardError,match='COHORT_BUSY'):run.dry_run('5A-01',prepared[3],directory)
        with pytest.raises(run.ExecutionGuardError,match='COHORT_BUSY'):
            run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)


def test_budget_exhaustion_across_scenarios(prepared,monkeypatch):
    directory=cohort(prepared,1)
    invoke(prepared,directory,monkeypatch)
    dataset,scenario,context=run.prepare('5A-02')
    with pytest.raises(run.ExecutionGuardError,match='APPROVED_BUDGET_EXHAUSTED'):
        run.execute('5A-02',context,prepared[3],directory,allow_real_api_call=True)


@pytest.mark.parametrize('defect', ['opt_in','directory','key','model','context'])
def test_live_guards_before_reservation(prepared,monkeypatch,defect):
    directory=cohort(prepared)
    context=prepared[2]
    if defect=='key':monkeypatch.delenv('OPENAI_KEY')
    if defect=='model':monkeypatch.setenv('OPENAI_COACH_MODEL','different')
    if defect=='context':context=replace(context,constraints=replace(context.constraints,available_training_days_per_week=0))
    with pytest.raises(run.ExecutionGuardError):
        run.execute('5A-01',context,prepared[3],None if defect=='directory' else directory,allow_real_api_call=defect!='opt_in')
    assert not list(directory.glob('*.attempt.json'))


@pytest.mark.parametrize('field', ['dataset_sha256','model','fingerprints','scenario_bindings'])
def test_frozen_configuration_change_blocked(prepared,field):
    directory=cohort(prepared)
    changed={**prepared[3],field:'changed'}
    with pytest.raises(run.ExecutionGuardError):run.dry_run('5A-01',changed,directory)
    with pytest.raises(run.ExecutionGuardError):
        run.execute('5A-01',prepared[2],changed,directory,allow_real_api_call=True)
    assert not list(directory.glob('*.attempt.json'))


def test_resource_changed_before_call_blocked(prepared,monkeypatch):
    directory=cohort(prepared)
    monkeypatch.setattr(run,'configuration',lambda *args:{'changed':True})
    with pytest.raises(run.ExecutionGuardError,match='FROZEN_CONFIGURATION_CHANGED'):
        run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)


def test_resource_changed_during_call_captures_no_response(prepared,monkeypatch):
    directory=cohort(prepared)
    config=run.configuration
    def generate(context):
        monkeypatch.setattr(run,'configuration',lambda *args:{'changed':True})
        return valid_response(prepared)
    monkeypatch.setattr(run.coach,'generate_coach_response',generate)
    result=run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)
    assert result['response'] is None and result['attempt_outcome']=='FAILED'
    monkeypatch.setattr(run,'configuration',config)
    assert run.dry_run('5A-01',prepared[3],directory)['attempt_already_consumed']


def test_artifacts_not_overwritten_and_corruption_blocks(prepared,monkeypatch):
    directory=cohort(prepared)
    invoke(prepared,directory,monkeypatch)
    path=directory/'5A-01.result.json'
    before=path.read_bytes()
    with pytest.raises(FileExistsError):run._write_new(path,{'overwrite':True})
    assert path.read_bytes()==before
    result=json.loads(before);result['response']['current_state']['text']='tampered'
    path.write_text(json.dumps(result))
    with pytest.raises(run.ExecutionGuardError,match='ARTIFACT_INTEGRITY_INVALID'):
        run.dry_run('5A-02',prepared[3],directory)


@pytest.mark.parametrize('defect', ['orphan','partial','manifest','symlink'])
def test_bad_local_artifact_blocks(prepared,defect):
    directory=cohort(prepared)
    if defect=='orphan':(directory/'5A-01.result.json').write_text('{}')
    elif defect=='partial':(directory/'5A-01.attempt.json').write_text('{')
    elif defect=='manifest':(directory/'manifest.json').write_text('{}')
    else:(directory/'5A-01.attempt.json').symlink_to(directory/'manifest.json')
    with pytest.raises((run.ExecutionGuardError,adaptation.EvaluationInputError)):
        run.dry_run('5A-01',prepared[3],directory)


def test_output_boundary_and_symlink(prepared,tmp_path):
    with pytest.raises(run.ExecutionGuardError):run.initialize(tmp_path/'outside',prepared[3])
    with pytest.raises(run.ExecutionGuardError):run.initialize(run.ARTIFACT_ROOT,prepared[3])
    run.ARTIFACT_ROOT.mkdir()
    (run.ARTIFACT_ROOT/'linked').symlink_to(tmp_path)
    with pytest.raises(run.ExecutionGuardError):run.initialize(run.ARTIFACT_ROOT/'linked'/'cohort',prepared[3])


@pytest.mark.parametrize('args', [[], ['--scenario','all'], ['--scenario','5A-01','--initialize-cohort'],
    ['--scenario','5A-01','--approve-budget','8'],
    ['--scenario','5A-01','--initialize-cohort','--allow-real-api-call'],
    ['--scenario','5A-01','--allow-real-api-call']])
def test_cli_invalid_args_no_execution(args,capsys):
    try:result=run.main(args)
    except SystemExit as error:result=error.code
    assert result==2
    assert 'TEST_KEY_MUST_NOT_LEAK' not in capsys.readouterr().err


def test_cli_initialize_and_mocked_live(prepared,monkeypatch,capsys):
    directory=run.ARTIFACT_ROOT/'cli'
    args=['--scenario','5A-01','--output-dir',str(directory)]
    assert run.main(args+['--initialize-cohort','--approve-budget','1'])==0
    assert json.loads(capsys.readouterr().out)['remaining_permitted_attempts']==1
    generate=Mock(return_value=valid_response(prepared))
    monkeypatch.setattr(run.coach,'generate_coach_response',generate)
    assert run.main(args+['--allow-real-api-call'])==0
    assert json.loads(capsys.readouterr().out)['attempt_outcome']=='SUCCESS'
    assert run.main(args+['--allow-real-api-call'])==2
    generate.assert_called_once()


def test_cli_missing_model_and_failed_execution(prepared,monkeypatch,capsys):
    monkeypatch.delenv('OPENAI_COACH_MODEL')
    assert run.main(['--scenario','5A-01'])==2
    monkeypatch.setenv('OPENAI_COACH_MODEL','offline-test-model')
    directory=cohort(prepared)
    monkeypatch.setattr(run.coach,'generate_coach_response',Mock(side_effect=run.coach.CoachProviderError('PRIVATE_SENTINEL')))
    assert run.main(['--scenario','5A-01','--output-dir',str(directory),'--allow-real-api-call'])==1
    assert 'PRIVATE_SENTINEL' not in capsys.readouterr().out


def test_eight_selected_attempts_and_single_provider_call_each(prepared,monkeypatch):
    directory=cohort(prepared)
    generate=Mock()
    monkeypatch.setattr(run.coach,'generate_coach_response',generate)
    for scenario_id in run.SCENARIO_IDS:
        dataset,scenario,context=run.prepare(scenario_id)
        generate.return_value=parse_coach_response(scenario['controls'][0]['response'],context=context,knowledge=load_training_knowledge())
        result=run.execute(scenario_id,context,prepared[3],directory,allow_real_api_call=True)
        assert result['attempt_outcome']=='SUCCESS'
    assert generate.call_count==8
    assert len(list(directory.glob('*.attempt.json')))==8
    assert run.dry_run('5A-08',prepared[3],directory)['remaining_permitted_attempts']==0


def test_production_pipeline_with_mocked_sdk_preserves_options(prepared,monkeypatch):
    from types import SimpleNamespace
    from src.ai import coach
    directory=cohort(prepared)
    # Restore the real orchestration, but replace the SDK factory with a mock.
    production=coach
    monkeypatch.setattr(production,'generate_coach_response',PRODUCTION_GENERATE)
    factory=MagicMock()
    create=factory.return_value.__enter__.return_value.chat.completions.create
    create.return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(refusal=None,content=json.dumps(prepared[1]['controls'][0]['response'])))])
    monkeypatch.setattr(production,'OpenAI',factory)
    result=run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)
    assert result['attempt_outcome']=='SUCCESS'
    factory.assert_called_once_with(api_key='TEST_KEY_MUST_NOT_LEAK',max_retries=0)
    create.assert_called_once()
    assert create.call_args.kwargs['store'] is False
    assert create.call_args.kwargs['response_format']['json_schema']['strict'] is True


@pytest.mark.parametrize('defect', ['schema_version','plan','budget','reservation','result_status','result_diagnostic','result_failure','result_response','accounting'])
def test_resealed_inconsistent_artifacts_rejected(prepared,monkeypatch,defect):
    directory=cohort(prepared)
    invoke(prepared,directory,monkeypatch)
    name='manifest.json' if defect in ('schema_version','plan','budget','accounting') else ('5A-01.attempt.json' if defect=='reservation' else '5A-01.result.json')
    path=directory/name
    payload=run._read_sealed(path)
    payload.pop('artifact_sha256')
    if defect=='schema_version':payload['artifact_format_version']='wrong'
    elif defect=='plan':payload['planned_scenarios']=[]
    elif defect=='budget':payload['approved_budget']=True
    elif defect=='accounting':payload['approved_budget']=0
    elif defect=='reservation':payload['attempt_outcome']='SUCCESS'
    elif defect=='result_status':payload['attempt_outcome']='wrong'
    elif defect=='result_diagnostic':payload['safe_validation_diagnostic']='PRIVATE_ERROR'
    elif defect=='result_failure':payload.update(attempt_outcome='INTERRUPTED',safe_failure_category='PROVIDER_ERROR',response=None,response_sha256=None)
    else:payload['response']=None
    path.write_bytes(run.canonical(run._sealed(payload)))
    with pytest.raises(run.ExecutionGuardError):run.dry_run('5A-02',prepared[3],directory)


def test_partial_reservation_write_cannot_be_retried(prepared,monkeypatch):
    directory=cohort(prepared)
    def partial(path,payload):
        path.write_text('{')
        raise OSError('disk failure')
    monkeypatch.setattr(run,'_write_new',partial)
    with pytest.raises(OSError):invoke(prepared,directory,monkeypatch)
    with pytest.raises(adaptation.EvaluationInputError):
        run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)


def test_missing_cohort_and_lock_symlink_blocked(prepared):
    with pytest.raises(run.ExecutionGuardError):run.dry_run('5A-01',prepared[3],run.ARTIFACT_ROOT/'missing')
    directory=cohort(prepared)
    (directory/'.lock').unlink()
    (directory/'.lock').symlink_to(directory/'manifest.json')
    with pytest.raises(OSError):run.dry_run('5A-01',prepared[3],directory)


def test_shared_provider_lock_blocks_other_cohort(prepared):
    first=cohort(prepared)
    second=run.ARTIFACT_ROOT/'second'
    run.initialize(second,prepared[3],8)
    with run._lock(run.ARTIFACT_ROOT):
        for directory in (first,second):
            with pytest.raises(run.ExecutionGuardError,match='COHORT_BUSY'):
                run.execute('5A-01',prepared[2],prepared[3],directory,allow_real_api_call=True)
            assert not list(directory.glob('*.attempt.json'))
