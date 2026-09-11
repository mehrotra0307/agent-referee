import json
import re
from typing import Any

from referee.providers import call_llm

_JUDGE_PROMPT_TEMPLATE = """You are grading an AI agent's response. Score it from 1 to 5 based on this rubric:

Rubric: {rubric}

Original question: {question}
Agent's actual response: {response}

Respond ONLY with valid JSON in this exact shape, nothing else:
{{"score": <integer 1-5>, "reasoning": "<one sentence why>"}}"""

_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw_text: str) -> dict[str, Any]:
    """Parse the judge model's JSON reply, tolerating markdown code fences or
    stray text around the object (a real failure mode LLMs hit in practice).
    Raises ValueError if no valid JSON object can be found at all.
    """
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = _JSON_OBJECT_PATTERN.search(text)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"LLM judge did not return parseable JSON. Raw output: {raw_text!r}")


def check_llm_judge(test_case: dict[str, Any], actual_response: str, provider_config: dict[str, Any]) -> dict[str, Any]:
    """Score a test case by asking a second LLM call to grade actual_response
    against test_case["rubric"], 1-5, using the provider configured in
    referee.yaml (Gemini, OpenAI, or Anthropic — see referee/providers.py).

    Returns:
        {"id": str, "passed": bool, "reason": str}
    """
    prompt = _JUDGE_PROMPT_TEMPLATE.format(
        rubric=test_case["rubric"],
        question=test_case["input"],
        response=actual_response,
    )

    raw_text = call_llm(prompt, provider_config)

    try:
        parsed = _extract_json(raw_text)
    except ValueError as exc:
        return {
            "id": test_case["id"],
            "passed": False,
            "reason": f"Judge call failed to produce valid JSON, treating as a failure: {exc}",
        }

    score = parsed["score"]
    threshold = test_case["pass_threshold"]
    passed = score >= threshold

    return {
        "id": test_case["id"],
        "passed": passed,
        "reason": f"Judge scored {score}/5 (needed >= {threshold}): {parsed.get('reasoning', 'no reasoning given')}",
    }
