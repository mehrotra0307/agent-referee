from pathlib import Path

import yaml

from referee.ui import divider, next_steps

_PROVIDER_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
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
        f"  1. Create a .env file in this directory and add:\n\n       {env_var}=your_key_here\n",
        "  2. Add one decorator above your agent's function:\n\n"
        "       import referee\n\n"
        "       @referee.protect(config=\"referee.yaml\")\n"
        "       def my_agent(user_input: str) -> str:\n"
        "           ...\n",
        "  3. Run your agent once, by hand, with any question. Before building a whole\n"
        "     dataset, just check you can see the guardrail and trace output printed\n"
        "     underneath the answer. That's confirmation it's wired up correctly.\n",
        "  4. Then run: referee dataset new",
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
