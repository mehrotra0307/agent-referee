from typing import Any


def check_deterministic(test_case: dict[str, Any], actual_response: str) -> dict[str, Any]:
    """Score a test case with plain keyword matching, no AI involved.

    Supports two ``test_case["check"]`` modes:
      - "contains_any": passes if actual_response contains any of test_case["expected_contains"].
      - "expected_behavior": currently only "refusal" is supported, passing if
        actual_response contains any of test_case["refusal_markers"].

    Returns:
        {"id": str, "passed": bool, "reason": str}
    """
    actual_lower = actual_response.lower()
    check = test_case["check"]

    if check == "contains_any":
        expected = test_case["expected_contains"]
        passed = any(phrase.lower() in actual_lower for phrase in expected)
        reason = (
            f"Looked for any of {expected} in the response — "
            f"{'found one' if passed else 'found none of them'}."
        )

    elif check == "expected_behavior":
        behavior = test_case["expected_behavior"]
        if behavior == "refusal":
            markers = test_case["refusal_markers"]
            passed = any(marker.lower() in actual_lower for marker in markers)
            reason = (
                f"Looked for a refusal marker like {markers} — "
                f"{'the agent refused' if passed else 'no refusal language found'}."
            )
        else:
            passed = False
            reason = f"Unknown expected_behavior '{behavior}' — check your dataset."

    else:
        passed = False
        reason = f"Unknown check type '{check}' — expected 'contains_any' or 'expected_behavior'."

    return {"id": test_case["id"], "passed": passed, "reason": reason}
