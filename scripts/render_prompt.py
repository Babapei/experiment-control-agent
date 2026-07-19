#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import config_path, load_config, resolve_path, root, state_file


def read_state(name: str, default: str = "") -> str:
    try:
        return state_file(name).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return default


def doc_path(config: dict[str, Any], key: str) -> str:
    value = (config.get("project_docs") or {}).get(key, "")
    return str(resolve_path(value)) if value else ""


def render_context(config: dict[str, Any], prompt_kind: str) -> str:
    modes = config.get("modes", {})
    agent_mode = read_state("AGENT_MODE", modes.get("default_agent_mode", ""))
    execution_mode = read_state("EXECUTION_MODE", modes.get("default_execution_mode", ""))
    batch_profile = read_state("BATCH_PROFILE", modes.get("default_batch_profile", "auto"))
    batch_profiles = modes.get("batch_profiles", {})
    active_batch_profile = batch_profiles.get(batch_profile, {})
    mode_contracts = modes.get("agent_mode_contracts", {})
    active_mode_contract = mode_contracts.get(agent_mode, {}) if isinstance(mode_contracts, dict) else {}
    active_mode_contract_json = json.dumps(active_mode_contract, ensure_ascii=False, indent=2)
    manifest_columns = config.get("batch", {}).get("manifest_columns", [])
    reference_docs = (config.get("project_docs") or {}).get("reference_docs", [])

    lines = [
        "# Rendered Agent Context",
        "",
        f"- prompt_kind: `{prompt_kind}`",
        f"- config_path: `{config_path()}`",
        f"- project_name: `{config.get('project', {}).get('name', '')}`",
        f"- agent_mode: `{agent_mode}`",
        f"- execution_mode: `{execution_mode}`",
        f"- batch_profile: `{batch_profile}`",
        f"- agents_policy: `{doc_path(config, 'agents_policy')}`",
        f"- cycle_brief: `{doc_path(config, 'cycle_brief')}`",
        f"- reference_docs: `{json.dumps([str(resolve_path(item)) for item in reference_docs], ensure_ascii=False)}`",
        f"- batch_profile_settings: `{json.dumps(active_batch_profile, ensure_ascii=False)}`",
        f"- manifest_columns: `{json.dumps(manifest_columns, ensure_ascii=False)}`",
        "",
        "## Active Agent Mode Contract",
        "",
        "```json",
        active_mode_contract_json,
        "```",
        "",
        "Read the configured project files above before making project-specific decisions.",
        "Follow the active_agent_mode_contract when choosing actions and required artifacts.",
        "If a configured project file is missing, stop and report the configuration problem.",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render a prompt with resolved project context.")
    parser.add_argument("kind", choices=["cycle", "batch_low_api"])
    args = parser.parse_args(argv)

    config = load_config()
    prompt_file = root() / "prompts" / ("cycle_prompt.md" if args.kind == "cycle" else "batch_low_api_cycle_prompt.md")
    print(render_context(config, args.kind), end="")
    print(prompt_file.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
