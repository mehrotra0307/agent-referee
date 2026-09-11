import json
from typing import Any, Callable

from referee.eval.deterministic import check_deterministic
from referee.eval.embedding_similarity import check_embedding_similarity
from referee.eval.llm_judge import check_llm_judge
from referee.eval.text_similarity import check_text_similarity


def load_dataset(path: str) -> dict[str, Any]:
    """Load a golden dataset JSON file (see docs/your-first-dataset.md for the shape)."""
    with open(path, "r") as f:
        return json.load(f)


def _route(test_case: dict[str, Any], actual_response: str, provider_config: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one test case to the evaluator matching its eval_type field."""
    eval_type = test_case["eval_type"]

    if eval_type == "deterministic":
        return check_deterministic(test_case, actual_response)
    if eval_type == "llm_judge":
        return check_llm_judge(test_case, actual_response, provider_config)
    if eval_type == "text_similarity":
        return check_text_similarity(test_case, actual_response)
    if eval_type == "embedding_similarity":
        return check_embedding_similarity(test_case, actual_response)

    return {
        "id": test_case["id"],
        "passed": False,
        "reason": (
            f"Unknown eval_type '{eval_type}' — expected one of "
            "'deterministic', 'llm_judge', 'text_similarity', 'embedding_similarity'."
        ),
    }


def run_evaluation(
    dataset_path: str,
    agent_fn: Callable[[str], str],
    provider_config: dict[str, Any],
    run_timestamp: str,
) -> dict[str, Any]:
    """Run every test case in dataset_path against agent_fn and build a report.

    A pure function on purpose (no file writes, no printing) so both the CLI
    and tests can call it directly. agent_fn is whatever the entry_point in
    referee.yaml resolves to — it may or may not be wrapped in
    @referee.protect() itself; this runner doesn't care either way.

    Returns:
        A report dict with run_timestamp, dataset_version, total_tests,
        passed, failed, pass_rate, critical_failures, and the full list of
        per-test-case results.
    """
    dataset = load_dataset(dataset_path)
    results = []

    for test_case in dataset["test_cases"]:
        actual_response = agent_fn(test_case["input"])
        result = _route(test_case, actual_response, provider_config)
        result["category"] = test_case["category"]
        result["severity"] = test_case["severity"]
        result["actual_response"] = actual_response
        results.append(result)

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    critical_failures = [r for r in results if not r["passed"] and r["severity"] == "critical"]

    return {
        "run_timestamp": run_timestamp,
        "dataset_version": dataset.get("dataset_version", "unversioned"),
        "total_tests": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": round(passed_count / total, 2) if total else 0.0,
        "critical_failures": len(critical_failures),
        "results": results,
    }
