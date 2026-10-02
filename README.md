# strava-ai-coach

## Tests and coverage

Install the project dependencies in an activated virtual environment:

```bash
python -m pip install -r requirements.txt
```

From the repository root, run the complete test suite:

```bash
python -m pytest
```

To run it with coverage:

```bash
python -m pytest --cov=src
```

`pyproject.toml` enables statement and branch coverage and shows missing lines
and branch destinations in the terminal. All production Python files under
`src` are included, including unexecuted modules; colocated test files are
omitted. The reported coverage percentage combines statements and branches.

There is no minimum coverage threshold. HTML and XML reports are not generated
by default. To optionally inspect coverage in a browser, run:

```bash
python -m coverage html
```

Open `htmlcov/index.html` after generating it. Coverage data and generated
reports are ignored by Git.

## Allure reporting

Generate Allure results using the pytest adapter included in `requirements.txt`:

```bash
python -m pytest --alluredir=allure-results --clean-alluredir
```

The root `conftest.py` groups `*_unit_test.py` as **Unit** and
`*_integration_test.py` as **Integration**, retaining the module suites beneath
each level. Classification only runs when Allure results are requested; it does
not change pytest selection or execution. Unrecognized filenames produce a warning
instead of being assigned a level silently. There are currently no E2E tests;
an **E2E** group will be added when their filename/path convention is established.

Generating `allure-results/` does not require the Allure CLI. The CLI is a separate
tool needed only to generate or view the HTML report. On macOS, it can be installed
with `brew install allure`; see the [official installation instructions](https://allurereport.org/docs/v2/install-for-macos/).
Once the CLI is installed:

```bash
allure generate allure-results --clean -o allure-report
allure open allure-report
```

`--clean-alluredir` avoids mixing previous test runs. Both `allure-results/` and
`allure-report/` are already ignored by Git. Allure reports traditional tests;
LLM evaluation reporting remains separate.
