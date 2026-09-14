import functools
import uuid
from pathlib import Path
from typing import Callable, Optional, Union

from referee.config import get_provider_config, load_config
from referee.guardrails.input_validation import validate_input
from referee.guardrails.output_validation import validate_output
from referee.guardrails.scope_check import check_scope
from referee.observe.tracing import get_tracer

_INTRO_SEEN_FILE = Path(".referee/.seen_intro")

_INTRO_TEXT = """
Agent Referee is now watching this call. Here's what just happened, once, so you
know what to expect going forward.

This is observability, sometimes also called tracing: quietly recording what an
agent actually did, step by step, without changing its behavior at all. There
are traditionally 3 pillars to it:
  · Traces  — the shape of ONE request, step by step. What this library does.
  · Logs    — free-form text messages, one event at a time.
  · Metrics — numbers aggregated over MANY requests (average latency, etc).
This library focuses on traces, printed straight to your terminal by default,
or sent to a real backend like Langfuse Cloud if you configure one.

Concretely, on every call to your decorated function, in order:

  1. A "span" starts — a timed record of this one call, with a unique ID.
     Every guardrail check and your own agent call gets nested inside it,
     building a small tree that shows exactly what happened and how long
     each step took. This is standard OpenTelemetry, the same tracing
     format Google Cloud, AWS, and most observability tools speak.
  2. Your input guardrails run, before your agent code does.
  3. Your agent function runs.
  4. Your output guardrails run, before the result is returned.
  5. The span ends.

Full explanation: docs/how-it-works.md
(This message only prints once — state is tracked in .referee/.seen_intro)
"""


def _maybe_print_intro() -> None:
    """Print the one-time "what's a span" explanation, on the first real
    call only. State is a dotfile, not an in-memory flag, so a long-running
    agent process restarting doesn't show it again."""
    if _INTRO_SEEN_FILE.exists():
        return
    print(_INTRO_TEXT)
    _INTRO_SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _INTRO_SEEN_FILE.write_text("seen\n")


def protect(config: Union[str, dict] = "referee.yaml") -> Callable:
    """The library's main entry point: wraps a plain str -> str agent
    function with automatic tracing and guardrails.

    Usage:
        @referee.protect(config="referee.yaml")
        def my_agent(user_input: str) -> str:
            ...

    config may be a path to a referee.yaml file, or an already-loaded config
    dict (used by `referee demo` and by tests, since they have no file on disk).

    On every call, in order: start a trace span, run input guardrails
    (blocking here skips your function entirely), call your function, run
    output guardrails, end the span. The wrapped function also accepts an
    optional session_id keyword argument for per-user rate limiting and
    tool-call limits; without one, all calls in this process share a single
    generated session ID.

    Does NOT cover execution-layer (tool-call) guardrails — see
    referee/guardrails/execution_layer.py for why that's a manual, one-line
    call instead.
    """
    loaded_config = config if isinstance(config, dict) else load_config(config)
    provider_config = get_provider_config(loaded_config)
    tracer = get_tracer(loaded_config)
    process_session_id = str(uuid.uuid4())

    guardrails_config = loaded_config.get("guardrails", {})
    input_config = guardrails_config.get("input", {})
    scope_check_config = input_config.get("scope_check", {})

    def decorator(fn: Callable[[str], str]) -> Callable[[str], str]:
        @functools.wraps(fn)
        def wrapped(user_input: str, session_id: Optional[str] = None) -> str:
            _maybe_print_intro()
            active_session_id = session_id or process_session_id

            with tracer.start_as_current_span("agent_request") as root_span:
                root_span.set_attribute("session.id", active_session_id)

                with tracer.start_as_current_span("input_guardrail") as span:
                    guard_result = validate_input(user_input, active_session_id, guardrails_config)

                    if guard_result["allowed"] and scope_check_config.get("enabled"):
                        guard_result = check_scope(
                            user_input, scope_check_config.get("description", ""), provider_config
                        )

                    span.set_attribute("guardrail.allowed", guard_result["allowed"])
                    if not guard_result["allowed"]:
                        span.set_attribute("guardrail.block_reason", guard_result["reason"])
                        return f"I can't help with that. ({guard_result['reason']})"
                    elif guard_result["reason"]:
                        span.set_attribute("guardrail.note", guard_result["reason"])

                with tracer.start_as_current_span("agent_call"):
                    agent_response = fn(user_input)

                with tracer.start_as_current_span("output_guardrail") as span:
                    output_result = validate_output(
                        user_input, agent_response, guardrails_config, provider_config
                    )
                    span.set_attribute("guardrail.allowed", output_result["allowed"])
                    if not output_result["allowed"]:
                        span.set_attribute("guardrail.block_reason", output_result["reason"])
                        return f"I can't share that response. ({output_result['reason']})"

                return agent_response

        return wrapped

    return decorator
