# Increment 5B-01: preparation and guarded capture

This developer-only tool prepares one explicitly selected scenario from the unchanged eight-scenario Increment 5A dataset. It reuses 5A's documented transformation, production CoachContext construction, schema specialization, knowledge and `generate_coach_response(context)`. There is no second Coach, SDK client implementation, scheduler, retry, automatic scenario iteration or semantic judge. No new dependency is required.

## Safe preparation and dry-run

Run from the repository root in the existing environment:

```sh
.venv/bin/python -m tests.llm.increment5b.run \
  --scenario 5A-01 --model gpt-4.1-mini-2025-04-14
```

Without `--allow-real-api-call`, this command never invokes Coach generation or constructs an OpenAI client. No API key is needed. `--model` supplies the plan model; otherwise the tool requires `OPENAI_COACH_MODEL`. There is no model default and no automatic `.env` loading. Output includes the scenario, model, synthetic provenance, scenario fingerprints, eligibility and remaining attempts. Without an initialized cohort, budget and remaining attempts are zero and eligibility is false.

Eligibility reflects the cohort, attempt and model guards. Dry-run does not inspect credentials; live execution checks them separately. A configured plan model must match `OPENAI_COACH_MODEL` before execution. Diagnostics and normal CLI output never include response bodies, contexts, credentials or raw exception messages.

The adapter preserves fixed reference dates, timezone, goal, availability, RunnerContext, coverage and partial-week metadata. It places all supplied synthetic activity totals in Other and zeros in other categories, exactly as 5A documents. Missing observations stay missing, zeros stay recorded zeros, open weeks remain partial, and 8–11 km / 300-second values stay unchanged. Execution timestamps never replace scenario reference dates. Production provenance labels are retained; the artifact explicitly declares synthetic origin.

## Frozen cohort initialization

Initialization is a separate, non-provider action. It requires an explicit cohort directory below the existing ignored `test-results/increment5b/` root:

```sh
.venv/bin/python -m tests.llm.increment5b.run \
  --scenario 5A-01 --model gpt-4.1-mini-2025-04-14 \
  --output-dir test-results/increment5b/cohort-01 \
  --initialize-cohort
```

Default approved budget is **zero**. To initialize a separately authorized paid experiment, supply `--approve-budget N` (integer 0–8). The budget, model, eight planned scenario IDs and fingerprints are frozen. Budget approval is accepted only during initialization; initialization cannot be combined with a live flag. Existing cohorts are never reinitialized or overwritten. Dry-runs consume no attempts.

For an existing cohort, omit `--initialize-cohort` and inspect it using the same scenario/model/output-dir arguments. No cohort was created or real request made during implementation; tests use temporary directories and mocks.

## Live authorization requirements

A later explicitly authorized execution requires all of:

- One scenario ID, never `all` or automatic iteration.
- Existing cohort and explicit `--output-dir`.
- Positive approved budget with a remaining attempt.
- No prior reservation for the selected scenario, including failures.
- Matching frozen implementation, dataset, context, prompt, schema and knowledge fingerprints.
- Matching `OPENAI_COACH_MODEL` and nonblank `OPENAI_API_KEY` in the process environment.
- Explicit `--allow-real-api-call`.

This flag can incur provider cost. It was never used against a real provider during development. The function calls the unchanged production Coach once. Production retains `max_retries=0`, `store=False`, strict output specialization and existing parser/validator behavior. No environment or authorization header is persisted.

Initialization of another directory is a new cohort requiring fresh human budget approval, not a retry facility. The eight-attempt cap applies per cohort, not to independent manual tools or the whole OpenAI account. SHA-256 checks detect accidental content changes; they do not authenticate a malicious operator who rewrites local files and recomputes hashes.

## Files, accounting and durability

Each cohort contains:

- `manifest.json`: sealed immutable configuration, budget and cohort UUID.
- `.lock`: persistent lock inode; never unlink while processes may use it.
- `<scenario>.attempt.json`: immutable reservation, written and fsynced before generation.
- `<scenario>.result.json`: immutable terminal capture, created after generation.

Reservations count against the budget even if no result exists. A `RESERVED_UNCERTAIN` reservation alone means completion/dispatch cannot be established; it must not be repeated. The tool never replaces a failed result. Both files are created exclusively, flushed and fsynced, with parent-directory synchronization. If a write leaves a partial file, integrity checks block further execution rather than repair it or retry. A result-write failure leaves the reservation consumed.

