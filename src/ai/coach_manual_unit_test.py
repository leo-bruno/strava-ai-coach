"""Developer command opt-in, rendering and safe failure; no real API calls."""

from unittest.mock import patch

import pytest

from src.ai import coach_manual
from src.ai.coach import CoachProviderError, CoachInvalidResponseError
from src.ai.coach_response import parse_coach_response
from src.ai.coach_response_fixtures_test import context_fixture, response_fixture
from src.ai.training_knowledge import load_training_knowledge


def test_opt_in_required(capsys):
    with patch.object(coach_manual, 'generate_coach_response') as generate:
        with pytest.raises(SystemExit) as error:
            coach_manual.main([])
    assert error.value.code == 2
    generate.assert_not_called()
    assert '--allow-real-api-call' in capsys.readouterr().err


def test_renders_validated_response(capsys):
    context = context_fixture()
    response = parse_coach_response(response_fixture(), context=context, knowledge=load_training_knowledge())
    with patch.object(coach_manual, 'generate_coach_response', return_value=response) as generate:
        assert coach_manual.main(['--allow-real-api-call']) == 0
    generate.assert_called_once_with(context)
    output = capsys.readouterr().out
    assert 'Status: guidance_available' in output
    assert response.next_week_recommendation.training_priorities[0].text in output


@pytest.mark.parametrize('error_class', [CoachProviderError, CoachInvalidResponseError])
def test_clear_error_and_no_fallback(capsys, error_class):
    with patch.object(coach_manual, 'generate_coach_response', side_effect=error_class('Safe error')) as generate:
        assert coach_manual.main(['--allow-real-api-call']) == 1
    generate.assert_called_once()
    output = capsys.readouterr()
    assert output.out == ''
    assert error_class.__name__ in output.err


def test_module_entry_point_requires_opt_in(monkeypatch, capsys):
    import runpy
    import sys
    monkeypatch.setattr('sys.argv', ['coach_manual'])
    monkeypatch.delitem(sys.modules, 'src.ai.coach_manual')
    with patch('src.ai.coach.generate_coach_response') as generate:
        with pytest.raises(SystemExit) as error:
            runpy.run_module('src.ai.coach_manual', run_name='__main__')
    assert error.value.code == 2
    generate.assert_not_called()
    assert '--allow-real-api-call' in capsys.readouterr().err


def test_diagnostic_flag_alone_cannot_authorize_api(capsys):
    with patch.object(coach_manual, 'generate_coach_response') as generate:
        with pytest.raises(SystemExit) as error:
            coach_manual.main(['--diagnose-validation'])
    assert error.value.code == 2
    generate.assert_not_called()
    assert '--allow-real-api-call' in capsys.readouterr().err


@pytest.mark.parametrize('code', ['UNKNOWN_VALIDATION_FAILURE', 'UNKNOWN_EVIDENCE_REFERENCE', 'injected\nsecret'])
def test_diagnostic_cli_uses_only_allowlisted_output(code, capsys):
    error = CoachInvalidResponseError('raw-error-sentinel')
    error.diagnostic_code = code
    with patch.object(coach_manual, 'generate_coach_response', side_effect=error) as generate:
        assert coach_manual.main(['--allow-real-api-call', '--diagnose-validation']) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert output.err == error.validation_diagnostic + '\n'
    assert 'raw-error-sentinel' not in output.err
    assert 'injected' not in output.err
    assert 'secret' not in output.err
    generate.assert_called_once()


def test_external_error_construction_preserves_compatibility():
    error = CoachInvalidResponseError('existing caller message')
    assert error.args == ('existing caller message',)
    assert str(error) == 'existing caller message'
    assert error.diagnostic_code == 'UNKNOWN_VALIDATION_FAILURE'


def test_diagnostic_flag_keeps_success_renderer_behavior(capsys):
    context = context_fixture()
    response = parse_coach_response(response_fixture(), context=context, knowledge=load_training_knowledge())
    with patch.object(coach_manual, 'generate_coach_response', return_value=response):
        assert coach_manual.main(['--allow-real-api-call', '--diagnose-validation']) == 0
    output = capsys.readouterr()
    assert output.err == ''
    assert 'Status: guidance_available' in output.out


def test_diagnostic_flag_preserves_provider_error_behavior(capsys):
    with patch.object(coach_manual, 'generate_coach_response', side_effect=CoachProviderError('Safe provider failure')):
        assert coach_manual.main(['--allow-real-api-call', '--diagnose-validation']) == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert output.err == 'CoachProviderError: Safe provider failure\n'
