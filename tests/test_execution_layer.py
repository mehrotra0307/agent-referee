from referee.guardrails.execution_layer import check_tool_call, reset_tool_call_counts


def setup_function():
    reset_tool_call_counts()


def test_allows_tool_not_covered_by_config():
    config = {"execution": {}}
    result = check_tool_call("send_email", {}, session_id="s1", config=config)
    assert result["allowed"] is True


def test_blocks_after_call_limit_reached():
    config = {"execution": {"max_calls_per_tool": {"place_order": 1}}}
    first = check_tool_call("place_order", {"size": "medium"}, session_id="s1", config=config)
    second = check_tool_call("place_order", {"size": "medium"}, session_id="s1", config=config)
    assert first["allowed"] is True
    assert second["allowed"] is False


def test_call_limit_is_per_session():
    config = {"execution": {"max_calls_per_tool": {"place_order": 1}}}
    check_tool_call("place_order", {}, session_id="s1", config=config)
    other_session = check_tool_call("place_order", {}, session_id="s2", config=config)
    assert other_session["allowed"] is True


def test_blocks_disallowed_argument_value():
    config = {
        "execution": {
            "allowed_values": {"place_order": {"size": ["small", "medium", "large"]}}
        }
    }
    result = check_tool_call("place_order", {"size": "xl"}, session_id="s1", config=config)
    assert result["allowed"] is False
