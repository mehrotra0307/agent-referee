from typing import Any

from referee.providers import call_llm

_SCOPE_PROMPT_TEMPLATE = """You are a topic-scope classifier for an AI agent.

The agent's allowed scope: {description}

Message to classify: {message}

Answer with EXACTLY one word: YES if the message is within the agent's allowed scope, \
NO if it is clearly outside that scope.

Example answer: "YES" or "NO\""""


def check_scope(user_input: str, description: str, provider_config: dict[str, Any]) -> dict[str, Any]:
    prompt = _SCOPE_PROMPT_TEMPLATE.format(description=description, message=user_input)

    try:
        raw_text = call_llm(prompt, provider_config)
    except Exception as exc:
        return {
            "allowed": True,
            "reason": f"Scope check call failed, failing open: {exc}",
        }

    answer = raw_text.strip().upper()

    if answer.startswith("NO"):
        return {
            "allowed": False,
            "reason": (
                f"Blocked: message looks off-topic for this agent (scope: '{description}'). "
                "This is the one guardrail check that makes a real LLM call — everything "
                "upstream of it (PII, injection, rate limit) is free and local, so an "
                "off-topic-but-otherwise-safe message is the only kind that reaches here."
            ),
        }

    if not answer.startswith("YES"):
        return {
            "allowed": True,
            "reason": f"Scope classifier returned an unexpected answer ('{raw_text.strip()}'), failing open.",
        }

    return {"allowed": True, "reason": None}
