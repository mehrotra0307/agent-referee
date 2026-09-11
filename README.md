# Agent Referee

[![CI](https://github.com/mehrotra0307/agent-referee/actions/workflows/ci.yml/badge.svg)](https://github.com/mehrotra0307/agent-referee/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

However you built your agent, and wherever you deployed it, plug it into Agent Referee and in
a few minutes you get real evaluation scoring, real guardrails, and real observability tracing.

It does not matter if you wrote plain Python calling Gemini or OpenAI directly, or if you used
a framework like LangGraph or CrewAI, or if your agent lives on GCP, AWS, or your own laptop.
If your agent is a piece of code that takes a question in and gives an answer back, Agent
Referee can wrap it.

100% free forever. No account. No signup. No credit card. Your API key never touches this tool,
ever, not even once, and we explain exactly why a little further down.

This project is also meant to teach. If you have never worked with agent evaluation,
guardrails, or observability before, and the words themselves sound intimidating, this is a
good place to actually learn them by doing, not just reading about them. Every command explains
what it just did and why, in plain language, right there in your terminal.

![Agent Referee demo](docs/assets/demo.gif)

*(If the GIF above is missing, it just hasn't been generated yet. See
[docs/assets/demo.tape](docs/assets/demo.tape) for the one command that makes it, using the
real `referee demo` command below.)*

## What is Agent Referee, really

Think of it in three simple pieces. Nobody explains these well the first time, so here they are
in plain English.

**Evaluation** is a report card for your agent. You write down some questions your agent might
get asked, and what a good answer should look like. Agent Referee then asks your agent those
questions for you, checks the answers, and tells you what passed and what failed, and why. You
do this after your agent has already answered, like a teacher grading homework.

**Guardrails** are a bouncer standing at the door. Before a risky message ever reaches your
agent, and before your agent's answer ever reaches your user, guardrails check it in real time
and can block it. A guardrail does not care if an answer is a *good* answer. It only cares if a
message is *safe* and *on topic*.

**Observability**, also called tracing, is a flight recorder. It does not change anything your
agent does. It just quietly writes down what happened, step by step, so that later, if something
goes wrong or runs slowly, you can look back and see exactly where the time went and exactly
what happened.

Most people building their first agent have never set up any of these three things. Agent
Referee gives you all three at once, with almost no code, and explains each one to you as it
runs.

## The one promise we will not break

Agent Referee will never ask you to paste an API key anywhere. Not in a terminal prompt, not in
a setup wizard, not in a config file.

The only place your key ever lives is a `.env` file on your own computer, which you create
yourself. Agent Referee reads it the exact same way the official Google, OpenAI, and Anthropic
libraries already do, using a standard function called `os.getenv()`. Your key is never sent to
us, never stored by us, and never seen by us, because there is no "us" in the loop at all. It is
just your computer reading its own file.

A command line tool asking you to type in a secret is one of the oldest tricks in phishing. So
this is not a feature we might relax later if it becomes inconvenient. It is a line we do not
cross, on purpose, by design.

## Try it in 30 seconds, before installing anything for real

```bash
pip install agent-referee
referee demo
```

This runs a tiny built in example agent. No API key, no config file, nothing else to set up.
You will see, in order:

1. A normal question passing straight through your agent, with a full trace printed underneath
   showing every step that happened along the way.
2. A message containing a phone number getting blocked automatically, before your agent even
   sees it.
3. A tiny evaluation, where Agent Referee checks a real answer from the agent against what a
   correct answer needed to mention, and tells you if it passed.

That is the entire pitch of this project, shown to you in under a minute, before you have
touched your own agent at all.

## The full end to end flow, plugging in your real agent

This is the exact order everything happens in, step by step, with no steps skipped.

### Step 1. Install the core package

```bash
pip install agent-referee
```

This install is small and fast on purpose. It does not pull in any heavy machine learning
libraries by default. A few advanced features need extra pieces, and you only install those if
you actually use them. More on that near the bottom of this README.

### Step 2. Run the setup wizard

```bash
referee init
```

It will ask you three plain questions:

- Where does your agent live. This is a file path and a function name, like
  `agent/my_agent.py:ask_my_agent`.
- What is your agent allowed to talk about, in one sentence. This is used later to catch
  questions that are completely off topic.
- Which LLM provider you use, Gemini, OpenAI, or Anthropic. This is only needed for the one or
  two checks that must ask an LLM a question of their own, like "does this answer sound toxic."

It will never ask for a key. When it finishes, it creates a file called `referee.yaml` in your
project, which holds all of this in plain text, safe to commit to git. It also makes sure your
`.env` file is listed in `.gitignore`, so your key can never be committed by accident.

### Step 3. Add your key, locally, yourself

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

Swap the variable name if you picked OpenAI or Anthropic in step 2. This file lives only on your
computer. Agent Referee reads it locally and nothing more.

### Step 4. Wrap your agent with one decorator

This is the only code change you make. Find the function in your own code that takes a
question and returns an answer, and add one line above it.

```python
import referee

@referee.protect(config="referee.yaml")
def my_agent(user_input: str) -> str:
    # everything below this line is your own code, completely unchanged
    ...
```

Here is what that one line quietly does for you, every single time your agent is called, in
this exact order:

1. It starts a trace, which is a timer that records everything that happens next.
2. It runs your input guardrails. If the message looks unsafe, off topic, or like someone is
   trying to jailbreak your agent, it gets blocked right here, and your own function never even
   runs.
3. It calls your actual agent function, completely unchanged.
4. It runs your output guardrails on whatever your agent just said, checking for things like
   leaked personal information.
5. It finishes the trace and hands you back the final answer.

You never write any of that yourself. You do not open a trace, you do not close a trace, you do
not call a guardrail function by hand. One decorator does the whole thing.

The very first time this decorator actually runs, it will print a short, one time explanation
of what a "trace" and a "span" are, so you are not left guessing. It only shows this once.

### Step 5. Build your first golden dataset, fully offline

```bash
referee dataset new
```

This is a simple back and forth wizard, right there in your terminal. It asks you a question a
user might type, and what a correct answer needs to mention, and repeats until you are done.
Nothing here calls an LLM, and no key is needed for this step, on purpose, so that even your very
first dataset costs nothing to build. It writes everything into a file called
`golden_dataset.json`.

There is also a small example dataset shipped with the tool that you can read for ideas. The
wizard tells you exactly where to find it. See
[docs/your-first-dataset.md](docs/your-first-dataset.md) for a full walkthrough.

### Step 6. Score your agent against that dataset

```bash
referee eval run
```

This reads your `referee.yaml`, finds your agent, and asks it every single question in your
dataset. For each one, it checks the real answer against what you said a correct answer needed,
and prints a plain sentence explaining why it passed or failed. At the end it saves a full
report as a JSON file inside a `reports` folder, and if anything marked "critical" failed, it
exits with an error code on purpose, so this same command can block a bad deploy in a CI
pipeline like GitHub Actions.

### Step 7. Attack your own guardrails on purpose

```bash
referee guardrails test
```

This throws a small packaged list of real attack attempts at your configured guardrails, things
like prompt injection phrases and fake email addresses and phone numbers, and tells you whether
each one actually got blocked. Most of these checks are free and run instantly on your own
computer with no internet call at all. If you turned on the "is this on topic" check, one of the
attacks does make a real call using your own key, so add `--local-only` if you want to skip that
and only run the free checks.

### Step 8. Look at everything in one place

```bash
referee dashboard
```

This opens a small dashboard in your browser, running only on your own computer, showing your
latest evaluation report and your latest guardrail test results side by side. Nothing here is
hosted by us. If you have separately connected a real tracing backend like Langfuse, this page
links out to it instead of trying to rebuild it badly.

That is the whole flow, start to finish. Nothing above needs anything beyond your own agent, your
own key in your own `.env` file, and these eight commands, roughly in this order.

## The one place you still write a little code by hand

Almost everything above is fully automatic once the decorator is in place. There is exactly one
exception, and it exists for an honest technical reason, not because we got lazy.

If your agent calls tools, for example a function that actually places an order or sends an
email, Agent Referee cannot see inside that decision from the outside. The decorator only wraps
the outer function, the one that takes a question and returns an answer. It cannot see what
happens in the middle. So if you want to block a specific tool call before it runs, for example
limiting how many orders one session can place, you add one small check right before that tool
actually runs.

```python
from referee.guardrails.execution_layer import check_tool_call

result = check_tool_call(tool_name, tool_args, session_id, config)
if not result["allowed"]:
    return result["reason"]
# only now does your tool actually run
```

That is the only manual wiring in the entire project. Everything else, guardrails and tracing
both, is fully automatic from the one decorator in step 4.

## What it actually contains

- **Evaluation**, with five different ways to score an answer. Exact phrase matching, checking
  for a refusal, word overlap scoring called ROUGE, meaning based scoring using embeddings, and
  a second LLM grading the first one's answer against a rubric you write.
- **Guardrails**, checking for personal information, prompt injection attempts, message rate
  limits, whether a question is on topic, and whether an answer sounds toxic or made something
  up. The cheap, free, instant checks always run before the ones that cost an API call.
- **Observability**, using the same open standard, OpenTelemetry, that Google Cloud and AWS use
  themselves. By default it prints a clean, readable trace straight to your terminal. You can
  also point it at any OpenTelemetry compatible backend if you want a permanent, searchable
  history instead of just console output.

It works with plain Python calling Gemini, OpenAI, or Anthropic directly, and with LangGraph and
CrewAI. All four are in the [examples](examples/) folder as complete, working files, not just
snippets. Agent Referee itself never imports any of those frameworks. It only ever wraps a
plain function, so it will keep working with whatever framework comes along next.

## Optional extras, only install what you use

The base install stays small on purpose. A couple of features need extra libraries, so they are
kept separate and only installed if you ask for them.

```bash
pip install agent-referee[embedding]   # meaning based scoring, needs sentence-transformers
pip install agent-referee[dashboard]   # the local dashboard, needs streamlit
pip install agent-referee[gemini]      # Google's SDK
pip install agent-referee[openai]      # OpenAI's SDK
pip install agent-referee[anthropic]   # Anthropic's SDK
pip install agent-referee[all]         # everything above, all at once
```

You only ever need the one SDK matching whichever provider you picked in `referee init`.

## Want to learn more, slowly

- [docs/how-it-works.md](docs/how-it-works.md), the three pillars explained again, more slowly,
  for someone who has genuinely never heard these words before today.
- [docs/your-first-dataset.md](docs/your-first-dataset.md), a full worked example of building a
  golden dataset by hand, question by question.

## Why this project exists

This started as a small, hand built project, writing every evaluator, every guardrail, and
every trace by hand, on purpose, to actually learn how these three pieces work underneath,
instead of just enabling a checkbox in someone else's dashboard. Agent Referee takes that same
hand built logic and makes it reusable, so that anyone plugging in their own agent gets the same
lesson, taught to them automatically, one command at a time.

## License

MIT. See [LICENSE](LICENSE).
