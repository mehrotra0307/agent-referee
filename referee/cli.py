import click

from referee.init_project import init_project

_PROVIDERS = ["gemini", "openai", "anthropic"]


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
