import pytest
import yaml

from referee.config import ConfigError, get_provider_config, load_config


def _write_config(tmp_path, content: dict):
    path = tmp_path / "referee.yaml"
    path.write_text(yaml.dump(content))
    return str(path)


def test_missing_file_raises_config_error():
    with pytest.raises(ConfigError, match="referee init"):
        load_config("/nonexistent/referee.yaml")


def test_missing_required_section_raises(tmp_path):
    path = _write_config(tmp_path, {"agent": {"name": "x"}})
    with pytest.raises(ConfigError, match="llm_provider"):
        load_config(path)


def test_missing_provider_name_raises(tmp_path):
    path = _write_config(tmp_path, {"agent": {"name": "x"}, "llm_provider": {}})
    with pytest.raises(ConfigError, match="name"):
        load_config(path)


def test_valid_config_loads(tmp_path):
    path = _write_config(
        tmp_path, {"agent": {"name": "x"}, "llm_provider": {"name": "gemini"}}
    )
    config = load_config(path)
    assert get_provider_config(config) == {"name": "gemini"}
