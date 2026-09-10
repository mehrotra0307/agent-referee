# Your first dataset

A golden dataset is just a list of questions your agent might get, and what a correct answer
should mention. This doc walks through building one for a small pizza-shop support agent, using
`referee dataset new` — the same wizard you'll use for your own agent, whatever it does.

## Running the wizard

```bash
referee dataset new
```

It's fully offline. No API key, no network call, nothing sent anywhere — it just asks questions
and writes a JSON file.

```
A golden dataset is just a list of questions your agent might get, and what a
correct answer should mention. `referee eval run` uses it to check your agent's
real answers automatically, so you don't have to read every response yourself.

This wizard runs fully offline — no API key, no network call, nothing sent
anywhere. Let's build yours, one question at a time.

Question #1 a user might ask your agent (Enter to finish): What time do you close?
What must a correct answer mention? (comma-separated phrases): 11 PM, 11:00 PM
Category (a short label to group this test case) [general]: hours

Question #2 a user might ask your agent (Enter to finish): Can I get a refund?
What must a correct answer mention? (comma-separated phrases): 24 hours, damaged
Category (a short label to group this test case) [general]: refund_policy

Question #3 a user might ask your agent (Enter to finish):

Wrote 2 test case(s) to golden_dataset.json. Run `referee eval run` next.
```

## What that produced

```json
{
  "dataset_version": "v1",
  "description": "Golden dataset, built with `referee dataset new`.",
  "test_cases": [
    {
      "id": "eval_001",
      "category": "hours",
      "input": "What time do you close?",
      "eval_type": "deterministic",
      "check": "contains_any",
      "expected_contains": ["11 PM", "11:00 PM"],
      "severity": "medium"
    },
    {
      "id": "eval_002",
      "category": "refund_policy",
      "input": "Can I get a refund?",
      "eval_type": "deterministic",
      "check": "contains_any",
      "expected_contains": ["24 hours", "damaged"],
      "severity": "medium"
    }
  ]
}
```

Run `referee eval run` and each of these becomes one test: call the agent with `input`, check
whether the real response contains any of `expected_contains`, report pass or fail with a plain
English reason either way.

## Beyond the wizard: the other 3 automated eval types

The wizard always writes `"eval_type": "deterministic"` — exact phrase matching, the simplest
and most predictable option, and the right default for a first dataset. Once you're comfortable,
you can hand-edit `golden_dataset.json` to use any of these instead, for cases where exact
phrase-matching is too brittle:

- **`text_similarity`** — scores word overlap (ROUGE) against a `reference_answer`, instead of
  requiring an exact phrase. Good for answers that can be phrased several correct ways but should
  still share most of the same words.
- **`embedding_similarity`** — scores *meaning* overlap against a `reference_answer`, catching a
  correct answer phrased completely differently (needs `pip install agent-referee[embedding]`).
- **`llm_judge`** — a second LLM call grades the real answer against a written `rubric`, 1 to 5.
  The most flexible option, and the one that costs an API call per test case.

See `referee/eval/example_dataset.json` (installed alongside the package, read-only) for one
worked example of each type — `referee dataset new` prints its exact path when it starts.

## A word on deterministic checks

Deterministic (exact-phrase) checks are fast and free, but brittle: if your agent says "we do
not allow substitutions" and your dataset only checks for the phrase "no substitutions," that's
a false negative — a genuinely correct answer scored as wrong, just because the wording didn't
match. If you see failures like that, it's usually a sign to either widen `expected_contains` to
include the alternate phrasing, or switch that test case to `text_similarity` or
`embedding_similarity` instead.
