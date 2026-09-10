import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click

from referee.config import get_provider_config, load_config
from referee.entry_point import load_entry_point
from referee.eval.deterministic import check_deterministic
from referee.eval.runner import run_evaluation
from referee.guardrails.input_validation import check_injection, check_pii
from referee.guardrails.scope_check import check_scope
from referee.guardrails.test_suite import ADVERSARIAL_TEST_CASES
from referee.init_project import init_project
from referee.protect import protect

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


@click.group()
@click.version_option()
def main():
    """Agent Referee — evaluation, guardrails, and observability for any AI agent."""


@main.command()
@click.option("--entry-point", prompt="Your agent's entry point (e.g. agent/my_agent.py:ask_my_agent)")
@click.option("--description", prompt="One-line description of what your agent is allowed to talk about")
@click.option(
    "--provider",
    prompt=f"Which LLM provider will you use for the checks that need one? ({'/'.join(_PROVIDERS)})",
    type=click.Choice(_PROVIDERS),
)
def init(entry_point: str, description: str, provider: str):
    """Scaffold referee.yaml for this project. Never asks for an API key."""
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
    cfg = load_config(config)
    input_cfg = cfg.get("guardrails", {}).get("input", {})
    scope_cfg = input_cfg.get("scope_check", {})
    provider_config = get_provider_config(cfg)

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
    """Zero-config, zero-API-key demo: eval + guardrails + tracing in ~30 seconds."""
    click.echo(
        "Agent Referee demo — no config file, no API key, nothing installed beyond this "
        "package. This wraps a tiny built-in mock agent so you can see the full loop before "
        "touching your own agent.\n"
    )

    protected_agent = protect(config=_DEMO_CONFIG)(_demo_agent)

    click.echo("1. A normal question passes straight through, guardrails and tracing running silently:\n")
    click.echo(f"   > {protected_agent('What time do you close?')}\n")

    click.echo("2. A message containing PII gets caught by the input guardrail BEFORE the agent ever runs:\n")
    click.echo(f"   > {protected_agent('call me back at 9876543210 please')}\n")

    click.echo("3. A tiny evaluation, scoring the agent's real answer against what it must mention:\n")
    eval_case = {
        "id": "demo_eval_001",
        "check": "contains_any",
        "expected_contains": ["11 AM", "11 PM"],
    }
    eval_result = check_deterministic(eval_case, _demo_agent("What time do you close?"))
    status = "PASS" if eval_result["passed"] else "FAIL"
    click.echo(f"   [{status}] {eval_result['reason']}\n")

    click.echo(
        "That's the whole loop: a guardrail blocking bad input before it ever reaches your "
        "agent, a trace recording every step above, and an evaluator scoring the answer — all "
        "with zero setup.\n\nNext: run `referee init` to wire this into your real agent."
    )


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
