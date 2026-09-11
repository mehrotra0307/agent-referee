from typing import Any

from rouge_score import rouge_scorer

_scorer = rouge_scorer.RougeScorer(["rouge1"], use_stemmer=True)


def check_text_similarity(test_case: dict[str, Any], actual_response: str) -> dict[str, Any]:
    """Score word overlap against test_case["reference_answer"] using ROUGE-1 recall.

    Uses recall rather than the blended F1 score on purpose: F1's precision
    component penalizes a longer but still-correct answer just for adding
    extra words beyond the reference, which is the wrong tradeoff for
    grading a customer-support-style answer.

    Returns:
        {"id": str, "passed": bool, "reason": str}
    """
    reference = test_case["reference_answer"]
    threshold = test_case["similarity_threshold"]

    scores = _scorer.score(reference, actual_response)
    rouge1_recall = scores["rouge1"].recall
    passed = rouge1_recall >= threshold

    return {
        "id": test_case["id"],
        "passed": passed,
        "reason": (
            f"ROUGE-1 recall: {rouge1_recall:.2f} (needed >= {threshold}). "
            "This counts word overlap with the reference answer, not meaning — "
            "a correct answer phrased very differently can still score low."
        ),
    }
