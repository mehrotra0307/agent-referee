import json
import subprocess
import sys
import warnings
from datetime import datetime
from pathlib import Path

import click

# Silences two specific, harmless warnings that fire the instant a provider
# SDK is imported on an older Python/OpenSSL setup (Python's own EOL notice
# via google-auth, and urllib3's LibreSSL notice) — not anything Agent
# Referee itself did wrong, just noise that makes a first-run demo look
# broken. Deliberately narrow: this doesn't touch any other warning.
warnings.filterwarnings("ignore", message=".*end of life.*")
warnings.filterwarnings("ignore", message=".*OpenSSL.*")

from referee.config import get_provider_config, load_config
from referee.entry_point import load_entry_point
from referee.eval.deterministic import check_deterministic
from referee.eval.runner import run_evaluation
from referee.guardrails.input_validation import check_injection, check_pii
from referee.guardrails.scope_check import check_scope
from referee.guardrails.test_suite import ADVERSARIAL_TEST_CASES
from referee.init_project import init_project
from referee.protect import protect
from referee.ui import divider, next_steps, pause, type_out

_PROVIDERS = ["gemini", "openai", "anthropic"]

_DEMO_CONFIG = {
    "agent": {"name": "demo-agent"},
    "llm_provider": {"name": "gemini"},
    "guardrails": {
        "input": {"pii_check": True, "injection_check": True, "rate_limit_per_session": 1000},
        "output": {"pii_check": True, "toxicity_and_groundedness_check": False},
    },
    "observe": {"exporter": "console"},
}


def _demo_agent(user_input: str) -> str:
    lower = user_input.lower()
    if "close" in lower or "hour" in lower:
        return "We're open 11 AM to 11 PM, every day."
    if "deliver" in lower:
        return "We deliver within 5 km, with a flat delivery fee."
    return "I can help with hours, menu, and delivery questions!"


_DATASET_INTRO = """
A golden dataset is just a list of questions your agent might get, and what a
correct answer should mention. `referee eval run` uses it to check your agent's
real answers automatically, so you don't have to read every response yourself.

This wizard runs fully offline — no API key, no network call, nothing sent
anywhere. Let's build yours, one question at a time.
"""

_EVAL_RUN_INTRO = """
An evaluation is a report card. It asks your agent every question in your golden
dataset, checks each real answer against what you said a correct one should
mention, and tells you what passed and what failed, in plain English, one
sentence at a time. Nothing here changes your agent — it only grades it.
"""

_GUARDRAILS_TEST_INTRO = """
A guardrail is a bouncer, not a grader. It doesn't care if an answer is good —
it cares whether a message is safe enough to let through at all. This command
throws a small set of real attack attempts (fake emails, prompt-injection
phrases, off-topic questions) at your setup and tells you which ones actually
got blocked. Never seen the word "guardrail" before today? This is the
fastest way to actually understand what one does.
"""


@click.group()
@click.version_option()
def main():
    """Agent Referee — evaluation, guardrails, and observability for any AI agent."""


@main.command()
@click.option("--entry-point", default=None, help="Skip the interactive question with this value.")
@click.option("--description", default=None, help="Skip the interactive question with this value.")
@click.option("--provider", default=None, type=click.Choice(_PROVIDERS), help="Skip the interactive question with this value.")
def init(entry_point: str, description: str, provider: str):
    """Scaffold referee.yaml for this project. Never asks for an API key."""
    click.echo("\nLet's get your agent connected. Three quick questions, no API key involved, ever.")

    if entry_point is None:
        divider("QUESTION 1 of 3 — Where does your agent live?")
        click.echo(
            "However you built your agent, a plain API call, CrewAI, LangGraph, Google's ADK,\n"
            "anything at all, somewhere in your code there's ONE function that takes a question\n"
            "in and returns an answer out. That's what we need to find: which file it's in, and\n"
            "what that function is called.\n"
        )
        click.echo("Format:  path/to/file.py:function_name\n")
        click.echo(
            "Example: say you have a file called my_agent.py, right here in this same folder,\n"
            "with a function in it called ask. You'd type:  my_agent.py:ask\n"
        )
        entry_point = click.prompt("Your answer")

    if description is None:
        divider("QUESTION 2 of 3 — What is your agent allowed to talk about?")
        click.echo(
            "One sentence, plain English. This gets used later to catch questions that are\n"
            "completely off-topic, like someone asking your pizza-shop bot for tax advice.\n"
        )
        click.echo('Example:  "Only answer questions about a pizza shop\'s menu, hours, and delivery"\n')
        description = click.prompt("Your answer")

    if provider is None:
        divider("QUESTION 3 of 3 — Which AI company's API do you use?")
        click.echo(
            "This is only used for the one or two checks that need to ask an AI a question of\n"
            "its own, like \"does this answer sound toxic?\" Pick whichever matches an API key\n"
            "you already have, or plan to get.\n"
        )
        provider = click.prompt("Your answer", type=click.Choice(_PROVIDERS))

    init_project(entry_point=entry_point, description=description, provider=provider)


