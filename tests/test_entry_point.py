import pytest

from referee.entry_point import load_entry_point


def test_loads_function_from_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent_file = tmp_path / "my_agent.py"
    agent_file.write_text("def ask(x):\n    return f'hi {x}'\n")

    fn = load_entry_point("my_agent.py:ask")
    assert fn("world") == "hi world"


def test_missing_colon_raises():
    with pytest.raises(ValueError, match="path/to/file.py:function_name"):
        load_entry_point("my_agent.py")


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_entry_point("nonexistent_file.py:ask")


def test_missing_function_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent_file = tmp_path / "my_agent.py"
    agent_file.write_text("def some_other_name(x):\n    return x\n")

    with pytest.raises(AttributeError, match="ask"):
        load_entry_point("my_agent.py:ask")
