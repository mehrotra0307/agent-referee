from pathlib import Path

import yaml

_PROVIDER_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

_WHAT_WAS_CREATED = """
Here's what was just created, and why:

  referee.yaml
    Your project's configuration — which agent to test, which LLM provider
    to use for the checks that need one, and which guardrails are on.
    Nothing secret lives in this file; it's meant to be committed to git.

  .gitignore entry for .env
    Your API key belongs in a local .env file that never gets committed.
    Agent Referee reads it the same way the official Google/OpenAI/Anthropic
    SDKs do — os.getenv() — and never asks you to paste it anywhere.

What to do next, in order:

  1. Create a .env file in this directory and add:

       {env_var}=your_key_here

  2. Add one decorator above your agent's function:

       import referee

       @referee.protect(config="referee.yaml")
       def my_agent(user_input: str) -> str:
           ...

  3. Run your agent once, by hand, with any question. Before you build a whole
     dataset, just check you can actually see the guardrail and trace output
     printed underneath the answer. If you see that, it's wired up correctly
     and you're ready for the next step.

  4. Then run `referee dataset new` to build your first test list, and
     `referee eval run` to grade your agent against it.
"""


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

    print(_WHAT_WAS_CREATED.format(env_var=_PROVIDER_ENV_VARS[provider]))

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
