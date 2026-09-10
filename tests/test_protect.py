import yaml

import referee
from referee.guardrails.input_validation import reset_rate_limits
from referee.observe.tracing import reset_tracer


def _write_minimal_config(tmp_path, guardrails=None):
    config = {
        "agent": {"name": "test-agent", "entry_point": "agent.py:ask"},
        "llm_provider": {"name": "gemini"},
        "guardrails": guardrails
        or {
            "input": {"pii_check": True, "injection_check": True},
            "output": {"pii_check": True, "toxicity_and_groundedness_check": False},
        },
        "observe": {"exporter": "console"},
    }
    path = tmp_path / "referee.yaml"
    path.write_text(yaml.dump(config))
    return str(path)


def setup_function():
    reset_rate_limits()
    reset_tracer()


def test_protect_passes_through_clean_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_minimal_config(tmp_path)

    @referee.protect(config=config_path)
    def agent(user_input: str) -> str:
        return f"echo: {user_input}"

    result = agent("what time do you close?")
    assert result == "echo: what time do you close?"


def test_protect_blocks_pii_before_calling_agent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_minimal_config(tmp_path)
    calls = []

    @referee.protect(config=config_path)
    def agent(user_input: str) -> str:
        calls.append(user_input)
        return "should never get here"

    result = agent("my email is test@example.com")
    assert "can't help" in result
    assert calls == [], "the wrapped agent function must not run when input is blocked"


def test_protect_blocks_pii_leaking_in_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = _write_minimal_config(tmp_path)

    @referee.protect(config=config_path)
    def agent(user_input: str) -> str:
        return "sure, reach us at contact@example.com"

    result = agent("what's your contact info?")
    assert "can't share" in result
