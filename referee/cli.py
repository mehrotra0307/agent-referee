import json
import logging
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

# Separate mechanism, same goal: google-genai logs a WARNING (via Python's
# logging module, not warnings.warn()) every time Gemini's response includes
# a "thought_signature" part alongside text, which is normal and expected
# whenever a model does any internal reasoning. It has nothing to do with
# anything going wrong, but it prints straight into the middle of a live
# trace and drowns it out. Raised only this one logger's threshold, nothing
# else is touched.
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

from referee.config import get_provider_config, load_config
from referee.entry_point import load_entry_point
from referee.eval.deterministic import check_deterministic
from referee.eval.runner import run_evaluation
from referee.guardrails.input_validation import check_injection, check_pii
from referee.guardrails.scope_check import check_scope
from referee.guardrails.test_suite import ADVERSARIAL_TEST_CASES
from referee.init_project import init_project
from referee.protect import protect
from referee.ui import callout, divider, example, next_steps, pause, phase, status_table, type_out

_PROVIDERS = ["gemini", "openai", "anthropic"]
_EXAMPLE_DATASET_URL = "https://github.com/mehrotra0307/agent-referee/blob/main/referee/eval/example_dataset.json"

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

There are 5 real ways to score an answer, and different tools use different
ones:
  · Deterministic     — exact phrase / refusal-marker matching. Free, instant.
  · ROUGE             — word-overlap scoring against a reference answer.
  · Embedding          — meaning-overlap scoring (catches different wording).
  · LLM-as-judge       — a second AI call grades the first one's answer.
  · Human review       — a person reads real conversations by hand.

Your dataset uses deterministic, the simplest and most predictable one,
because that's what `referee dataset new` always writes. Here's exactly what
that means for every question below: your real agent gets called with the
exact question, and it PASSES if its real answer contains any one of the
phrases you said a correct answer must mention, and FAILS if it doesn't.
That's the whole rule, no AI judging another AI here.
"""

_GUARDRAILS_TEST_INTRO = """
A guardrail is a bouncer, not a grader. It doesn't care if an answer is good —
it cares whether a message is safe enough to let through at all. You did not
have to configure any of this by hand: the moment you added the one decorator
earlier, sensible guardrail defaults switched on automatically. Nothing to
build, nothing to turn on separately.

There are 5 real kinds of guardrail. This library ships all 5, on by default:
  · PII detection      — regex, catches emails/phones/card numbers. Free.
  · Injection detection — regex, catches known jailbreak phrasing. Free.
  · Rate limiting       — a counter, caps messages per session. Free.
  · Scope / topic check — an AI call, catches off-topic questions.
  · Toxicity / groundedness — an AI call, catches unsafe or made-up answers.

