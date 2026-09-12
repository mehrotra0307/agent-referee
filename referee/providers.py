"""Provider-agnostic LLM calls, shared by the LLM-judge evaluator and the
scope-check guardrail. All three SDKs ship in core (see pyproject.toml for
why), but are still imported lazily inside each _call_* function rather
than at module load time: importing google-genai in particular drags in
google-auth, which prints noisy environment warnings (Python version,
OpenSSL version) the instant it's imported — before anyone has actually
asked to call an LLM. `referee demo`, for example, never needs a real
provider call at all, and shouldn't pay that cost just because
`import referee` happened."""

import os
from typing import Any

_DEFAULT_MODELS = {
    "gemini": "gemini-3.1-flash-lite",
    "openai": "gpt-5-nano",
    "anthropic": "claude-haiku-4-5-20251001",
}

_API_KEY_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def _get_api_key(provider_name: str) -> str:
    env_var = _API_KEY_ENV_VARS[provider_name]
    api_key = os.getenv(env_var)
    if not api_key:
        raise RuntimeError(
            f"Agent Referee needs {env_var} to call the '{provider_name}' LLM judge/scope-check, "
            f"but it isn't set. Add this to your .env file:\n\n"
            f"    {env_var}=your_key_here\n\n"
            "Agent Referee reads it locally with os.getenv() — it is never sent to us or "
            "typed into any prompt."
        )
    return api_key


def _call_gemini(prompt: str, model: str) -> str:
    from google import genai

    client = genai.Client(api_key=_get_api_key("gemini"))
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


def _call_openai(prompt: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=_get_api_key("openai"))
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str, model: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=_get_api_key("anthropic"))
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


_DISPATCH = {
    "gemini": _call_gemini,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
}


def call_llm(prompt: str, provider_config: dict[str, Any]) -> str:
    """Send prompt to whichever provider provider_config["name"] names
    (from referee.yaml's llm_provider section), using provider_config["model"]
    if set, else a sensible per-provider default. Returns the raw text reply.
    """
    provider_name = provider_config["name"]
    if provider_name not in _DISPATCH:
        raise ValueError(
            f"Unknown llm_provider '{provider_name}' in referee.yaml — "
            f"must be one of {sorted(_DISPATCH)}."
        )

    model = provider_config.get("model") or _DEFAULT_MODELS[provider_name]
    return _DISPATCH[provider_name](prompt, model)
