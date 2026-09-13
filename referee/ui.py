"""Shared terminal styling helpers, used by cli.py and init_project.py so
every command (init, demo, dataset new, eval run, guardrails test) shares
one consistent visual language instead of each printing its own one-off
formatting. Small and dependency-free beyond click, which is already a
core dependency of the whole package.
"""

import json
import re
import sys
import time
from pathlib import Path

import click

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _visible_len(text: str) -> int:
    return len(_ANSI.sub("", text))


def _draw_table(headers: list, rows: list) -> None:
    """Render a real bordered grid table (box-drawing characters), not just
    an indented list. Column widths are computed from visible text length,
    ignoring ANSI color codes, so styled cells (a colored ✓/✗) still align.
    """
    widths = [
        max(_visible_len(headers[i]), *(_visible_len(row[i]) for row in rows)) if rows else _visible_len(headers[i])
        for i in range(len(headers))
    ]

    def _line(left: str, mid: str, right: str, fill: str = "─") -> str:
        return left + mid.join(fill * (w + 2) for w in widths) + right

    def _row(cells) -> str:
        parts = []
        for cell, width in zip(cells, widths):
            pad = width - _visible_len(cell)
            parts.append(f" {cell}{' ' * pad} ")
        return "│" + "│".join(parts) + "│"

    click.echo(click.style(_line("┌", "┬", "┐"), dim=True))
    click.echo(_row([click.style(h, bold=True) for h in headers]))
    click.echo(click.style(_line("├", "┼", "┤"), dim=True))
    for row in rows:
        click.echo(_row(row))
    click.echo(click.style(_line("└", "┴", "┘"), dim=True))


def phase(title: str, description: str, color: str = "magenta") -> None:
    """Announce moving into a whole new phase (evaluation, guardrails, etc.) —
    more prominent than divider(), which marks a sub-section within one
    command, not a shift to a different part of the overall workflow.
    """
    click.echo()
    click.echo(click.style("═" * 58, fg=color))
    click.echo(click.style(f"  {title}", bold=True, fg=color))
    click.echo(click.style("═" * 58, fg=color))
    click.echo()
    for line in description.splitlines():
        click.echo(line)
    click.echo()


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
            click.echo("  Run this:")
            click.echo(click.style(f"  {command}", fg="cyan", bold=True))
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


def _latest_report(pattern: str):
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return None
    matches = sorted(reports_dir.glob(pattern), reverse=True)
    if not matches:
        return None
    return json.loads(matches[0].read_text())


def status_table() -> None:
    """Print a compact, colored terminal summary of everything set up on this
    agent so far, reading only local files (golden_dataset.json and the
    latest reports/*.json). A real, zero-extra-dependency alternative to the
    full Streamlit dashboard for anyone who doesn't want the ~180MB install
    just to see where things stand.
    """
    click.echo()
    click.echo(click.style("═" * 58, fg="cyan"))
    click.echo(click.style("  STATUS — everything set up on this agent so far", bold=True, fg="cyan"))
    click.echo(click.style("═" * 58, fg="cyan"))
    click.echo()

    ok_mark = click.style("✓", fg="green", bold=True)
    fail_mark = click.style("✗", fg="red", bold=True)
    pending_mark = click.style("·", dim=True)

    rows = [[ok_mark, "Guardrails + tracing", "ON, automatic on every real call via the decorator"]]

    dataset_path = Path("golden_dataset.json")
    if dataset_path.exists():
        count = len(json.loads(dataset_path.read_text()).get("test_cases", []))
        rows.append([ok_mark, "Golden dataset", f"{count} question(s) saved"])
    else:
        rows.append([pending_mark, "Golden dataset", "not built yet — referee dataset new"])

    eval_report = _latest_report("eval_run_*.json")
    if eval_report:
        mark = ok_mark if eval_report["passed"] == eval_report["total_tests"] else fail_mark
        pct = eval_report["pass_rate"] * 100
        rows.append([mark, "Evaluation", f"{eval_report['passed']}/{eval_report['total_tests']} passed ({pct:.0f}%)"])
    else:
        rows.append([pending_mark, "Evaluation", "not run yet — referee eval run"])

    guard_report = _latest_report("guardrails_run_*.json")
    if guard_report:
        mark = ok_mark if guard_report["blocked"] == guard_report["total_attacks"] else fail_mark
        rows.append([mark, "Guardrail attacks", f"{guard_report['blocked']}/{guard_report['total_attacks']} blocked"])
    else:
        rows.append([pending_mark, "Guardrail attacks", "not run yet — referee guardrails test"])

    _draw_table(["", "Step", "Result"], rows)

    click.echo()
    click.echo(
        "  Want the fuller version, side by side with your actual answers? That's what\n"
        "  referee dashboard is for — this table above is the free, no-install summary."
    )
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
