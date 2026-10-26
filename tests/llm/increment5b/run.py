"""Increment 5B-01: one selected synthetic scenario, dry-run by default.

Only the existing production Coach can generate a response. No semantic judge.
"""

import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from uuid import uuid4

from src.ai import coach
from src.ai.coach_response import parse_coach_response, validate_coach_response
from src.ai.training_knowledge import load_training_knowledge
from src.models.coach_response import CoachResponse
from tests.llm.increment5a import evaluate as adaptation


ARTIFACT_ROOT = adaptation.ROOT / 'test-results' / 'increment5b'
SCENARIO_IDS = tuple(f'5A-{number:02d}' for number in range(1, 9))
FORMAT_VERSION = '5B-01-1.0.0'
PROVENANCE = 'synthetic_increment5a_inputs_generated_response'
FAILURES = {
    coach.CoachConfigurationError: 'CONFIGURATION_ERROR',
    coach.CoachProviderError: 'PROVIDER_ERROR',
    coach.CoachRefusalError: 'REFUSAL',
    coach.CoachMalformedOutputError: 'MALFORMED_OUTPUT',
    coach.CoachInvalidResponseError: 'DOMAIN_VALIDATION_FAILURE',
}


class ExecutionGuardError(ValueError):
    """Fixed local error codes; never include rejected content or exception text."""


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def sha(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def domain_json(value):
    return json.loads(json.dumps(asdict(value), default=coach._json_value,
                                 ensure_ascii=False, allow_nan=False))


def prepare(scenario_id: str):
    if scenario_id not in SCENARIO_IDS:
        raise ExecutionGuardError('SCENARIO_SELECTION_INVALID')
    dataset = adaptation.validate_dataset(adaptation.read_json(adaptation.DATASET_PATH))
    scenario = next(row for row in dataset['scenarios'] if row['id'] == scenario_id)
    return dataset, scenario, adaptation.build_context(scenario['input'])


def configuration(dataset, model: str):
    if not isinstance(model, str) or not model.strip() or model != model.strip():
        raise ExecutionGuardError('MODEL_CONFIGURATION_INVALID')
    fingerprints = adaptation.fingerprints()
    fingerprints['execution_code_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    knowledge = load_training_knowledge()
    bindings = {}
    for scenario in dataset['scenarios']:
        context = adaptation.build_context(scenario['input'])
        schema = adaptation.read_json(coach._SCHEMA_PATH)
        coach._constrain_reference_schema(schema, context, knowledge)
        bindings[scenario['id']] = {
            'scenario_input_sha256': sha(scenario['input']),
            'context_sha256': sha(domain_json(context)),
            'specialized_schema_sha256': sha(schema),
        }
    return {
        'dataset_version': dataset['dataset_version'], 'rubric_version': dataset['rubric_version'],
        'dataset_sha256': sha(dataset), 'model': model, 'provenance': PROVENANCE,
        'prompt_identifier': 'coach_v1', 'prompt_version': '1',
        'schema_identifier': 'coach_response_v1', 'schema_revision': fingerprints['transport_template_sha256'],
        'fingerprints': fingerprints, 'scenario_bindings': bindings,
    }


def _directory(path, *, create=False):
    """Constrain writes to the ignored root and reject symbolic path components."""
    raw = Path(os.path.abspath(path))
    root = Path(os.path.abspath(ARTIFACT_ROOT))
    if raw == root or not raw.is_relative_to(root):
        raise ExecutionGuardError('OUTPUT_DIRECTORY_INVALID')
    if any(part.is_symlink() for part in (raw, *raw.parents)):
        raise ExecutionGuardError('SYMLINK_OUTPUT_REJECTED')
    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        raw.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not raw.is_dir():
        raise ExecutionGuardError('COHORT_DIRECTORY_MISSING')
    if create:
        os.chmod(raw, 0o700)
    return raw


def _sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _lock(directory):
    # Keep the lock inode: unlinking it would allow concurrent locks on new inodes.
    fd = os.open(directory / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ExecutionGuardError('LOCK_FILE_INVALID')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ExecutionGuardError('COHORT_BUSY') from None
        yield
    finally:
        os.close(fd)


def _write_new(path, payload):
    """Exclusive, fsynced writes; a partial file is never silently overwritten."""
    content = canonical(payload) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    _sync_directory(path.parent)


def _sealed(payload):
    return {**payload, 'artifact_sha256': sha(payload)}


def _read_sealed(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise ExecutionGuardError('ARTIFACT_FILE_INVALID')
    value = adaptation.read_json(path)
    if not isinstance(value, dict) or 'artifact_sha256' not in value:
        raise ExecutionGuardError('ARTIFACT_INTEGRITY_INVALID')
    payload = {key: item for key, item in value.items() if key != 'artifact_sha256'}
    if value['artifact_sha256'] != sha(payload):
        raise ExecutionGuardError('ARTIFACT_INTEGRITY_INVALID')
    return value


def initialize(directory, config, budget=0):
    if type(budget) is not int or not 0 <= budget <= len(SCENARIO_IDS):
        raise ExecutionGuardError('BUDGET_INVALID')
    directory = _directory(directory, create=True)
    with _lock(directory):
        if any(path.name != '.lock' for path in directory.iterdir()):
            raise ExecutionGuardError('COHORT_ALREADY_EXISTS')
        manifest = _sealed({
            'artifact_format_version': FORMAT_VERSION, 'cohort_id': str(uuid4()),
            'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'planned_scenarios': list(SCENARIO_IDS), 'approved_budget': budget,
            'configuration': config,
        })
        _write_new(directory / 'manifest.json', manifest)
    return manifest


def _manifest(directory, config):
    manifest = _read_sealed(directory / 'manifest.json')
    expected_keys = {'artifact_format_version', 'cohort_id', 'created_at', 'planned_scenarios',
                     'approved_budget', 'configuration', 'artifact_sha256'}
    budget = manifest.get('approved_budget')
    if (set(manifest) != expected_keys or manifest['artifact_format_version'] != FORMAT_VERSION
        or not isinstance(manifest['cohort_id'], str) or not manifest['cohort_id']
        or manifest['planned_scenarios'] != list(SCENARIO_IDS)
        or type(budget) is not int or not 0 <= budget <= len(SCENARIO_IDS)):
        raise ExecutionGuardError('MANIFEST_INVALID')
    if manifest['configuration'] != config:
        raise ExecutionGuardError('FROZEN_CONFIGURATION_CHANGED')
    return manifest


def _artifact(manifest, scenario_id, outcome, *, response=None, failure=None, diagnostic=None, timestamp=None):
    config = manifest['configuration']
    return _sealed({
        'artifact_format_version': FORMAT_VERSION, 'cohort_id': manifest['cohort_id'],
        'scenario_id': scenario_id, 'provenance': PROVENANCE,
        'dataset_version': config['dataset_version'], 'rubric_version': config['rubric_version'],
        'configured_model': config['model'], 'provider_reported_model': None,
        'prompt_identifier': config['prompt_identifier'], 'prompt_version': config['prompt_version'],
        'schema_identifier': config['schema_identifier'], 'schema_revision': config['schema_revision'],
        'cohort_manifest_sha256': manifest['artifact_sha256'], 'dataset_sha256': config['dataset_sha256'],
        'fingerprints': config['fingerprints'], **config['scenario_bindings'][scenario_id],
        'execution_timestamp_utc': timestamp or datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'attempt_outcome': outcome,
        'structural_validation': 'PASS' if response is not None else ('FAIL' if failure in ('DOMAIN_VALIDATION_FAILURE', 'MALFORMED_OUTPUT') else 'NOT_EVALUATED'),
        'response': response, 'response_sha256': sha(response) if response is not None else None,
        'safe_failure_category': failure, 'safe_validation_diagnostic': diagnostic,
        'token_usage': None, 'cost': None,
        'unavailable_metadata_reason': 'Not exposed by the production Coach return contract.',
    })


def _attempts(directory, manifest):
    consumed = set()
    for scenario_id in SCENARIO_IDS:
        reservation = directory / f'{scenario_id}.attempt.json'
        result = directory / f'{scenario_id}.result.json'
        if result.exists() and not reservation.exists():
            raise ExecutionGuardError('ORPHAN_RESULT_INVALID')
        if reservation.exists() or reservation.is_symlink():
            consumed.add(scenario_id)
            reserved = _read_sealed(reservation)
            expected = _artifact(manifest, scenario_id, 'RESERVED_UNCERTAIN', timestamp=reserved.get('execution_timestamp_utc'))
            if reserved != expected:
                raise ExecutionGuardError('RESERVATION_INVALID')
            if result.exists() or result.is_symlink():
                completed = _read_sealed(result)
                outcome = completed.get('attempt_outcome')
                response = completed.get('response')
                failure = completed.get('safe_failure_category')
                diagnostic = completed.get('safe_validation_diagnostic')
                allowed_diagnostics = {f'{code}: {explanation}' for code, explanation in coach._VALIDATION_DIAGNOSTICS.items()}
                if diagnostic is not None and diagnostic not in allowed_diagnostics:
                    raise ExecutionGuardError('RESULT_INVALID')
                if outcome == 'INTERRUPTED' and failure != 'INTERRUPTED':
                    raise ExecutionGuardError('RESULT_INVALID')
                if outcome not in ('SUCCESS', 'FAILED', 'INTERRUPTED'):
                    raise ExecutionGuardError('RESULT_INVALID')
                if outcome == 'SUCCESS':
                    if response is None or failure is not None or diagnostic is not None:
                        raise ExecutionGuardError('RESULT_INVALID')
                    dataset, scenario, context = prepare(scenario_id)
                    parse_coach_response(response, context=context, knowledge=load_training_knowledge())
                elif response is not None or failure not in (*FAILURES.values(), 'UNEXPECTED_ERROR', 'INTERRUPTED'):
                    raise ExecutionGuardError('RESULT_INVALID')
                expected = _artifact(manifest, scenario_id, outcome, response=response, failure=failure,
                                     diagnostic=diagnostic, timestamp=reserved['execution_timestamp_utc'])
                if completed != expected:
                    raise ExecutionGuardError('RESULT_INVALID')
    if len(consumed) > manifest['approved_budget']:
        raise ExecutionGuardError('ATTEMPT_ACCOUNTING_INVALID')
    return consumed


def _summary(scenario_id, config, budget=0, consumed=(), initialized=False):
    remaining = budget - len(consumed)
    model_matches = os.environ.get('OPENAI_COACH_MODEL') == config['model']
    return {'mode': 'dry_run', 'scenario_id': scenario_id, 'configured_model': config['model'],
            'provenance': PROVENANCE, 'eligible_for_execution': initialized and remaining > 0 and scenario_id not in consumed and model_matches,
            'production_model_matches': model_matches, 'live_credentials_checked': False,
            'approved_budget': budget, 'remaining_permitted_attempts': remaining,
            'attempt_already_consumed': scenario_id in consumed, 'fingerprints_valid': True,
            'scenario_fingerprints': config['scenario_bindings'][scenario_id], 'api_calls': 0}


def dry_run(scenario_id, config, directory=None):
    if directory is None:
        return _summary(scenario_id, config)
    directory = _directory(directory)
    with _lock(directory):
        manifest = _manifest(directory, config)
        consumed = _attempts(directory, manifest)
        return _summary(scenario_id, config, manifest['approved_budget'], consumed, True)


def execute(scenario_id, context, config, directory, *, allow_real_api_call=False):
    if not allow_real_api_call:
        raise ExecutionGuardError('LIVE_OPT_IN_REQUIRED')
    if directory is None:
        raise ExecutionGuardError('LIVE_OUTPUT_DIRECTORY_REQUIRED')
    directory = _directory(directory)
    # One shared provider lock also excludes concurrent calls in different cohorts.
    with _lock(ARTIFACT_ROOT), _lock(directory):
        dataset = adaptation.validate_dataset(adaptation.read_json(adaptation.DATASET_PATH))
        if configuration(dataset, config['model']) != config:
            raise ExecutionGuardError('FROZEN_CONFIGURATION_CHANGED')
        manifest = _manifest(directory, config)
        consumed = _attempts(directory, manifest)
        if scenario_id not in SCENARIO_IDS:
            raise ExecutionGuardError('SCENARIO_SELECTION_INVALID')
        if scenario_id in consumed:
            raise ExecutionGuardError('SCENARIO_ATTEMPT_ALREADY_CONSUMED')
        if len(consumed) >= manifest['approved_budget']:
            raise ExecutionGuardError('APPROVED_BUDGET_EXHAUSTED')
        if os.environ.get('OPENAI_COACH_MODEL') != config['model']:
            raise ExecutionGuardError('PRODUCTION_MODEL_MISMATCH')
        if not os.environ.get('OPENAI_KEY', '').strip():
            raise ExecutionGuardError('LIVE_CREDENTIALS_MISSING')
        if sha(domain_json(context)) != config['scenario_bindings'][scenario_id]['context_sha256']:
            raise ExecutionGuardError('SCENARIO_CONTEXT_MISMATCH')
        reserved = _artifact(manifest, scenario_id, 'RESERVED_UNCERTAIN')
        _write_new(directory / f'{scenario_id}.attempt.json', reserved)
        response, failure, diagnostic, outcome = None, None, None, 'SUCCESS'
        try:
            validated = coach.generate_coach_response(context)
            if not isinstance(validated, CoachResponse):
                raise coach.CoachInvalidResponseError('Rejected execution return type.')
            try:
                validate_coach_response(validated, context=context, knowledge=load_training_knowledge())
            except ValueError as error:
                rejected = coach.CoachInvalidResponseError('Rejected execution return value.')
                rejected.diagnostic_code = coach._validation_diagnostic_code(error)
                raise rejected from None
            response = domain_json(validated)
            # Reject artifacts if resources changed during generation.
            dataset = adaptation.validate_dataset(adaptation.read_json(adaptation.DATASET_PATH))
            if configuration(dataset, config['model']) != config:
                raise ExecutionGuardError('FROZEN_CONFIGURATION_CHANGED')
        except (KeyboardInterrupt, SystemExit):
            response, failure, outcome = None, 'INTERRUPTED', 'INTERRUPTED'
        except Exception as error:
            response, outcome = None, 'FAILED'
            failure = next((code for kind, code in FAILURES.items() if isinstance(error, kind)), 'UNEXPECTED_ERROR')
            if isinstance(error, coach.CoachInvalidResponseError):
                diagnostic = error.validation_diagnostic
        artifact = _artifact(manifest, scenario_id, outcome, response=response, failure=failure,
                             diagnostic=diagnostic, timestamp=reserved['execution_timestamp_utc'])
        _write_new(directory / f'{scenario_id}.result.json', artifact)
        return artifact


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', required=True, choices=SCENARIO_IDS)
    parser.add_argument('--model', help='Configured model; otherwise OPENAI_COACH_MODEL. No model default.')
    parser.add_argument('--output-dir', type=Path, help='Cohort directory below test-results/increment5b/.')
    parser.add_argument('--initialize-cohort', action='store_true')
    parser.add_argument('--approve-budget', type=int, default=None, help='Frozen initialization budget 0–8; default zero.')
    parser.add_argument('--allow-real-api-call', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.initialize_cohort and args.allow_real_api_call:
            raise ExecutionGuardError('INITIALIZATION_CANNOT_EXECUTE')
        if args.approve_budget is not None and not args.initialize_cohort:
            raise ExecutionGuardError('BUDGET_APPROVAL_REQUIRES_INITIALIZATION')
        if args.initialize_cohort and args.output_dir is None:
            raise ExecutionGuardError('INITIALIZATION_OUTPUT_REQUIRED')
        dataset, scenario, context = prepare(args.scenario)
        config = configuration(dataset, args.model or os.environ.get('OPENAI_COACH_MODEL'))
        if args.initialize_cohort:
            initialize(args.output_dir, config, args.approve_budget if args.approve_budget is not None else 0)
        if args.allow_real_api_call:
            result = execute(args.scenario, context, config, args.output_dir, allow_real_api_call=True)
            print(json.dumps({'scenario_id': args.scenario, 'attempt_outcome': result['attempt_outcome'],
                              'structural_validation': result['structural_validation'],
                              'safe_failure_category': result['safe_failure_category']}))
            return 0 if result['attempt_outcome'] == 'SUCCESS' else 1
        print(json.dumps(dry_run(args.scenario, config, args.output_dir), indent=2))
        return 0
    except (ExecutionGuardError, adaptation.EvaluationInputError, coach.CoachError, OSError, ValueError, TypeError, KeyError):
        print('Preparation or execution guard failed; check local configuration and cohort integrity.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
