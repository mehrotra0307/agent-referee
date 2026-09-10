from referee.eval.deterministic import check_deterministic


def test_contains_any_passes_on_match():
    test_case = {"id": "t1", "check": "contains_any", "expected_contains": ["11 PM", "23:00"]}
    result = check_deterministic(test_case, "We close at 11 PM every night.")
    assert result["passed"] is True
    assert result["id"] == "t1"


def test_contains_any_fails_without_match():
    test_case = {"id": "t2", "check": "contains_any", "expected_contains": ["11 PM"]}
    result = check_deterministic(test_case, "We're open all day.")
    assert result["passed"] is False


def test_expected_behavior_refusal_passes():
    test_case = {
        "id": "t3",
        "check": "expected_behavior",
        "expected_behavior": "refusal",
        "refusal_markers": ["cannot help", "can't help"],
    }
    result = check_deterministic(test_case, "I'm sorry, I cannot help with that.")
    assert result["passed"] is True


def test_unknown_check_type_fails_with_explanation():
    test_case = {"id": "t4", "check": "not_a_real_check"}
    result = check_deterministic(test_case, "anything")
    assert result["passed"] is False
    assert "Unknown check type" in result["reason"]
