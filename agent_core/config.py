from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "project.json"
EXAMPLE_CONFIG = ROOT / "configs" / "project.example.json"


def root() -> Path:
    return ROOT


def config_path() -> Path:
    configured = os.environ.get("AGENT_CONFIG")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else ROOT / path
    if DEFAULT_CONFIG.exists():
        return DEFAULT_CONFIG
    return EXAMPLE_CONFIG


def load_config() -> dict[str, Any]:
    path = config_path()
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise TypeError(f"config root must be an object: {path}")
    return interpolate(data)


def interpolate(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("{root}", str(ROOT))
    if isinstance(value, list):
        return [interpolate(item) for item in value]
    if isinstance(value, dict):
        return {str(key): interpolate(item) for key, item in value.items()}
    return value


def get_value(config: dict[str, Any], dotted: str, default: Any = None) -> Any:
    current: Any = config
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def resolve_path(path: str | os.PathLike[str]) -> Path:
    item = Path(path)
    return item if item.is_absolute() else ROOT / item


def state_file(name: str) -> Path:
    return ROOT / "runtime" / name


def ensure_runtime_dirs() -> None:
    for rel in ("logs", "runtime", "runtime/batch_low_api", "runtime/batch_low_api/batches", "runtime/batch_low_api_supervisor", "workspaces", "originals"):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

