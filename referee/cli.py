import json
from datetime import datetime
from pathlib import Path

import click

from referee.config import get_provider_config, load_config
from referee.entry_point import load_entry_point
from referee.eval.runner import run_evaluation
from referee.init_project import init_project

_PROVIDERS = ["gemini", "openai", "anthropic"]

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
    report_path = reports_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    click.echo(f"Full report saved to: {report_path}")

    if report["critical_failures"] > 0:
        click.echo("\nBLOCKING: critical-severity test failure(s) detected.")
        raise SystemExit(1)
