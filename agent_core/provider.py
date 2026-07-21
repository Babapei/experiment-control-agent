from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agent_core.config import resolve_path, root


SUPPORTED_PROVIDER_TYPES = {"codex"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _resolve_optional_path(value: str) -> str:
    if not value:
        return ""
    return str(resolve_path(value))


def planning_provider(config: dict[str, Any]) -> dict[str, Any]:
    provider = _as_dict(config.get("provider"))
    codex = _as_dict(config.get("codex"))
    provider_codex = _as_dict(provider.get("codex"))
    merged_codex = {**codex, **provider_codex}

    provider_type = str(provider.get("type") or "codex").strip() or "codex"
    command = str(provider.get("command") or merged_codex.get("command") or "codex").strip()
    if provider_type not in SUPPORTED_PROVIDER_TYPES:
        return {
            "type": provider_type,
            "supported": False,
            "command": command,
            "error": f"unsupported planning provider type: {provider_type}",
        }

    home = str(merged_codex.get("home") or ".codex-home")
    resolved_home = _resolve_optional_path(home)
    conda_init = str(merged_codex.get("conda_init") or "")
    return {
        "type": "codex",
        "supported": True,
        "command": command,
        "home": resolved_home,
        "auth_required": _as_bool(merged_codex.get("auth_required", True), True),
        "conda_init": conda_init,
        "conda_env": str(merged_codex.get("conda_env") or ""),
        "extra_path_entries": [_resolve_optional_path(item) for item in _as_list(merged_codex.get("extra_path_entries"))],
        "default_model": str(merged_codex.get("default_model") or ""),
        "default_reasoning_effort": str(merged_codex.get("default_reasoning_effort") or ""),
        "fallback_after_failures": int(merged_codex.get("fallback_after_failures") or 3),
        "fallback_model": str(merged_codex.get("fallback_model") or ""),
        "fallback_reasoning_effort": str(merged_codex.get("fallback_reasoning_effort") or ""),
        "secondary_fallback_after_failures": int(merged_codex.get("secondary_fallback_after_failures") or 5),
        "secondary_fallback_model": str(merged_codex.get("secondary_fallback_model") or ""),
        "secondary_fallback_reasoning_effort": str(merged_codex.get("secondary_fallback_reasoning_effort") or ""),
        "disable_response_storage": _as_bool(merged_codex.get("disable_response_storage", False), False),
    }


def shell_environment(provider: dict[str, Any]) -> dict[str, str]:
    if provider.get("type") != "codex":
        return {}
    env = {
        "PLANNING_PROVIDER_TYPE": "codex",
        "PLANNING_PROVIDER_COMMAND": str(provider.get("command") or "codex"),
        "CODEX_HOME": str(provider.get("home") or root() / ".codex-home"),
        "PROVIDER_AUTH_REQUIRED": "true" if provider.get("auth_required") else "false",
        "PROVIDER_CONDA_INIT": str(provider.get("conda_init") or ""),
        "PROVIDER_CONDA_ENV": str(provider.get("conda_env") or ""),
    }
    return env


def selected_model(provider: dict[str, Any], model_override: str = "") -> str:
    return model_override.strip() or str(provider.get("default_model") or "")


def selected_reasoning_effort(provider: dict[str, Any], effort_override: str = "") -> str:
    return effort_override.strip() or str(provider.get("default_reasoning_effort") or "")


def codex_exec_args(
    provider: dict[str, Any],
    *,
    cwd: str | os.PathLike[str] | None = None,
    last_message_path: str | os.PathLike[str],
    model_override: str = "",
    reasoning_effort_override: str = "",
) -> list[str]:
    if provider.get("type") != "codex" or not provider.get("supported", False):
        raise ValueError(str(provider.get("error") or "unsupported planning provider"))

    model = selected_model(provider, model_override)
    effort = selected_reasoning_effort(provider, reasoning_effort_override)
    args = [str(provider.get("command") or "codex"), "exec"]
    if model:
        args.extend(["--model", model])
    if effort:
        args.extend(["--config", f'model_reasoning_effort="{effort}"'])
    if provider.get("disable_response_storage"):
        args.extend(["--config", "disable_response_storage=true"])
    args.extend(
        [
            "--skip-git-repo-check",
            "-C",
            str(Path(cwd) if cwd is not None else root()),
            "--dangerously-bypass-approvals-and-sandbox",
            "--output-last-message",
            str(last_message_path),
            "--json",
            "-",
        ]
    )
    return args
