"""Shared terminal styling helpers, used by cli.py and init_project.py so
every command (init, demo, dataset new, eval run, guardrails test) shares
one consistent visual language instead of each printing its own one-off
formatting. Small and dependency-free beyond click, which is already a
core dependency of the whole package.
"""

import sys
import time

import click


def divider(title: str, color: str = "cyan") -> None:
    """Print a labeled section break, e.g. "QUESTION 1 of 3 — ..." or "SCENE 2 — ...".

    Always prints two leading blank lines rather than one: a prompt or
    printed line right before this call rarely ends with a blank line of
    its own (click.prompt() in particular doesn't), so a single leading
    echo() here isn't enough to guarantee real visual separation.
    """
    click.echo()
    click.echo()
    click.echo(click.style("─" * 58, dim=True))
    click.echo(click.style(title, bold=True, fg=color))
    click.echo(click.style("─" * 58, dim=True))
    click.echo()


def next_steps(*lines: str) -> None:
    """Print a clearly marked "what to do next" block, consistent across every command."""
    click.echo()
    click.echo(click.style("→ NEXT", bold=True, fg="magenta"))
    click.echo(click.style("─" * 58, dim=True))
    for line in lines:
        click.echo(line)
    click.echo()


def type_out(text: str, delay: float = 0.018) -> None:
    """Print text one character at a time, so it reads as something happening live."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")


def pause(seconds: float) -> None:
    time.sleep(seconds)
