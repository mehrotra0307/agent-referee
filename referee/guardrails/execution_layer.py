"""Execution-layer guardrails: blocking a specific tool call before it runs.

This is the one guardrail @referee.protect() cannot wire in automatically.
The decorator only sees the boundary of your top-level function; it has no
visibility into your agent's own tool-calling loop. So check_tool_call()
below is meant to be called manually, with one line, right before your tool
actually executes. See the README's "one place you still write a little
code by hand" section.
"""

from typing import Any

_tool_call_counts: dict[tuple[str, str], int] = {}


def check_tool_call_limit(
    tool_name: str, session_id: str, max_calls_per_tool: dict[str, int]
) -> dict[str, Any]:
    """Block tool_name once it's been called max_calls_per_tool[tool_name]
    times in this session_id. Tools not present in max_calls_per_tool are
    unlimited. Returns {"allowed": bool, "reason": str | None}."""
    if tool_name not in max_calls_per_tool:
        return {"allowed": True, "reason": None}

    key = (session_id, tool_name)
    count = _tool_call_counts.get(key, 0) + 1
    _tool_call_counts[key] = count
    limit = max_calls_per_tool[tool_name]

    if count > limit:
        return {
            "allowed": False,
            "reason": f"Blocked: tool '{tool_name}' already called {limit} time(s) this session.",
        }
    return {"allowed": True, "reason": None}


def check_tool_args(tool_name: str, tool_args: dict[str, Any], allowed_values: dict[str, dict[str, list]]) -> dict[str, Any]:
    """Block tool_name if any argument named in allowed_values[tool_name]
    holds a value outside its allow-list. Tools not present in
    allowed_values are unchecked. Returns {"allowed": bool, "reason": str | None}."""
    rules = allowed_values.get(tool_name)
    if not rules:
        return {"allowed": True, "reason": None}

    for arg_name, allowed in rules.items():
        actual = tool_args.get(arg_name)
        if actual not in allowed:
            return {
                "allowed": False,
                "reason": (
                    f"Blocked: tool '{tool_name}' called with {arg_name}={actual!r}, "
                    f"which isn't one of the allowed values {allowed}."
                ),
            }
    return {"allowed": True, "reason": None}


def check_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    session_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Call this by hand, right before your tool executes. Checks the
    per-tool call limit, then the argument allow-list, both driven by
    config's execution.* section in referee.yaml.

    Returns:
        {"allowed": bool, "reason": str | None}
    """
    execution_config = config.get("execution", {})

    limit_result = check_tool_call_limit(
        tool_name, session_id, execution_config.get("max_calls_per_tool", {})
    )
    if not limit_result["allowed"]:
        return limit_result

    args_result = check_tool_args(
        tool_name, tool_args, execution_config.get("allowed_values", {})
    )
    if not args_result["allowed"]:
        return args_result

    return {"allowed": True, "reason": None}


def reset_tool_call_counts() -> None:
    """Clear in-memory tool-call counts. Mainly for tests."""
    _tool_call_counts.clear()
