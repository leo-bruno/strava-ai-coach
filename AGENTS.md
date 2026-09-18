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