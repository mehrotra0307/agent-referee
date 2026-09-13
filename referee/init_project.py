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

    project_folder = target.resolve().name

    env_step = (
        f"  1. Add your {provider} API key to a file called .env, in the same folder as\n"
        "     everything else here (not a subfolder, not one level up, this one).\n\n"
        "     Already have a .env file sitting here? Just add this one line to it:\n\n"
        f"       {env_var}=your_key_here\n\n"
        "     Don't have one yet, or not sure? A .env file is nothing fancy, just a plain\n"
        "     text file. Concretely, using your actual project, it should end up looking\n"
        "     like this either way:\n\n"
        f"       {project_folder}/                 <- this folder, right where you are now\n"
        f"       ├── {file_hint:<22} <- your agent\n"
        "       ├── referee.yaml           <- just created, a moment ago\n"
        "       └── .env                   <- your key goes in here\n\n"
        "     Easiest way to create it: run this command in this same terminal. It works\n"
        "     whether or not a .env file already exists here, it only ever adds a line,\n"
        "     never deletes or overwrites anything, so there's no wrong time to run it:\n\n"
        f"       echo \"{env_var}=your_key_here\" >> .env\n\n"
        "     Either way, open that .env file (as a file, in a text editor app like VS Code,\n"
        "     Sublime, or even TextEdit, NOT this terminal window, and not a chat with an AI\n"
        "     assistant helping you set this up) and replace your_key_here with your real\n"
        f"     {provider} key.\n\n"
        "     And since we know exactly what you're thinking: no, nothing here checks "
        "whether\n     that key is real, valid, or even shaped like a real key. We're not "
        "peeking. This\n     step is just getting it saved somewhere your own code can read "
        "it later.\n"
    )

    decorator_step = (
        "  2. Add one decorator. A \"decorator\" is just one line of Python, written directly\n"
        "     above a function, that wraps it with extra behavior without changing what's\n"
        "     inside it.\n\n"
        f"     Open {file_hint} (as a file, in a text editor app, not this terminal) and find\n"
        f"     the function called {function_hint}. That's your real file and function name,\n"
        "     straight from your answer to Question 1, not a generic example, so it's already\n"
        "     exactly right for your project.\n\n"
        "     Copy exactly these two lines, character for character. Nothing below is a\n"
        "     symbol or a marker, it's the literal code:\n\n"
        "         import referee\n\n"
        "         @referee.protect(config=\"referee.yaml\")\n\n"
        f"     Paste them directly above your {function_hint} function's own `def` line,\n"
        "     whatever that line already says. Don't retype or change that line, or anything\n"
        "     inside the function, just add these two lines above it.\n\n"
        "     If your agent is already a plain Python function like that, you're done, that's\n"
        "     the whole change.\n\n"
        "     Built it with CrewAI, LangGraph, or Google's ADK instead? Your real agent\n"
        "     doesn't look like a plain function, it's a Crew, a graph, or a Runner, so you\n"
        "     need one small adapter function first (a few lines that call your real agent\n"
        "     and hand back a plain string), with the decorator on THAT adapter instead. A\n"
        "     complete, working example for each framework, showing exactly what that adapter\n"
        f"     looks like, lives here:\n\n       {_EXAMPLES_URL}\n"
    )

    try_step = (
        "  3. Run your agent once, by hand, right in this same terminal. Replace the text in\n"
        "     quotes below with an actual question, that's a placeholder, not something to\n"
        "     copy exactly as it is:\n\n"
        "       referee try \"type any question here\"\n\n"
        "     What you should expect to see (illustration only, your real numbers and answer\n"
        "     will look different, this is just the shape of it):\n\n"
        "       ────────────────────────────────────────────────────────\n"
        "       LIVE TRACE — printed as it happens, below\n"
        "       ────────────────────────────────────────────────────────\n"
        "         · input_guardrail (0.3ms) — guardrail.allowed=True\n"
        "         · agent_call (612.0ms)\n"
        "         · output_guardrail (0.2ms) — guardrail.allowed=True\n\n"
        "       ┏━ AGENT'S ANSWER\n"
        "       ┃ We're open 11 AM to 11 PM, every day.\n"
        "       ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "     Some trace lines above, then your real answer clearly boxed off at the end. If\n"
        "     you see something in roughly that shape, even with completely different words\n"
        "     and numbers, it's wired up correctly and you're ready for the next step.\n"
    )

    next_steps(
        env_step,
        decorator_step,
        try_step,
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