@main.group(name="dataset")
def dataset_group():
    """Manage your golden evaluation dataset."""


@dataset_group.command(name="new")
@click.option("--output", default="golden_dataset.json", show_default=True)
def dataset_new(output: str):
    """Build a golden dataset interactively. Fully offline — no API key needed."""
    click.echo(_DATASET_INTRO)

    example_path = Path(__file__).parent / "eval" / "example_dataset.json"
    click.echo(f"Need inspiration first? A read-only worked example lives at:\n  {example_path}\n")

    entries = []
    counter = 1
    while True:
        question = click.prompt(
            f"Question #{counter} a user might ask your agent (Enter to finish)",
            default="",
            show_default=False,
        )
        if not question:
            break

        must_mention = click.prompt("What must a correct answer mention? (comma-separated phrases)")
        category = click.prompt("Category (a short label to group this test case)", default="general")

        entries.append(
            {
                "id": f"eval_{counter:03d}",
                "category": category,
                "input": question,
                "eval_type": "deterministic",
                "check": "contains_any",
                "expected_contains": [phrase.strip() for phrase in must_mention.split(",") if phrase.strip()],
                "severity": "medium",
            }
        )
        counter += 1

    if not entries:
        click.echo("No test cases added — nothing written.")
        return

    dataset = {
        "dataset_version": "v1",
        "description": "Golden dataset, built with `referee dataset new`.",
        "test_cases": entries,
    }
    Path(output).write_text(json.dumps(dataset, indent=2) + "\n")
    click.echo(f"\nWrote {len(entries)} test case(s) to {output}. Run `referee eval run` next.")


@main.group(name="eval")
def eval_group():
    """Run evaluations against your agent."""


@eval_group.command(name="run")
@click.option("--config", default="referee.yaml", show_default=True)
def eval_run(config: str):
    """Run your golden dataset against your agent and print a report. CI-ready."""
    click.echo(_EVAL_RUN_INTRO)
    cfg = load_config(config)
    agent_cfg = cfg["agent"]
    dataset_path = cfg.get("eval", {}).get("dataset", "golden_dataset.json")

    agent_fn = load_entry_point(agent_cfg["entry_point"])
    provider_config = get_provider_config(cfg)

    click.echo(f"Running evaluation for '{agent_cfg['name']}' against {dataset_path}...\n")

    report = run_evaluation(dataset_path, agent_fn, provider_config, datetime.now().isoformat())

    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        click.echo(f"[{status}] {result['id']} ({result['category']}, severity={result['severity']})")
        click.echo(f"       {result['reason']}")

    click.echo("\n--- SUMMARY ---")
    click.echo(f"Passed: {report['passed']}/{report['total_tests']} ({report['pass_rate'] * 100:.0f}%)")
    click.echo(f"Critical failures: {report['critical_failures']}")

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"eval_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    click.echo(f"Full report saved to: {report_path}")

    if report["critical_failures"] > 0:
        click.echo("\nBLOCKING: critical-severity test failure(s) detected.")
        raise SystemExit(1)


@main.group(name="guardrails")
def guardrails_group():
    """Test your configured guardrails against packaged adversarial attacks."""


