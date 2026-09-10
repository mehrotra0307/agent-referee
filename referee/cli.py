import json
from pathlib import Path

import click

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