Exactly what this command does, mechanically, so none of it is a mystery:

  It does NOT call your agent function at all. Not once. Guardrails are
  meant to catch a bad message BEFORE it ever reaches your agent, so testing
  them means testing whether a specific message gets caught, which doesn't
  need your agent involved.

  Instead, it has 8 pre-written attack strings built into this library (not
  yours, not generated, always the same 8), and sends each one DIRECTLY to
  the guardrail-checking code itself:
    · The 3 PII and 3 injection attacks each run through a plain regex
      pattern match against that exact string. No network call at all.
    · The 2 scope attacks (only if you've turned scope-check on) each
      trigger one real API call: your agent's topic description plus the
      attack string get sent to your configured AI provider, asking "is
      this on-topic or not."

  PASS means the guardrail correctly said "block this." FAIL means it let
  the string through untouched. Only 3 of the 5 kinds above actually get
  tested here, on purpose: rate limiting needs real repeated traffic to
  mean anything, not one string, and toxicity/groundedness only ever checks
  what your agent SAYS back, not what comes in, so there's no single
  "attack string" version of it the same way.

Bottom line, whether you've built your own guardrails before or never heard
the word until today: this checks the guardrail logic itself is working,
using fixed test inputs, with zero involvement from your actual agent code.
"""


def _require_nonblank(value: str) -> str:
    """click.prompt's value_proc for a field that would silently create a
    broken, always-failing test case if left blank or whitespace-only.
    click.prompt() already re-asks on a truly empty answer by itself, but
    only checks for the exact empty string — this also catches
    whitespace-only input, and gives a reason instead of just re-asking
    silently."""
    if not value.strip():
        raise click.UsageError("Can't be blank — this is what actually gets checked. Type at least one word or phrase.")
    return value


@click.group()
@click.version_option()
def main():
    """Agent Referee — evaluation, guardrails, and observability for any AI agent."""


_PROVIDER_CHOICES = ["gemini", "openai", "anthropic", "none"]

_NO_KEY_YET_MESSAGE = (
    "\nTotally fine, most people start here. Fastest free option: go to "
    "https://aistudio.google.com, sign in with any Google account, and click "
    "\"Get API key.\" No credit card, no waiting. Once you've got a key for one of\n"
    "the three above (or decide you'd rather use OpenAI or Anthropic), come back "
    "and answer again.\n"
)


def _ask_entry_point() -> str:
    divider("QUESTION 1 of 3 — Where does your agent live?")
    click.echo(
        "However you built your agent, a plain API call, CrewAI, LangGraph, Google's ADK,\n"
        "or anything else, somewhere in your code there is exactly ONE function that takes a\n"
        "question in (as a string) and hands an answer back out (also a string). We're not\n"
        "asking about your whole project, just that one function: which file it's in, and\n"
        "what it's called.\n"
    )
    click.echo(
        "Format:  path/to/file.py:function_name\n"
        "         (the part before the colon is the file, the part after is the function)\n"
    )
    click.echo(
        "Example: say you have a file called my_agent.py, sitting right here in this same\n"
        "folder, and inside it there's a function called ask. You'd type exactly this:\n\n"
        "    my_agent.py:ask\n"
    )

    while True:
        entry_point = click.prompt("Your answer")
        file_part = entry_point.split(":", 1)[0] if ":" in entry_point else entry_point
        if ":" not in entry_point:
            click.echo(
                f"\nThat's missing the ':function_name' part — we got '{entry_point}' but need "
                "something like my_agent.py:ask. Try again.\n"
            )
            continue
        if not Path(file_part).exists():
            click.echo(
                f"\nCan't find a file at '{file_part}' from here. Typo, or is it in a different "
                "folder? Try again (or Ctrl+C to quit and double check).\n"
            )
            continue
        return entry_point


def _ask_description() -> str:
    divider("QUESTION 2 of 3 — What is your agent allowed to talk about?")
    click.echo(
        "Picture a small pizza shop's support bot. Its whole job is menu, hours, and\n"
        "delivery questions, nothing else. If a customer asked it \"should I file my taxes as\n"
        "self-employed?\", that's wildly outside its job, and this question is exactly how we\n"
        "teach Agent Referee to recognize and block things like that for YOUR agent.\n"
    )
    click.echo(
        "So: one sentence, plain English, describing what your agent's job actually is.\n"
        "For that pizza shop example above, the literal answer would be:\n\n"
        "    Only answer questions about a pizza shop's menu, hours, and delivery\n"
    )
    return click.prompt("Your answer")


def _ask_provider() -> str:
    divider("QUESTION 3 of 3 — Which AI company's API do you use?")
    click.echo(
        click.style("Before anything else: ", bold=True)
        + "this question wants a COMPANY NAME, not a password. Nobody here is fishing "
        "for your key, we promise, we don't even have a form to put it in.\n"
    )
    click.echo("Pick whichever matches an API key you already have, or plan to get:\n")
    click.echo("  gemini      Google's models (what powers Gemini / Google AI Studio)")
    click.echo("  openai      the company behind ChatGPT")
    click.echo("  anthropic   the company behind Claude")
    click.echo("  none        I don't have any of these yet\n")

    provider = click.prompt("Your answer", type=click.Choice(_PROVIDER_CHOICES, case_sensitive=False)).lower()
    while provider == "none":
        click.echo(_NO_KEY_YET_MESSAGE)
        provider = click.prompt("Your answer", type=click.Choice(_PROVIDER_CHOICES, case_sensitive=False)).lower()
    return provider


@main.command()
@click.option("--entry-point", default=None, help="Skip the interactive question with this value.")
@click.option("--description", default=None, help="Skip the interactive question with this value.")
@click.option("--provider", default=None, type=click.Choice(_PROVIDERS, case_sensitive=False), help="Skip the interactive question with this value.")
def init(entry_point: str, description: str, provider: str):
    """Scaffold referee.yaml for this project. Never asks for an API key."""
    click.echo("\nLet's get your agent connected. Three quick questions, no API key involved, ever.")

    if entry_point is None:
        entry_point = _ask_entry_point()
    if description is None:
        description = _ask_description()
    if provider is None:
        provider = _ask_provider()
    else:
        provider = provider.lower()

    init_project(entry_point=entry_point, description=description, provider=provider)


@main.group(name="dataset")
def dataset_group():
    """Manage your golden evaluation dataset."""


@dataset_group.command(name="new")
@click.option("--output", default="golden_dataset.json", show_default=True)
def dataset_new(output: str):
    """Build a golden dataset interactively. Fully offline — no API key needed."""
    phase(
        "STARTING: EVALUATION",
        "You've already got guardrails and tracing running on every real call, from the\n"
        "decorator you added earlier. Evaluation is the third piece: grading your\n"
        "agent's answers after the fact, like a report card, instead of blocking\n"
        "anything live.\n\n"
        "It's two steps. First, right here, you build a golden dataset: a list of\n"
        "questions your agent might get, and what a correct answer should mention.\n"
        "Second, once that's saved, `referee eval run` asks your agent every one of\n"
        "those questions and grades each real answer against what you wrote.\n\n"
        "Let's build the dataset first.",
    )

    click.echo(_DATASET_INTRO)

    click.echo(
        f"Want more ideas before you start? A read-only sample dataset, covering every\n"
        f"question type this tool supports, is on GitHub here:\n  {_EXAMPLE_DATASET_URL}\n"
    )

    example(
        "imagine your agent runs a pizza shop",
        {
            "Question a user might ask": "What time do you close?",
            "What a correct answer must mention": "11 PM",
            "Category": "hours",
        },
    )

    click.echo(
        "That's it, that's the whole shape. Below, you'll be asked those same three\n"
        "things, once per question, as many times as you want. When you're done, either\n"
        "press Enter on a blank question, or type exit (or quit) as your answer, either\n"
        "one stops the wizard the same way — nothing typed after that point gets used.\n"
    )

    entries = []
    counter = 1
    while True:
        divider(f"Test case #{counter}", color="cyan")
        question = click.prompt(
            "Question a user might ask your agent (blank, or type exit, to finish)",
            default="",
            show_default=False,
        )
        if not question or question.strip().lower() in ("exit", "quit", "q", "cancel", "stop"):
            break

        must_mention = click.prompt(
            "What must a correct answer mention? (comma-separated phrases)",
            value_proc=_require_nonblank,
        )

        click.echo(
            "\nCategory is just a label for grouping related questions later, it doesn't\n"
            "affect scoring at all. Reuse the same word across multiple questions on\n"
            "purpose, e.g. \"hours\" for every hours-related question.\n"
        )
        category = click.prompt("Category", default="general")

        expected_contains = [phrase.strip() for phrase in must_mention.split(",") if phrase.strip()]
        click.echo(
            f"\n  Question:              {question}\n"
            f"  Must mention one of:   {expected_contains}\n"
            f"  Category:              {category}\n"
        )
        if not click.confirm("Add this test case?", default=True):
            click.echo("Discarded — let's redo this one.")
            continue

        entries.append(
            {
                "id": f"eval_{counter:03d}",
                "category": category,
                "input": question,
                "eval_type": "deterministic",
                "check": "contains_any",
                "expected_contains": expected_contains,
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
    output_path = Path(output).resolve()
    Path(output).write_text(json.dumps(dataset, indent=2) + "\n")

    callout(
        "SAVED",
        f"{len(entries)} test case(s) written to:\n{output_path}\n\n"
        "It's a plain text file, open it anytime in a text editor or your file browser\n"
        "to see exactly what's in it — nothing hidden, nothing binary.",
        color="green",
    )

    first = entries[0]
    divider("Understanding the file you just created", color="yellow")
    click.echo("Nothing here is private or hidden from you, so here's exactly what each field means,")
    click.echo("using your own first question as the real example:\n")
    click.echo(f'  "id": "{first["id"]}"')
    click.echo("      A stable name for this one test. Survives you editing the question later.\n")
    click.echo(f'  "category": "{first["category"]}"')
    click.echo("      The label you gave. Purely for grouping results, doesn't affect scoring.\n")
    click.echo(f'  "input": "{first["input"]}"')
    click.echo("      The exact question, word for word, that will get sent to your agent.\n")
    click.echo(f'  "eval_type": "{first["eval_type"]}"')
    click.echo("      Which of Agent Referee's 5 scoring methods grades this question. This\n"
                "      wizard always picks \"deterministic\" (exact-phrase matching), the simplest\n"
                "      and most predictable one.\n")
    click.echo(f'  "check": "{first["check"]}"')
    click.echo("      The specific rule: pass if the real answer contains ANY ONE of the phrases\n"
                "      below, not all of them.\n")
    click.echo(f'  "expected_contains": {first["expected_contains"]}')
    click.echo("      The phrase(s) you said a correct answer must mention.\n")
    click.echo(f'  "severity": "{first["severity"]}"')
    click.echo("      How serious a failure here is. This wizard always writes \"medium\" — hand-edit\n"
                "      the file later to mark anything as \"critical\" (referee eval run treats\n"
                "      critical failures as build-blocking) or \"low\".\n")
    click.echo(f"Open {output_path} yourself any time — it's exactly this shape, once per question.\n")

    next_steps(
        (
            None,
            "This file is the foundation of your whole evaluation setup. Every question\n"
            "in it, and what you said a correct answer must mention, is what the next\n"
            "command grades your real agent against.",
        ),
        (
            "referee eval run",
            "This is evaluation: your agent gets asked every question above, its real\n"
            "answer gets checked against what you said a correct one should mention,\n"
            "and each one gets graded pass or fail with a plain-English reason. Run it\n"
            "any time you change your agent's code or prompt, to catch a regression\n"
            "before a real user does.",
        ),
    )


@main.command(name="try")
@click.argument("question")
@click.option("--config", default="referee.yaml", show_default=True)
def try_once(question: str, config: str):
    """Call your real agent once with QUESTION and print what comes back.

    This is the quickest way to check the decorator is actually wired up:
    it loads your agent from referee.yaml's entry_point (whatever framework
    it's built with) and calls it exactly once, right here in this
    terminal. If you see guardrail and trace lines printed above the
    answer, it's working.
    """
    cfg = load_config(config)
    agent_fn = load_entry_point(cfg["agent"]["entry_point"])

    click.echo(f"\nCalling your agent with: {question!r}")
    divider("LIVE TRACE — printed as it happens, below", color="yellow")
    response = agent_fn(question)
    callout("AGENT'S ANSWER", response, color="green")

    next_steps(
        (None, "Saw guardrail and trace lines above, and a real answer in the box?\nThat means your setup is wired up correctly."),
        (
            "referee dataset new",
            "Walks you through a few questions about your agent (what might someone\n"
            "ask, what should a correct answer mention) and saves YOUR OWN answers as\n"
            "a test file. Nothing here is auto-generated, and no API key is needed for\n"
            "this step. This is what lets referee eval run (later) grade your agent\n"
            "automatically instead of you reading every answer by hand.",
        ),
    )


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

    click.echo(f"Running evaluation for '{agent_cfg['name']}' against {dataset_path}...")
    divider("RESULTS — one line per test case", color="cyan")

    report = run_evaluation(dataset_path, agent_fn, provider_config, datetime.now().isoformat())

    for result in report["results"]:
        passed = result["passed"]
        status = click.style("PASS", fg="green", bold=True) if passed else click.style("FAIL", fg="red", bold=True)
        click.echo(f"[{status}] {result['id']} ({result['category']}, severity={result['severity']})")
        click.echo(f"       {result['reason']}")

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_path = reports_dir / f"eval_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    summary_color = "red" if report["critical_failures"] > 0 else "green"
    callout(
        "SUMMARY",
        f"Passed: {report['passed']}/{report['total_tests']} ({report['pass_rate'] * 100:.0f}%)\n"
        f"Critical failures: {report['critical_failures']}\n"
        f"Full report saved to: {report_path}",
        color=summary_color,
    )

    if report["critical_failures"] > 0:
        click.echo(click.style("BLOCKING: critical-severity test failure(s) detected.", fg="red", bold=True))
        raise SystemExit(1)

    next_steps(
        (
            "referee guardrails test",
            "Same idea as this command, but for safety instead of quality. A guardrail\n"
            "is a live check that blocks a risky message before it does damage, not a\n"
            "grade after the fact. You didn't configure any yourself, sensible defaults\n"
            "switched on automatically the moment you added the one decorator earlier.\n"
            "This command does NOT call your agent: it sends 8 fixed attack strings,\n"
            "built into this library, directly to the guardrail-checking code itself\n"
            "(mostly plain regex, one type makes a real API call), and reports which\n"
            "ones got correctly blocked.",
        ),
    )


@main.group(name="guardrails")
def guardrails_group():
    """Test your agent's guardrails (on by default) against packaged adversarial attacks."""


@guardrails_group.command(name="test")
@click.option("--config", default="referee.yaml", show_default=True)
@click.option(
    "--local-only",
    is_flag=True,
    help="Skip the scope-check attack, which makes a real LLM call using your configured key.",
)
def guardrails_test(config: str, local_only: bool):
    """Run packaged adversarial attacks against your agent's guardrails."""
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

    divider("ATTACKS — one line per attempt", color="cyan")

    blocked_count = 0
    total = 0
    case_results = []

    for case in ADVERSARIAL_TEST_CASES:
        check_type = case["check"]

        if check_type == "scope" and (local_only or not scope_cfg.get("enabled")):
            click.echo(click.style("[SKIP] ", dim=True) + f"{case['id']} ({case['category']}) — scope_check disabled or --local-only set")
            continue

        if check_type == "pii":
            result = check_pii(case["input"])
            how = "free, local regex check — no API call, your key was never touched"
        elif check_type == "injection":
            result = check_injection(case["input"])
            how = "free, local regex check — no API call, your key was never touched"
        else:
            result = check_scope(case["input"], scope_cfg.get("description", ""), provider_config)
            how = f"real API call to {provider_config.get('name', 'your provider')}, using your configured key"

        total += 1
        blocked = not result["allowed"]
        if blocked:
            blocked_count += 1

        status = click.style("PASS", fg="green", bold=True) if blocked else click.style("FAIL", fg="red", bold=True)
        click.echo(f"[{status}] {case['id']} ({case['category']})")
        click.echo(f"       Attack simulated: {case['attack_description']}")
        click.echo(click.style(f"       How it was checked: {how}", dim=True))
        if not blocked:
            click.echo(click.style("       This guardrail let the attack through — it was not caught.", fg="red"))

        case_results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "attack_description": case["attack_description"],
                "blocked": blocked,
            }
        )

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

    all_blocked = blocked_count == total
    callout(
        "SUMMARY",
        f"Blocked {blocked_count}/{total} adversarial attacks.\n"
        f"Full report saved to: {report_path}",
        color="green" if all_blocked else "red",
    )

    if all_blocked:
        phase(
            "YOU'RE SET UP",
            "Quick recap of what's actually running on your agent now:\n\n"
            "  1. Guardrails + tracing — one decorator, automatic on every real call.\n"
            "  2. A golden dataset — your own questions, saved as a plain JSON file.\n"
            "  3. Evaluation — referee eval run grades real answers against it.\n"
            "  4. Guardrail testing — real attacks, just confirmed they get blocked.\n\n"
            "That's real evaluation, real guardrails, and real observability, running on\n"
            "your own agent, with your own key, on your own machine. Nothing hosted by\n"
            "anyone else at any point.",
            color="green",
        )
    else:
        phase(
            "SOME ATTACKS GOT THROUGH — here's what that means",
            "This is real, useful signal, not a bug in this library: one or more of your\n"
            "guardrails didn't catch an attack it should have. Most likely cause if it's\n"
            "the scope check specifically: the description you gave in referee.yaml\n"
            "(guardrails.input.scope_check.description) is a bit loose, or the AI call\n"
            "judged that particular message differently than you expected.\n\n"
            "Two real options, neither is required right now:\n"
            "  1. Tighten that description in referee.yaml, then run this command again.\n"
            "  2. Note it and move on — everything below still works either way.",
            color="red",
        )

    status_table()

    click.echo(click.style("═" * 58, dim=True))
    click.echo(
        click.style("  ALL MANDATORY STEPS ARE DONE", bold=True, fg="green" if all_blocked else "yellow")
    )
    click.echo(click.style("═" * 58, dim=True))
    click.echo()
    click.echo(
        "That's the whole guided flow, start to finish. Nothing else is required.\n"
        "Everything from here is optional:"
    )

    next_steps(
        (
            'pip install "agent-referee[dashboard]"',
            "Optional, one-time, ~180MB (mostly Streamlit's own dependencies). Adds a\n"
            "local webpage on your own machine showing both reports side by side, with\n"
            "your agent's actual answers visible too, not just pass/fail counts.",
        ),
        (
            "referee dashboard",
            "Run this after the install above, whenever you want the fuller view. It\n"
            "starts a local web server and opens your browser to it automatically — no\n"
            "account, nothing sent anywhere, closing the terminal shuts it down.",
        ),
    )

    if not all_blocked:
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
    next_steps(("referee init", "Wire this into your real agent — three quick questions, no API key."))


def _suppress_streamlit_onboarding_prompt() -> None:
    """Streamlit itself, completely separately from anything this library
    does, asks for an email address the very first time it ever runs on a
    machine ("Welcome to Streamlit!"). That directly contradicts this
    project's own never-ask-for-anything promise, even though it's
    Streamlit's own onboarding flow, not ours. Pre-creating its credentials
    file with a blank email is Streamlit's own documented way to skip that
    prompt entirely — verified this actually suppresses it, not just
    assumed. Never overwrites a real credentials file if one exists.
    """
    credentials_path = Path.home() / ".streamlit" / "credentials.toml"
    if credentials_path.exists():
        return
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text('[general]\nemail = ""\n')


@main.command()
def dashboard():
    """Launch the local Streamlit dashboard (reads local reports/, nothing hosted by us)."""
    app_path = Path(__file__).parent / "dashboard" / "app.py"

    try:
        import streamlit  # noqa: F401
    except ImportError:
        click.echo(
            "The dashboard needs Streamlit, which isn't installed by default. Install it with:\n\n"
            '    pip install "agent-referee[dashboard]"\n'
        )
        raise SystemExit(1)

    _suppress_streamlit_onboarding_prompt()
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])
