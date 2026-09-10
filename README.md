# Agent Referee

Plug any AI agent — however you built it, wherever you deployed it — into real evaluation
scoring, real guardrails, and real observability tracing. In minutes, not days.

100% free forever. No account. No signup. No API key is ever typed into this tool.

> **Status: early build, not yet released.** This README will grow into a full quickstart as
> each piece lands. Follow along in the commit history if you want to see it get built.

## The security promise, up front

Agent Referee will **never** ask you to paste an API key into a prompt, a CLI flow, or a config
file. The only place a key ever lives is your own local `.env` file, read the same way the
official Google / OpenAI / Anthropic SDKs already read it — `os.getenv(...)`. We never see it,
store it, or transmit it anywhere. A CLI tool asking you to paste a secret is indistinguishable
from a phishing pattern, so this isn't a convenience feature we might relax later — it's a hard
boundary the design does not allow crossing.

## What it does

Wrap your agent's entry point with one decorator, and you get:

- **Evaluation** — a golden-dataset test runner with 5 scoring methods (exact match, refusal
  detection, ROUGE text similarity, embedding similarity, LLM-as-judge), CI-ready (exits non-zero
  on critical failure).
- **Guardrails** — layered input/output/execution-time checks: PII detection, prompt-injection
  detection, rate limiting, topic-scope enforcement, toxicity and groundedness checks. Cheapest
  checks run first; only the checks that need one do make an LLM call.
- **Observability** — OpenTelemetry tracing wired in automatically, exportable to the console or
  any OTLP-compatible backend (e.g. Langfuse Cloud's free tier).

Works with plain Python + Gemini/OpenAI/Anthropic, CrewAI, LangGraph, or anything else that can
be called like a function — Agent Referee never imports or depends on any agent framework.

## Why this exists

Built by generalizing a hand-built, from-scratch reference implementation (evaluators,
guardrails, and OpenTelemetry tracing all written by hand, bugs and all) into a library anyone
can drop into their own agent — and, at every step, an explanation of *why* each check exists,
not just whether it passed.

## License

MIT — see [LICENSE](LICENSE).
