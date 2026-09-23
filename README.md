# strava-ai-coach

## Tests and coverage

Install the project dependencies in an activated virtual environment:

```bash
python -m pip install -r requirements.txt
```

From the repository root, run the complete test suite with coverage:

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
