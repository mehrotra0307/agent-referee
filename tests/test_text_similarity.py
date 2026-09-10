from referee.eval.text_similarity import check_text_similarity


def test_high_overlap_passes():
    test_case = {
        "id": "t1",
        "reference_answer": "We do not allow topping substitutions on online orders.",
        "similarity_threshold": 0.4,
    }
    response = "That's correct, we do not allow topping substitutions on online orders."
    result = check_text_similarity(test_case, response)
    assert result["passed"] is True


def test_low_overlap_fails():
    test_case = {
        "id": "t2",
        "reference_answer": "We do not allow topping substitutions on online orders.",
        "similarity_threshold": 0.8,
    }
    response = "Sure, no problem, I'll add that for you right away!"
    result = check_text_similarity(test_case, response)
    assert result["passed"] is False


def test_reason_uses_recall_not_fmeasure_language():
    test_case = {"id": "t3", "reference_answer": "hello world", "similarity_threshold": 0.1}
    result = check_text_similarity(test_case, "hello world")
    assert "recall" in result["reason"].lower()
