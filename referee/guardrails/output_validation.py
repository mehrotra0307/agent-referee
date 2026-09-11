from typing import Any

from referee.guardrails.input_validation import PII_PATTERNS
from referee.providers import call_llm
import re

_TOXICITY_ONLY_PROMPT = """Analyze this AI agent's response.

Response: {response}

Answer with EXACTLY one word: YES if the response is toxic, hateful, or otherwise \
inappropriate, NO if it is not.

Example answer: "YES" or "NO\""""

_TOXICITY_AND_GROUNDEDNESS_PROMPT = """Analyze this AI agent's response.

Reference context the response must stay consistent with: {grounding_context}
User asked: {user_input}
Agent responded: {agent_response}

Answer with EXACTLY two words, space-separated:
First word: YES or NO (is this response toxic, hateful, or inappropriate?)
Second word: YES or NO (does this response contradict or invent something NOT in the reference context?)

Example answer: "NO NO\""""


def check_output_pii(agent_response: str) -> dict[str, Any]:
    """Regex-only check for PII leaking in the agent's own response (mirrors
    check_pii on the input side). No API call.

    Returns:
        {"allowed": bool, "reason": str | None}
    """
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, agent_response):
            return {
                "allowed": False,
                "reason": (
                    f"Blocked: the agent's response looks like it contains a {pii_type}. "
                    "Same regex patterns as the input-side check, run on the way out instead "
                    "of the way in — catches the model leaking or inventing sensitive data."
                ),
            }
    return {"allowed": True, "reason": None}


def check_toxicity_and_groundedness(
    user_input: str,
    agent_response: str,
    provider_config: dict[str, Any],
    grounding_context: str = "",
) -> dict[str, Any]:
    """One LLM call checking toxicity, and groundedness too if grounding_context
    is non-empty (i.e. the user configured guardrails.output.grounding_context
    in referee.yaml). Fails open (allowed=True) on a call error or an
    unparseable answer, by explicit design choice — see the returned reason.

    Returns:
        {"allowed": bool, "reason": str | None}
    """
    if grounding_context:
        prompt = _TOXICITY_AND_GROUNDEDNESS_PROMPT.format(
            grounding_context=grounding_context, user_input=user_input, agent_response=agent_response
        )
    else:
        prompt = _TOXICITY_ONLY_PROMPT.format(response=agent_response)

    try:
        raw_text = call_llm(prompt, provider_config)
    except Exception as exc:
        return {"allowed": True, "reason": f"Output guardrail call failed, failing open: {exc}"}

    parts = raw_text.strip().upper().split()
    if not parts:
        return {"allowed": True, "reason": "Output guardrail returned an empty answer, failing open."}

    if "YES" in parts[0]:
        return {
            "allowed": False,
            "reason": "Blocked: response flagged as toxic or inappropriate.",
        }

    if grounding_context and len(parts) > 1 and "YES" in parts[1]:
        return {
            "allowed": False,
            "reason": (
                "Blocked: response appears to contradict or invent something not in the "
                "grounding context you configured (possible hallucination)."
            ),
        }

    return {"allowed": True, "reason": None}


def validate_output(
    user_input: str,
    agent_response: str,
    config: dict[str, Any],
    provider_config: dict[str, Any],
) -> dict[str, Any]:
    """Run the configured output guardrails in order: PII leak, then
    toxicity/groundedness. Stops and returns at the first block. config is
    the full guardrails.* section of referee.yaml.

    Returns:
        {"allowed": bool, "reason": str | None}
    """
    output_config = config.get("output", {})

    if output_config.get("pii_check", True):
        pii_result = check_output_pii(agent_response)
        if not pii_result["allowed"]:
            return pii_result

    if output_config.get("toxicity_and_groundedness_check", True):
        toxicity_result = check_toxicity_and_groundedness(
            user_input,
            agent_response,
            provider_config,
            grounding_context=output_config.get("grounding_context", ""),
        )
        if not toxicity_result["allowed"]:
            return toxicity_result

    return {"allowed": True, "reason": None}
