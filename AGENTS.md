Strava AI Coach — Development Guidelines

Project goal

Build an AI-powered training assistant that connects to Strava, retrieves running activities, analyzes training data, and allows the user to interact with the data through natural language.

The project is also a learning and portfolio project focused on:

* Python
* REST APIs
* OAuth 2.0
* LLMs
* Tool calling
* AI agents
* LLM evaluation
* Automated testing

Technology

The project should primarily use:

* Python
* Strava API
* OpenAI API
* pytest
* pandas when useful
* Streamlit for the initial UI
* Playwright for end-to-end browser testing
* Allure for test reporting
* GitHub Actions for CI

Prefer simple, well-established libraries over unnecessary dependencies.

Do not add a dependency unless it provides clear value.

Architecture

Keep responsibilities separated:

* src/strava/ — Strava API integration and authentication.
* src/analytics/ — Training data processing and calculations.
* src/ai/ — LLM integration, prompts, tools and agent logic.
* src/ui/ — User interface.
* src/main.py — Application entry point.
* tests/e2e/ — End-to-end browser tests.
* tests/llm/ — LLM evaluation tests.

Unit and integration tests should be colocated with the production code they test.

Example:

src/analytics/
├── training.py
├── training.unit.test.py
└── training.integration.test.py

Do not create global tests/unit/ or tests/integration/ directories.

End-to-end and LLM tests are exceptions and remain in their dedicated directories:

tests/
├── e2e/
└── llm/

Development principles

* Keep the code simple and readable.
* Prefer small functions with a single responsibility.
* Use type hints where they improve readability.
* Handle errors explicitly.
* Do not hardcode secrets, tokens or credentials.
* Use environment variables for sensitive configuration.
* Do not over-engineer early versions of the project.
* Do not modify unrelated code when implementing a feature.
* Prefer incremental changes over large rewrites.
* Follow existing project conventions before introducing new patterns.

Testing strategy

The project uses multiple testing levels:

Unit tests

Unit tests verify isolated pieces of logic without relying on external services.

Use mocks for external dependencies.

Unit tests should be colocated with the implementation:

src/analytics/
├── training.py
└── training.unit.test.py

Unit tests should be fast, deterministic and focused on one behavior.

Integration tests

Integration tests verify that multiple components work correctly together or that the application integrates correctly with external services.

Integration tests should also be colocated with the implementation:

src/strava/
├── client.py
└── client.integration.test.py

External services should be mocked when appropriate.

Tests requiring real external services should be explicitly identified and controlled.

End-to-end tests

E2E tests verify complete user journeys through the application.

Use Playwright for browser-based E2E testing.

Examples:

* Connecting a Strava account.
* Viewing the training dashboard.
* Asking the AI assistant a question.
* Viewing an activity.
* Navigating between application sections.

E2E tests belong under:

tests/e2e/

E2E tests should focus on critical user journeys rather than duplicating lower-level tests.

LLM evaluation

LLM evaluation is treated separately from traditional software testing.

LLM evaluations should verify aspects such as:

* Correctness
* Relevance
* Groundedness
* Hallucination
* Tool selection
* Tool arguments
* Response format
* Safety

LLM evaluations belong under:

tests/llm/

LLM evaluations should use representative datasets and should be reproducible whenever possible.

Test reporting

Use pytest as the main test runner.

Use Allure for reporting traditional automated tests, including:

* Unit tests
* Integration tests
* E2E tests

Test reports should clearly distinguish between:

* Unit tests
* Integration tests
* E2E tests

E2E reports should retain relevant artifacts when useful, including:

* Screenshots
* Videos
* Traces
* Logs

LLM evaluations should have a dedicated evaluation report rather than being treated as conventional pass/fail tests.

LLM reports should include relevant metrics such as:

* Correctness
* Relevance
* Groundedness
* Hallucination rate
* Tool-selection accuracy
* Tool-argument accuracy

When useful, evaluation results should be comparable between different:

* Models
* Prompts
* Agent versions
* Dataset versions

Testing principles

When adding non-trivial functionality:

1. Add or update the appropriate tests.
2. Run the relevant tests.
3. Run the complete test suite when appropriate.
4. Do not remove or weaken tests just to make the implementation pass.
5. Prefer deterministic tests.
6. Keep external dependencies isolated from unit tests.
7. Test important error and edge cases.
8. Avoid duplicating the same behavior across multiple testing levels unless the duplication provides meaningful coverage.

Working with AI coding tools

When implementing functionality:

