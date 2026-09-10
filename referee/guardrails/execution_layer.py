from typing import Any

_tool_call_counts: dict[tuple[str, str], int] = {}


def check_tool_call_limit(
    tool_name: str, session_id: str, max_calls_per_tool: dict[str, int]
) -> dict[str, Any]:
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
    _tool_call_counts.clear()
