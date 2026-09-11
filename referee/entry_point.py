import importlib.util
import sys
from pathlib import Path
from typing import Callable


def load_entry_point(entry_point: str) -> Callable[[str], str]:
    """Resolve a "path/to/file.py:function_name" string (referee.yaml's
    agent.entry_point) into the actual callable, without requiring the
    user's project to be an installed package. Adds the target file's own
    directory to sys.path first, so its own local imports still work.
    """
    if ":" not in entry_point:
        raise ValueError(
            f"entry_point '{entry_point}' isn't in the expected 'path/to/file.py:function_name' shape."
        )

    file_path_str, function_name = entry_point.rsplit(":", 1)
    file_path = Path(file_path_str)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Can't find '{file_path}' — check the entry_point path in referee.yaml is "
            "relative to where you run `referee` from."
        )

    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)

    project_root = str(file_path.resolve().parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    spec.loader.exec_module(module)

    if not hasattr(module, function_name):
        raise AttributeError(
            f"'{file_path}' doesn't define a function called '{function_name}' — "
            "check the entry_point in referee.yaml."
        )

    return getattr(module, function_name)
