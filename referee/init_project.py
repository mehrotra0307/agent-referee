from pathlib import Path

import yaml

from referee.ui import divider, next_steps

_PROVIDER_ENV_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

_EXAMPLES_URL = "https://github.com/mehrotra0307/agent-referee/tree/main/examples"


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

    if ":" in entry_point:
        file_hint, function_hint = entry_point.rsplit(":", 1)
    else:
        file_hint, function_hint = entry_point, "your_function"

    divider("DONE — here's what just happened", color="green")
    print(
        "Created referee.yaml\n"
        "  A plain text settings file, sitting right here in this folder. It's just your\n"
        "  three answers above, nothing else, and nothing secret. Curious what's actually in\n"
        "  it? Run: cat referee.yaml\n"
    )
    print(
        "Updated .gitignore\n"
        "  Quick primer if you haven't hit this before: .gitignore is a file git (the tool\n"
        "  that tracks your code's history) reads to decide what to NEVER track or upload.\n"
        "  We added exactly one line to it: .env\n\n"
        "  To be extremely clear about this: Agent Referee has not read, received, or stored\n"
        "  any API key from you. There isn't one yet, you haven't created your .env file at\n"
        "  this point. This step is purely defensive, so that whenever you DO add a real key\n"
        "  later, git can never accidentally upload it.\n"
    )

    env_path = target.resolve() / ".env"
    if env_path.exists():
        env_step = (
            f"  1. You already have a .env file here:\n\n       {env_path}\n\n"
            f"     Open THAT file (as a file, in a text editor app, like VS Code, Sublime, "
            "or even\n     TextEdit, not this terminal window) and add this line to it, or "
            "update it if a\n     line for this key is already there:\n\n"
            f"       {env_var}=your_key_here\n\n"
            "     Replace your_key_here with your real key. By the way: nothing checks "
            "whether\n     that key is even valid at this point, we're just getting it "
            "saved somewhere\n     your own code can read it later. No pressure.\n"
        )
    else:
        env_step = (
            "  1. Create a new file called exactly .env in this folder:\n\n"
            f"       {target.resolve()}\n\n"
            "     Easiest way: in this same terminal, run this command (it creates the file "
            "for you):\n\n"
            f"       echo \"{env_var}=your_key_here\" > .env\n\n"
            f"     Then open that new .env file (as a file, in a text editor app, not this "
            "terminal\n     window, and not a chat with an AI assistant helping you set this "
            f"up) and\n     replace your_key_here with your real {provider} key. By the way: "
            "nothing checks\n     whether that key is even valid at this point, we're just "
            "getting it saved\n     somewhere your own code can read it later. No pressure.\n"
        )

    next_steps(
        env_step,
        "  2. Add one decorator. A \"decorator\" is just one line of Python, written directly\n"
        "     above a function, that wraps it with extra behavior without changing what's\n"
        "     inside it. Here's exactly what to do:\n\n"
        f"       Open {file_hint} (as a file, in a text editor app, not this terminal) and\n"
        f"       find the function called {function_hint}.\n"
        "       Add these two NEW lines (marked with +) directly above its `def` line:\n\n"
        "         + import referee\n"
        "         +\n"
        "         + @referee.protect(config=\"referee.yaml\")\n"
        f"           def {function_hint}(user_input: str) -> str:\n"
        "               ...   <- everything below this line stays exactly as it was\n\n"
        "     If your agent is already a plain Python function like that, you're done, that's\n"
        "     the whole change.\n\n"
        "     Built it with CrewAI, LangGraph, or Google's ADK instead? Your real agent\n"
        "     doesn't look like a plain function, it's a Crew, a graph, or a Runner, so you\n"
        "     need one small adapter function first (a few lines that call your real agent\n"
        "     and hand back a plain string), with the decorator on THAT adapter instead. A\n"
        "     complete, working example for each framework, showing exactly what that adapter\n"
        f"     looks like, lives here:\n\n       {_EXAMPLES_URL}\n",
        "  3. Run your agent once, by hand, with any question, right in this same terminal:\n\n"
        f"       referee try \"a question for your agent\"\n\n"
        "     This calls your agent exactly once and prints the answer. If you also see\n"
        "     guardrail and trace lines printed above it, the decorator is wired up correctly\n"
        "     and you're ready for the next step. This works no matter which framework your\n"
        "     agent uses underneath, since it's calling the same entry_point you gave in\n"
        "     Question 1.\n",
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