A nonblocking POSIX `fcntl.flock` is held for the entire invocation and result write. A shared lock at the artifact root also blocks provider execution across different cohorts. Concurrent initialization, dry-run inspection or execution against the same cohort is blocked. Process death releases the lock but not the reservation. Symbolic output paths, linked artifact files and writes outside the ignored root are rejected. New cohort directories use 0700, files use 0600. This implementation targets local POSIX filesystems on macOS/Linux; Windows and network/distributed filesystems are not supported.

## Capture format and failure handling

Artifact version: `5B-01-1.0.0`. JSON is canonical UTF-8 with sorted keys, no NaN/Infinity and no normalization of statement text. Artifacts contain cohort/scenario IDs, synthetic provenance, dataset/rubric versions, configured model, prompt/schema identifiers, UTC execution timestamp, attempt outcome, structural validation, safe failure category, response hash and a hash of the artifact excluding its own hash field.

Configuration fingerprints include dataset content, scenario input, built CoachContext, production Python files, 5A adapter, this execution module, prompt, schema template, request-specialized schema and approved knowledge. Templates are never written. Configuration is checked before invocation and again after successful generation; drift prevents response capture. Existing result artifacts are hash-checked, rebound to their manifest and revalidated by the production parser before allowing another attempt.

Only a production-validated CoachResponse is captured. The wrapper defensively validates the typed return again, preserving dates, enums, reference arrays and statement text in the original domain structure. Invalid outputs, rejected bodies and raw SDK envelopes are never saved. Structural PASS does **not** imply semantic PASS.

Terminal outcomes are SUCCESS, FAILED or INTERRUPTED. Existing errors map to CONFIGURATION_ERROR, PROVIDER_ERROR, REFUSAL, MALFORMED_OUTPUT or DOMAIN_VALIDATION_FAILURE. Unknown errors use UNEXPECTED_ERROR. Validation diagnostics use only the production allowlist and fixed explanations. Interrupted execution records INTERRUPTED if it can write a terminal artifact; hard crashes leave RESERVED_UNCERTAIN. Neither outcome authorizes rerun. A locally missing key/model mismatch is blocked before reserving an attempt; a production error after reservation consumes it conservatively.

`token_usage`, `provider_reported_model` and `cost` are explicitly null because the production return contract exposes none of them. Null means unavailable, **not zero**. No request-count or monetary billing certainty is inferred from a failed or interrupted execution. `store=False` does not establish that a provider has no retention policy. Even structurally valid synthetic responses may contain unsafe or injected statements, so captures must be treated as untrusted text, not executed or interpreted as instructions.

CLI exit codes: 0 for successful preparation/dry-run or valid capture; 1 for a terminal failed/interrupted attempt; 2 for configuration, integrity, filesystem or guard failure. Consult reservation files when an error occurs after dispatch: exit 2 alone does not imply an unused attempt.

## Offline verification and deferred scope

```sh
.venv/bin/python -m pytest tests/llm/increment5b/run_unit_test.py \
  tests/llm/increment5a/evaluate_unit_test.py \
  --cov=tests.llm.increment5b.run --cov=tests.llm.increment5a.evaluate \
  --cov-report=term-missing
.venv/bin/python -m pytest --cov=src --cov=tests.llm.increment5a.evaluate \
  --cov=tests.llm.increment5b.run --cov-report=term-missing
```

All new tests prohibit network access and unmocked Coach generation. The integration check restores production orchestration only with a mocked SDK factory. No test sends a real OpenAI request. Tests verify all eight context equivalences, opt-in, credentials, budget, locks, interruption accounting, tampering, safe errors and response capture.

Increment 5B-02 human semantic review, generated-performance reports, real executions and model-quality acceptance are deferred. This tool does not read or alter 5A human verdicts, copy expected labels to generated responses, or mark semantic quality PASS. No new recommendations, pace thresholds, medical rules, retries, dependencies or production changes are introduced.

Verification on 14 October 2026: 70 new tests and 97 existing 5A tests pass together (167 focused); all 1,486 regression tests pass without warnings. Runner combined coverage: 96.59% (statements 97.66%, branches 93.75%); production remains 99.10%; production plus 5A/5B tooling is 98.67%. All 5B-01 acceptance criteria are verified offline. Increment 5B-01 is COMPLETE; no real provider call or live cohort was created. Generated-model performance remains unevaluated.
