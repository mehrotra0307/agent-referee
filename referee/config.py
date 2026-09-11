from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_REQUIRED_TOP_LEVEL_KEYS = ["agent", "llm_provider"]


class ConfigError(ValueError):
    pass


def load_config(path: str = "referee.yaml") -> dict[str, Any]:
    """Load and validate a referee.yaml file, then load the local .env file
    (via python-dotenv) so API keys read with os.getenv() are available.

    Raises:
        ConfigError: if the file is missing, or missing a required section.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(
            f"No config file found at '{path}'. Run `referee init` first to create one."
        )

    with config_path.open("r") as f:
        config = yaml.safe_load(f) or {}

    for key in _REQUIRED_TOP_LEVEL_KEYS:
        if key not in config:
            raise ConfigError(f"referee.yaml is missing the required '{key}' section.")

    if "name" not in config.get("llm_provider", {}):
        raise ConfigError("referee.yaml's llm_provider section needs a 'name' field.")

    load_dotenv()

    return config


def get_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    """Pull out the llm_provider.* section, passed to referee/providers.py's call_llm()."""
    return config.get("llm_provider", {})