@guardrails_group.command(name="test")
@click.option("--config", default="referee.yaml", show_default=True)
@click.option(
    "--local-only",
    is_flag=True,
    help="Skip the scope-check attack, which makes a real LLM call using your configured key.",
)
def guardrails_test(config: str, local_only: bool):
    """Run packaged adversarial attacks against your configured guardrails."""
    click.echo(_GUARDRAILS_TEST_INTRO)

    scope_cfg = {}
    provider_config = {}
    if Path(config).exists():
        cfg = load_config(config)
        input_cfg = cfg.get("guardrails", {}).get("input", {})
        scope_cfg = input_cfg.get("scope_check", {})
        provider_config = get_provider_config(cfg)
    else:
        click.echo(
            f"No {config} found — that's fine, this command doesn't need one. Running the free, "
            "local checks (PII and prompt-injection) only. Run `referee init` first if you also "
            "want to test the on-topic scope check.\n"
        )
        local_only = True

    click.echo("Running packaged adversarial guardrail tests...\n")

    blocked_count = 0
    total = 0
    case_results = []

    for case in ADVERSARIAL_TEST_CASES:
        check_type = case["check"]

        if check_type == "scope" and (local_only or not scope_cfg.get("enabled")):
            click.echo(f"[SKIP] {case['id']} ({case['category']}) — scope_check disabled or --local-only set")
            continue

        if check_type == "pii":
            result = check_pii(case["input"])
        elif check_type == "injection":
            result = check_injection(case["input"])
        else:
            result = check_scope(case["input"], scope_cfg.get("description", ""), provider_config)

        total += 1
        blocked = not result["allowed"]
        if blocked:
            blocked_count += 1

        click.echo(f"[{'PASS' if blocked else 'FAIL'}] {case['id']} ({case['category']})")
        click.echo(f"       Attack simulated: {case['attack_description']}")
        if not blocked:
            click.echo("       This guardrail let the attack through — it was not caught.")

        case_results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "attack_description": case["attack_description"],
                "blocked": blocked,
            }
        )

    click.echo("\n--- SUMMARY ---")
    click.echo(f"Blocked {blocked_count}/{total} adversarial attacks.")

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"guardrails_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(
        json.dumps(
            {
                "run_timestamp": datetime.now().isoformat(),
                "total_attacks": total,
                "blocked": blocked_count,
                "results": case_results,
            },
            indent=2,
        )
        + "\n"
    )
    click.echo(f"Full report saved to: {report_path}")

    if blocked_count < total:
        raise SystemExit(1)


@main.command()
def demo():
    """Zero-config, zero-API-key demo: eval + guardrails + tracing, live."""
    click.echo(
        "Agent Referee demo — no config file, no API key, nothing installed beyond this "
        "package.\n"
    )
    pause(0.4)
    click.echo(
        "Meet the demo agent: a pretend pizza-shop assistant, built into this package just "
        "for this walkthrough. It's not a real AI, just a few lines of if/else — the point "
        "isn't the agent, it's watching Agent Referee work around it. Three short scenes:\n"
    )
    pause(0.8)

    protected_agent = protect(config=_DEMO_CONFIG)(_demo_agent)

    divider("SCENE 1 — A normal question")
    click.echo("A customer types a question. Watch it go in, and come back out the other side:\n")
    pause(0.3)
    click.echo(click.style("customer> ", fg="cyan"), nl=False)
    type_out("What time do you close?")
    pause(0.4)
    click.echo("\n(behind the scenes, this is the real trace, printed live as it happens:)\n")
    response = protected_agent("What time do you close?")
    pause(0.2)
    click.echo()
    click.echo(click.style("agent> ", fg="green") + response)
    pause(1.0)

    divider("SCENE 2 — Someone pastes personal info by accident")
    click.echo("Same agent, but this time the message itself is the problem:\n")
    pause(0.3)
    click.echo(click.style("customer> ", fg="cyan"), nl=False)
    type_out("call me back at 9876543210 please")
    pause(0.4)
    click.echo("\n(the input guardrail catches this BEFORE the agent function ever runs:)\n")
    response = protected_agent("call me back at 9876543210 please")
    pause(0.2)
    click.echo()
    click.echo(click.style("agent> ", fg="yellow") + response)
    pause(1.0)

    divider("SCENE 3 — Grading the answer from Scene 1")
    click.echo(
        "A golden dataset says a correct answer to 'What time do you close?' must mention "
        "'11 AM' or '11 PM'. Checking the real answer from Scene 1 against that:\n"
    )
    pause(0.5)
    eval_case = {
        "id": "demo_eval_001",
        "check": "contains_any",
        "expected_contains": ["11 AM", "11 PM"],
    }
    eval_result = check_deterministic(eval_case, _demo_agent("What time do you close?"))
    status_color = "green" if eval_result["passed"] else "red"
    click.echo(click.style(f"[{'PASS' if eval_result['passed'] else 'FAIL'}] ", fg=status_color, bold=True) + eval_result["reason"])
    pause(0.6)

    click.echo()
    click.echo(click.style("─" * 58, dim=True))
    click.echo(
        "\nThat's the whole loop: a guardrail blocking bad input before it reaches your agent "
        "(Scene 2), a trace recording every step as it happens (Scene 1), and an evaluator "
        "grading the answer afterward (Scene 3). Zero setup, zero API key, all three pillars."
    )
    next_steps("referee init   — wire this into your real agent")


@main.command()
def dashboard():
    """Launch the local Streamlit dashboard (reads local reports/, nothing hosted by us)."""
    app_path = Path(__file__).parent / "dashboard" / "app.py"

    try:
        import streamlit  # noqa: F401
    except ImportError:
        click.echo(
            "The dashboard needs Streamlit, which isn't installed by default. Install it with:\n\n"
            "    pip install agent-referee[dashboard]\n"
        )
        raise SystemExit(1)

    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])