* Understand the existing code before modifying it.
* Explain significant architectural decisions.
* Do not make assumptions about external APIs; verify their documented behavior.
* Prefer small, incremental changes.
* Do not rewrite unrelated code.
* When there are significant trade-offs, explain them before implementing the change.
* Do not introduce unnecessary abstractions.
* Ask for clarification when requirements are genuinely ambiguous rather than making risky assumptions.

The purpose of using AI coding tools is not only to generate code but also to help the developer understand the implementation.

Multi-agent development workflow

Development work may be coordinated through a multi-agent workflow with three distinct roles:

* Orchestrator
* Architect
* Developer

The roles must remain separate. An agent must not silently take over responsibilities assigned to another role.

Orchestrator

The Orchestrator coordinates the workflow but does not perform architecture, implementation, or code review itself.

Responsibilities:

* Receive the user's development request.
* Create and coordinate the Architect and Developer agents.
* Route specifications, implementation results, review findings, and corrections between them.
* Reuse the same Architect and Developer agents during a workflow so they retain their role-specific context.
* Stop and ask the user when a genuine human decision is required.
* Enforce the review loop and iteration limit.

The Orchestrator must not:

* Design the technical solution.
* Implement or modify production code or tests.
* Perform the final technical review itself.
* Resolve product or architectural ambiguity on behalf of the user.

Architect

The Architect acts as Product Owner, software architect, and independent implementation reviewer.

Before defining work, the Architect must:

* Read PROJECT.md.
* Read relevant repository documentation and instructions.
* Inspect the actual implementation and tests relevant to the requested work.
* Determine the real current project state rather than relying only on summaries or previous agent messages.

When deciding what to implement next, the Architect must use PROJECT.md together with the actual repository state.

The Architect is responsible for:

* Understanding the requested outcome.
* Identifying the next logical increment when the user asks to continue the project.
* Identifying relevant product, technical, and testing constraints.
* Evaluating meaningful alternatives when necessary.
* Defining the proposed design.
* Defining clear acceptance criteria.
* Defining the validation required from the Developer.
* Identifying decisions that require human input.

The Architect must not modify production code or tests.

After implementation, the same Architect should independently review the work.

The review must inspect the actual repository state, including as appropriate:

* Changed files.
* git diff.
* Implementation.
* Tests.
* Relevant validation results.
* PROJECT.md changes.

The Architect must not accept an implementation solely from the Developer's summary.

The final review result must be either ACCEPTED or REJECTED with concrete findings.

Developer

The Developer implements the specification produced by the Architect.

Before modifying code, the Developer must inspect the relevant repository files and understand the existing implementation and conventions.

The Developer is responsible for:

* Implementing only the agreed scope.
* Following the existing architecture and project conventions.
* Adding or updating appropriate tests.
* Running the validation requested by the Architect.
* Running additional relevant validation when necessary to ensure the change is safe.
* Reporting implementation results, tests, limitations, and blockers.
* Applying corrections requested during Architect review.

The Developer must not:

* Redefine product requirements.
* Make significant architectural decisions that contradict or extend the Architect's specification.
* Expand the scope with unrelated refactors or improvements.
* Weaken or remove tests merely to make the implementation pass.

If implementation reveals an important conflict, ambiguity, or architectural issue, the Developer must report it instead of making a unilateral decision.

Workflow

For normal development work:

1. The Orchestrator sends the user's request to the Architect.
2. The Architect inspects PROJECT.md and the actual repository.
3. The Architect determines the appropriate next step and designs the increment.
4. If an important decision requires human judgment, the workflow stops and asks the user.
5. Otherwise, the Architect produces:
   * Goal
   * Current context
   * Proposed design
   * Acceptance criteria
   * Constraints
   * Required validation
6. The Orchestrator sends the specification to the Developer.
7. The Developer implements and validates the change.
8. The Orchestrator returns the implementation result to the same Architect.
9. The Architect independently inspects the actual implementation and returns ACCEPTED or REJECTED.
10. If REJECTED, the Orchestrator sends the findings to the same Developer for correction.
11. The corrected implementation returns to the same Architect for another independent review.
12. The review loop may run a maximum of three times.
13. If the implementation is still rejected after three review iterations, stop and ask the user.
14. When ACCEPTED, ensure PROJECT.md is updated when required by the Project documentation rules.
15. When ACCEPTED, create a Git checkpoint: return control to the user, summarize the completed increment and validation, and provide a recommended commit message.
16. Do not begin another development increment until the user explicitly asks to continue.

Human decisions

Do not interrupt the user for routine implementation details that can be safely resolved from the specification, repository, existing conventions, or documented project decisions.

Stop and ask the user when a decision materially affects:

