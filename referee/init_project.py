from pathlib import Path

import yaml

from referee.ui import divider, next_steps

_PROVIDER_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

_PROVIDER_KEY_HELP = {
    "gemini": (
        "Go to https://aistudio.google.com, sign in with any Google account, and click "
        "\"Get API key.\" Free, no credit card needed."
    ),
    "openai": (
        "Go to https://platform.openai.com/api-keys and create a new secret key. Needs "
        "billing set up first; there's no free tier."
    ),
    "anthropic": (
        "Go to https://console.anthropic.com and create a key under API Keys. Needs "
        "billing set up first; there's no free tier."
    ),
}


def init_project(
    entry_point: str,
    description: str,
    provider: str,
    target_dir: str = ".",
) -> Path:
    """Scaffold a referee.yaml with sensible guardrail defaults, and make
    sure .env is gitignored. Called by `referee init`; never touches or
    asks for an API key value itself, only prints which env var to set.

    Returns:
        The path to the referee.yaml file just written.
    """
    if provider not in _PROVIDER_ENV_VARS:
        raise ValueError(f"Unknown provider '{provider}' — expected one of {sorted(_PROVIDER_ENV_VARS)}")

    target = Path(target_dir)
    config = {
        "agent": {
            "name": Path(target_dir).resolve().name,
            "entry_point": entry_point,
        },
        "llm_provider": {
            "name": provider,
        },
        "eval": {
            "dataset": "golden_dataset.json",
        },
        "guardrails": {
            "input": {
                "pii_check": True,
                "injection_check": True,
                "rate_limit_per_session": 10,
                "scope_check": {
                    "enabled": True,
                    "description": description,
                },
            },
            "output": {
                "pii_check": True,
                "toxicity_and_groundedness_check": True,
            },
        },
        "observe": {
            "exporter": "console",
        },
    }

    config_path = target / "referee.yaml"
    with config_path.open("w") as f:
        yaml.dump(config, f, sort_keys=False, default_flow_style=False)

    _ensure_gitignore_has_env(target)

    env_var = _PROVIDER_ENV_VARS[provider]
    key_help = _PROVIDER_KEY_HELP[provider]

    if ":" in entry_point:
        file_hint, function_hint = entry_point.rsplit(":", 1)
    else:
        file_hint, function_hint = entry_point, "your_function"

    divider("DONE — here's what just happened", color="green")
    print(
        "Created referee.yaml\n"
        "  Your project's settings: which agent to test, which AI company to use for the\n"
        "  checks that need one, and which guardrails are on. Nothing secret lives in this\n"
        "  file, it's meant to be committed to git.\n"
    )
    print(
        "Updated .gitignore\n"
        "  Your API key belongs in a local .env file that never gets committed. Agent Referee\n"
        "  reads it the same way the official Google/OpenAI/Anthropic SDKs do, with\n"
        "  os.getenv(), and never asks you to paste it anywhere.\n"
    )

    next_steps(
        "  1. If you don't already have an API key:\n\n"
        f"       {key_help}\n",
        "  2. Save that key in a .env file, right here in this folder:\n\n"
        f"       {env_var}=your_key_here\n\n"
        "     Type your real key directly into that line yourself. Never paste it anywhere\n"
        "     else, including into a chat with an AI assistant helping you set this up.\n",
        "  3. Add one decorator. A \"decorator\" is just one line of Python, written directly\n"
        "     above a function, that wraps it with extra behavior without changing what's\n"
        "     inside it. Here's exactly what to do:\n\n"
        f"       Open {file_hint} in your editor and find the function called {function_hint}.\n"
        "       Add these two lines directly above its `def` line, so it looks like this:\n\n"
        "         import referee\n\n"
        "         @referee.protect(config=\"referee.yaml\")\n"
        f"         def {function_hint}(user_input: str) -> str:\n"
        "             ...   # everything already inside this function stays exactly as it was\n\n"
        "     If your agent is already a plain Python function like this, you're done, that's\n"
        "     the whole change. If you built it with CrewAI, LangGraph, or Google's ADK, your\n"
        "     real agent doesn't look like a plain function; you need one small adapter\n"
        "     function first, with the decorator on the adapter instead. See the examples/\n"
        "     folder in this project, there's a complete, working file for each of those.\n",
        "  4. Run your agent once, by hand, with any question. Before building a whole\n"
        "     dataset, just check you can see the guardrail and trace output printed\n"
        "     underneath the answer. That's confirmation it's wired up correctly.\n",
        "  5. Then run: referee dataset new",
    )

    return config_path


def _ensure_gitignore_has_env(target: Path) -> None:
    """Append a .env line to .gitignore (creating the file if needed), unless it's already there."""
    gitignore_path = target / ".gitignore"
    existing = gitignore_path.read_text() if gitignore_path.exists() else ""

    if ".env" in existing.splitlines():
        return

    with gitignore_path.open("a") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(".env\n")
