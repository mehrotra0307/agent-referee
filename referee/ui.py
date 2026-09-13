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


def next_steps(*steps) -> None:
    """Print a clearly marked "what to do next" block, consistent across every command.

    Each step is a (command, description) tuple. command is a literal
    string to run, shown on its own bold/colored line prefixed with '$',
    or None for a step with no command (a plain confirmation note).
    description is plain text explaining that step; long lines are left
    as-is (the caller should hand-wrap around ~75 chars).

    Deliberately structured instead of accepting raw pre-formatted
    strings: leaving spacing to be typed correctly by hand at every call
    site is exactly how "Next: referee dataset new" and its description
    ended up jammed onto adjacent lines with no gap between them in an
    earlier version of this function.
    """
    click.echo()
    click.echo(click.style("→ NEXT", bold=True, fg="magenta"))
    click.echo(click.style("─" * 58, dim=True))
    for command, description in steps:
        click.echo()
        if command:
            click.echo(click.style(f"  $ {command}", fg="cyan", bold=True))
            click.echo()
        for line in description.splitlines():
            click.echo(f"  {line}" if line else "")
    click.echo()


def example(title: str, fields: dict) -> None:
    """Print a labeled, indented example block (e.g. a worked question/answer/
    category triple), visually distinct from surrounding prose with its own
    colored label — so an example never blends into the paragraph around it.
    """
    click.echo()
    click.echo(click.style(f"◆ EXAMPLE — {title}", bold=True, fg="yellow"))
    label_width = max((len(key) for key in fields), default=0)
    for key, value in fields.items():
        click.echo(f"    {key.ljust(label_width)}   {value}")
    click.echo()


def callout(label: str, text: str, color: str = "green") -> None:
    """Print text set apart with a left border and a colored label, so a
    result (a final answer, a pass/fail summary) doesn't get lost among
    whatever else was printed just before it, like trace lines.
    """
    click.echo()
    click.echo(click.style(f"┏━ {label}", bold=True, fg=color))
    for line in text.splitlines() or [""]:
        click.echo(click.style("┃ ", fg=color) + line)
    click.echo(click.style("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", fg=color))
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