* Product behavior.
* Project scope.
* Significant architecture.
* Public contracts or compatibility.
* Evaluation semantics requiring human judgment.
* Risk that cannot be resolved from existing project evidence.
* A genuinely ambiguous requirement with multiple materially different valid outcomes.

When asking for a decision, explain the alternatives and provide the Architect's recommendation when possible.


Git checkpoints

The workflow must actively identify appropriate Git checkpoints, while all Git write operations remain exclusively under user control.

Before starting any new development increment, the Orchestrator must check git status.

If the working tree is not clean:

1. Inspect the diff and determine whether the changes belong to completed, accepted, incomplete, or unknown work.
2. If they belong to a completed and ACCEPTED increment, stop and recommend a Git checkpoint, including a suggested commit message.
3. If they are incomplete, rejected, mixed, or their status cannot be established with confidence, stop and explain the situation to the user.
4. Do not start a new increment until the user explicitly decides how to handle the existing changes.

A dirty working tree must never be silently carried into a new development increment.

If the repository contains uncommitted changes from a completed and ACCEPTED increment:

1. Stop before starting the next increment.
2. Tell the user that the previous increment appears ready to be committed.
3. Summarize what the completed increment contains.
4. Provide a concise recommended commit message following the repository's existing commit style.
5. Recommend that the user commit and push the changes before continuing.
6. Wait for the user to confirm before starting the next increment.

If uncommitted changes are present and their status cannot be determined safely, stop before starting a new increment and ask the user.

Never assume that existing uncommitted changes are part of the current development state or safe to carry into a new increment.

After completing an increment:

When the Developer has completed the implementation, required validation has passed, the Architect has returned ACCEPTED, and PROJECT.md has been updated when required:

1. Treat this state as a Git checkpoint.
2. Return control to the user before beginning another development increment.
3. Summarize the completed increment and validation status.
4. Provide a recommended commit message.
5. Recommend that the user commit and push the accepted increment.
6. Do not start another increment until the user explicitly asks to continue.

Agents must never execute git commit, git push, or other history-changing Git operations. The checkpoint is advisory and the user remains responsible for all Git writes.

Git history is controlled exclusively by the user.

Agents may use read-only Git commands needed to understand and review the work, including commands such as:

* git status
* git diff
* git log

Agents must NEVER execute:

* git commit
* git push
* git merge
* git rebase
* git reset --hard
* other destructive or history-changing Git operations

The user performs all commits and pushes.

Workflow completion

A development increment is ready to return to the user only when:

* The Developer has completed the implementation and required validation.
* The Architect has independently reviewed the actual repository changes.
* The Architect has returned ACCEPTED.
* PROJECT.md has been updated when required.
* No unresolved blocking issue remains.

Acceptance by the Architect does not authorize a Git commit or push. Those actions remain exclusively under user control.

Security

Never commit:

* Strava client secrets
* OAuth access tokens
* OAuth refresh tokens
* OpenAI API keys
* .env files containing secrets

Sensitive configuration must be stored outside the source code.

The .env file must be excluded from Git.

Git

All git commits and pushes are performed exclusively by the user.
AI agents must never execute git commit or git push.

Make focused commits with clear messages.

Avoid mixing unrelated changes in the same commit.

Do not commit generated environments such as .venv/.

Before committing:

* Run relevant tests.
* Verify that no secrets are staged.
* Keep the commit focused on one logical change.

Code quality

Before considering a feature complete:

* The code should be readable.
* Important behavior should be covered by appropriate tests.
* External API errors should be handled.
* Secrets should not be exposed.
* Existing functionality should continue to work.
* Tests should be deterministic where possible.
* The implementation should not contain unnecessary complexity.

When unsure between a simple solution and a complex one, prefer the simple solution unless there is a clear reason not to.

Project documentation

PROJECT.md is the source of truth for the product vision, current capabilities, development status, architectural/product decisions, known gaps, and roadmap.

Before implementing a new feature or making a significant architectural change:

* Read the relevant sections of PROJECT.md.
* Ensure the implementation is consistent with the documented product boundaries and current development strategy.
* Do not assume that roadmap items described in PROJECT.md are already implemented. Verify the actual code and tests.

After completing a meaningful functional increment:

* Update PROJECT.md if the change affects implemented capabilities, current development status, known gaps, product decisions, validation status, or the next development step.
* Keep PROJECT.md product-oriented. Do not turn it into low-level code documentation.
* Do not mark a capability as complete unless the implementation and tests support that status.
* Keep the Current Focus, roadmap, and Next Step sections consistent with the actual state of the repository.

Small refactors, formatting changes, test-only changes, and internal implementation changes that do not alter the documented product state do not require a PROJECT.md update.