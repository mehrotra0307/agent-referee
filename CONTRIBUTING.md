# Contributing

Thanks for considering it. This project is meant to be readable and approachable, so
contributions of any size are welcome: a typo fix, a new example integration, a new guardrail
check, a doc improvement.

## Setup

```bash
git clone https://github.com/mehrotra0307/agent-referee.git
cd agent-referee
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

That installs the package in editable mode, plus pytest.

## Running the tests

```bash
pytest tests/ -v
```

All tests should pass with the base install alone. Tests that need an optional extra
(embedding, a specific provider SDK, streamlit) should skip cleanly if that extra isn't
installed, not fail.

## Before opening a pull request

- Run the test suite and make sure it passes.
- If you're changing behavior in `referee/`, add or update a test for it.
- If you're adding a new public function, give it a short docstring explaining what it does,
  what it needs, and what it returns. The project favors clear docstrings and clear naming over
  inline comments explaining what code does; a comment is worth adding only when it explains a
  non-obvious *why*, like a workaround for a specific bug or a deliberate tradeoff.
- Keep the core install light. If your change needs a new dependency, check whether it belongs
  in `pyproject.toml`'s core `dependencies` or in `optional-dependencies` as a new or existing
  extra, and default to the extra unless it's genuinely tiny and always needed.

## Reporting a bug or proposing an idea

Open a GitHub issue. For a bug, include what you ran, what you expected, and what actually
happened. For an idea, a sentence or two on the problem it solves is more useful than a full
design up front.
