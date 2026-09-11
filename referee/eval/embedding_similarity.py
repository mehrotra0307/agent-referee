from typing import Any

_model = None
_util = None


def _get_model_and_util():
    """Lazily import and cache sentence-transformers, so the base package
    never pays its import cost unless this evaluator actually runs."""
    global _model, _util
    if _model is not None:
        return _model, _util

    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError as exc:
        raise ImportError(
            "Embedding-similarity scoring needs sentence-transformers, which isn't "
            "installed by default (it pulls in PyTorch, ~500MB+, and most projects "
            "never use this evaluator). Install it with:\n\n"
            "    pip install agent-referee[embedding]\n"
        ) from exc

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _util = util
    return _model, _util


def check_embedding_similarity(test_case: dict[str, Any], actual_response: str) -> dict[str, Any]:
    """Score meaning overlap against test_case["reference_answer"] via cosine
    similarity between sentence embeddings (model: all-MiniLM-L6-v2, local,
    no API call). Requires the 'embedding' extra.

    Returns:
        {"id": str, "passed": bool, "reason": str}
    """
    reference = test_case["reference_answer"]
    threshold = test_case["similarity_threshold"]

    model, util = _get_model_and_util()
    embeddings = model.encode([reference, actual_response])
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
    passed = similarity >= threshold

    return {
        "id": test_case["id"],
        "passed": passed,
        "reason": (
            f"Embedding similarity: {similarity:.2f} (needed >= {threshold}). "
            "This compares meaning, not exact words — it can catch a correct answer "
            "phrased completely differently from the reference."
        ),
    }
