import re
from typing import Any

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{10}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
}

INJECTION_PATTERNS = [
    "ignore your instructions",
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard your instructions",
    "disregard the above",
    "reveal your instructions",
    "reveal your system prompt",
    "print your system prompt",
    "you are now",
    "new instructions:",
]

_session_message_counts: dict[str, int] = {}


def check_pii(user_input: str) -> dict[str, Any]:
    """Regex-only PII check (email, phone, credit card). No API call.

    Returns:
        {"allowed": bool, "reason": str | None}
    """
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, user_input):
            return {
                "allowed": False,
                "reason": (
                    f"Blocked: message looks like it contains a {pii_type}. "
                    "This runs as a plain regex check, no AI call — it protects users from "
                    "accidentally pasting sensitive data into a chat log."
                ),
            }
    return {"allowed": True, "reason": None}


def check_injection(user_input: str) -> dict[str, Any]:
    """Regex match against known prompt-injection phrasing (INJECTION_PATTERNS).
    No API call. Returns {"allowed": bool, "reason": str | None}.
    """
    lower_input = user_input.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower_input:
            return {
                "allowed": False,
                "reason": (
                    f"Blocked: message matched a known prompt-injection pattern ('{pattern}'). "
                    "This is a fast, free regex check — real production systems layer this "
                    "with an LLM-based classifier for phrasing regex can't anticipate."
                ),
            }
    return {"allowed": True, "reason": None}


def check_rate_limit(session_id: str, max_messages_per_session: int) -> dict[str, Any]:
    """Count messages per session_id and block once max_messages_per_session
    is exceeded. State is an in-memory dict, per-process only — see the
    returned reason for why that's a real limitation in a multi-process
    deployment, not just a note.
    """
    count = _session_message_counts.get(session_id, 0) + 1
    _session_message_counts[session_id] = count

    if count > max_messages_per_session:
        return {
            "allowed": False,
            "reason": (
                f"Blocked: session '{session_id}' has sent {count} messages, over the "
                f"configured limit of {max_messages_per_session}. This is in-memory, per-process "
                "state — it resets on restart and isn't shared across multiple server processes. "
                "A production deployment behind a load balancer needs a shared store (e.g. Redis) "
                "keyed by session ID instead."
            ),
        }
    return {"allowed": True, "reason": None}


def reset_rate_limits() -> None:
    """Clear in-memory rate-limit state. Mainly for tests and for a long-running
    process that wants to start a fresh counting window."""
    _session_message_counts.clear()


def validate_input(user_input: str, session_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Run the configured input guardrails in order: rate limit, then PII,
    then injection. Stops and returns at the first block. config is the
    full guardrails.* section of referee.yaml. Does not run scope_check
    (see referee/guardrails/scope_check.py) since that needs an LLM call.

    Returns:
        {"allowed": bool, "reason": str | None}
    """
    input_config = config.get("input", {})

    if "rate_limit_per_session" in input_config:
        rate_result = check_rate_limit(session_id, input_config["rate_limit_per_session"])
        if not rate_result["allowed"]:
            return rate_result

    if input_config.get("pii_check", True):
        pii_result = check_pii(user_input)
        if not pii_result["allowed"]:
            return pii_result

    if input_config.get("injection_check", True):
        injection_result = check_injection(user_input)
        if not injection_result["allowed"]:
            return injection_result

    return {"allowed": True, "reason": None}
