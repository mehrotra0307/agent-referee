# How it works

This doc is for someone who has never heard the words "evaluation," "guardrails," or
"observability" applied to an AI agent before. If you already know this stuff, skip straight to
the [README quickstart](../README.md).

## The three pillars, in plain English

Agent Referee does three genuinely different jobs. It is worth understanding why they are kept
separate, because mixing them up is the most common confusion for anyone new to this.

### 1. Evaluation, the security camera reviewing yesterday's footage

Evaluation checks quality **after the fact, offline**. You write down a list of questions and
what a correct answer should look like. That list is called a *golden dataset*. Then you run
your agent against every question and check its real answers against your list, and count how
many it got right. Everything else, like ROUGE scoring, embedding similarity, or an LLM grading
another LLM's answer, is just making that same checking process faster and more automatic, so a
human does not have to read every single answer forever.

This is what `referee eval run` does.

### 2. Guardrails, the bouncer at the door

Guardrails are different. They make an allow or block decision **live, in real time**, before
something bad can actually happen. A guardrail does not care whether an answer is *good*. It
only cares whether a message is *safe and on topic* enough to let through at all.

Agent Referee runs guardrails in layers, cheapest first, so an obviously bad message never
triggers an expensive one:

1. **Rate limit.** A plain counter, no AI involved, practically free.
2. **PII check.** Regex pattern matching, no API call.
3. **Injection check.** Regex pattern match against known jailbreak phrasing, no API call.
4. **Scope check.** The one check that makes a real LLM call, and it only runs if the first
   three did not already block the message.

Output guardrails run the same idea in reverse, checking what your agent is about to say before
the user sees it. Does it leak personal information, does it sound toxic, does it contradict
what it is supposed to know.

This is what `@referee.protect()` and `referee guardrails test` do.

### 3. Observability, the flight recorder

Observability does not change your agent's behavior at all. It just records what actually
happened, in detail, so a human can debug or monitor it later. Every step of a request, each
guardrail check and your agent's own call, gets wrapped in something called a **span**, which is
a timed record with a unique ID. Nesting spans inside each other builds a small tree showing
exactly what happened and how long each step took.

A common way people remember the difference between the three signals that make up
observability is this: **metrics tell you WHAT changed, traces tell you WHERE, logs tell you
WHY.** Agent Referee focuses on traces, the "where," because that is what actually shows you the
shape of one request through your agent.

This is what `@referee.protect()` wires in automatically, printed as console output by default.

## Why these are three separate things, not one

It is tempting to think "just check if the answer is good" covers everything. It does not,
because each pillar answers a question the other two cannot:

| Question | Answered by |
|---|---|
| "Is my agent's answer quality holding up over time?" | Evaluation |
| "Did this specific message need to be blocked right now?" | Guardrails |
| "What actually happened during this one request, step by step?" | Observability |

A guardrail cannot tell you if an *allowed* answer was any good. An evaluator cannot stop a bad
message from reaching your agent in the first place, it only checks after the fact. And neither
one tells you *why* a particular call took 40 seconds instead of 4.

## The order of operations inside `@referee.protect()`

```
1. Start a trace span for this request.
2. Run input guardrails, in order: rate limit, then PII, then injection, then scope check.
   If any of them block, stop here. Your agent function never runs.
3. Call your agent function.
4. Run output guardrails: PII leak check, then toxicity and groundedness check.
   If they block, the response is replaced with a block message.
5. End the span.
```

Every step above gets its own nested span, so a trace of one request shows you exactly where
time was spent, and exactly which check, if any, made the call to block it.

## A note on the one guardrail that doesn't fit the decorator

Execution layer guardrails, meaning blocking a specific *tool call* before it runs, like
rejecting an order for an invalid pizza size, have to intercept something happening *inside*
your agent's own tool calling loop, not at the boundary of your top level function. A decorator
wrapped around `my_agent(user_input: str) -> str` structurally cannot see into that loop. This
is the one deliberate exception to "just a decorator." See the README's
[one place you still write a little code by hand](../README.md#the-one-place-you-still-write-a-little-code-by-hand)
section for the one line fix.

## Where to go next

- [docs/your-first-dataset.md](your-first-dataset.md), build a real golden dataset with
  `referee dataset new`.
- The [examples/](../examples/) directory, four complete, runnable integrations across
  different frameworks.
