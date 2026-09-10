# Agent Referee

[![CI](https://github.com/mehrotra0307/agent-referee/actions/workflows/ci.yml/badge.svg)](https://github.com/mehrotra0307/agent-referee/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

Plug any AI agent — however you built it, wherever you deployed it — into real evaluation
scoring, real guardrails, and real observability tracing. In minutes, not days.

100% free forever. No account. No signup. No API key is ever typed into this tool.

## The security promise, up front

Agent Referee will **never** ask you to paste an API key into a prompt, a CLI flow, or a config
file. The only place a key ever lives is your own local `.env` file, read the same way the
official Google / OpenAI / Anthropic SDKs already read it — `os.getenv(...)`. We never see it,
store it, or transmit it anywhere. A CLI tool asking you to paste a secret is indistinguishable
from a phishing pattern, so this isn't a convenience feature that might get relaxed later — it's
a hard boundary the design does not allow crossing.

## The 30-second version, before you install anything

```bash
pip install agent-referee
referee demo
```

No config file, no API key, nothing else installed. This wraps a tiny built-in mock agent and
shows you the entire pitch — a guardrail blocking bad input, a trace of every step, and an
evaluator scoring a real answer — before you've touched your own agent at all.

## The 10-minute quickstart, on your own agent

**1. Install the core package.**

```bash
pip install agent-referee
```

This install is intentionally small — no PyTorch, no heavy ML deps. Embedding-similarity
scoring and the local dashboard are opt-in extras (see [Optional extras](#optional-extras)
below) so this step takes seconds, not minutes.

**2. Wire it into your agent — one decorator.**

```python
import referee

@referee.protect(config="referee.yaml")
def my_agent(user_input: str) -> str:
    # your existing code, completely unchanged
    ...
```

That's the whole integration surface for guardrails and tracing. Internally, in order: a trace
span starts, your input guardrails run, your function runs, your output guardrails run, the span
ends — all automatic, no manual span-wrapping in your code.

**3. Scaffold your config.**

```bash
referee init
```

Answers three questions — your agent's entry point, a one-line description of what it's allowed
to talk about, and which LLM provider you'll use for the one or two checks that need an LLM call.
It never asks for a key. It writes `referee.yaml` and adds `.env` to your `.gitignore`.

**4. Add your key locally — never here.**

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

(Swap the variable name for `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` depending on what you chose
in step 3.) Agent Referee reads this with `os.getenv()`, exactly like the official SDKs do.

**5. Build your first golden dataset — fully offline.**

```bash
referee dataset new
```

An interactive wizard, zero API calls, zero key required. Walks through questions your agent
might get and what a correct answer must mention, and writes `golden_dataset.json` directly. See
[docs/your-first-dataset.md](docs/your-first-dataset.md) for a full worked example.

**6. Run it.**

```bash
referee eval run          # scores your agent against your golden dataset, CI-ready
referee guardrails test   # runs packaged adversarial attacks against your configured guardrails
referee dashboard         # local Streamlit UI over both reports, nothing hosted by us
```

## What it does

- **Evaluation** — a golden-dataset test runner with 5 scoring methods (exact match, refusal
  detection, ROUGE text similarity, embedding similarity, LLM-as-judge), CI-ready (exits non-zero
  on any critical-severity failure).
- **Guardrails** — layered input/output/execution-time checks: PII detection, prompt-injection
  detection, rate limiting, topic-scope enforcement, toxicity and groundedness checks. Cheapest
  checks run first; only the checks that genuinely need one make an LLM call.
- **Observability** — OpenTelemetry tracing wired in automatically, printed as readable
  one-line-per-span console output by default, or exportable to any OTLP-compatible backend
  (e.g. Langfuse Cloud's free tier).

Works with plain Python + Gemini/OpenAI/Anthropic, CrewAI, LangGraph, or anything else that can
be called like a function — see [examples/](examples/) for all four. Agent Referee never imports
or depends on any agent framework; it only ever wraps a plain `str -> str` callable.

## The one exception to "just a decorator"

Execution-layer guardrails (blocking a specific tool call before it runs — rate-limiting an
order tool, rejecting an invalid argument) can't live inside `@referee.protect()`. A decorator
around your top-level function can only see the boundary of that call, not what happens inside
your agent's own tool-calling loop. So this is the one place that needs a manual, one-line call,
right before your tool actually executes:

```python
from referee.guardrails.execution_layer import check_tool_call

result = check_tool_call(tool_name, tool_args, session_id, config)
if not result["allowed"]:
    return result["reason"]
# only now do you actually run the tool
```

Everything else — guardrails, tracing — is fully automatic.

## Optional extras

The core install is deliberately minimal. Add what you actually use:

```bash
pip install agent-referee[embedding]   # sentence-transformers, for embedding-similarity scoring
pip install agent-referee[dashboard]   # streamlit, for `referee dashboard`
pip install agent-referee[gemini]      # google-genai SDK
pip install agent-referee[openai]      # openai SDK
pip install agent-referee[anthropic]   # anthropic SDK
pip install agent-referee[all]         # everything above
```

Only the SDK for the provider you actually configured in `referee.yaml` is ever needed.

## Documentation

- [docs/how-it-works.md](docs/how-it-works.md) — the 3 pillars (evaluation, guardrails,
  observability), explained for someone who's never heard the words before.
- [docs/your-first-dataset.md](docs/your-first-dataset.md) — a full worked example of building a
  golden dataset with `referee dataset new`.

## Why this exists

Built by generalizing a hand-built, from-scratch reference implementation — evaluators,
guardrails, and OpenTelemetry tracing all written by hand, real bugs hit and fixed along the way
— into a library anyone can drop into their own agent. At every step, it explains *why* a check
passed or failed, not just whether it did.

## License

MIT — see [LICENSE](LICENSE).
