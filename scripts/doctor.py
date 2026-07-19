#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import config_path, load_config, resolve_path, root


@dataclass
class Finding:
    severity: str
    check: str
    message: str


def add(findings: list[Finding], severity: str, check: str, message: str) -> None:
    findings.append(Finding(severity, check, message))


def check_modes(findings: list[Finding], cfg: dict[str, Any]) -> None:
    modes = cfg.get("modes", {})
    agent_modes = modes.get("agent_modes", [])
    execution_modes = modes.get("execution_modes", [])
    batch_profiles = modes.get("batch_profiles", {})
    if not isinstance(agent_modes, list) or not agent_modes:
        add(findings, "ERROR", "modes", "modes.agent_modes must be a non-empty list")
    if modes.get("default_agent_mode") not in agent_modes:
        add(findings, "ERROR", "modes", "default_agent_mode is not listed in agent_modes")
    if not isinstance(execution_modes, list) or not execution_modes:
        add(findings, "ERROR", "modes", "modes.execution_modes must be a non-empty list")
    if modes.get("default_execution_mode") not in execution_modes:
        add(findings, "ERROR", "modes", "default_execution_mode is not listed in execution_modes")
    if not isinstance(batch_profiles, dict) or not batch_profiles:
        add(findings, "WARN", "modes", "no batch profiles configured")
        return
    default_profile = modes.get("default_batch_profile")
    if default_profile not in batch_profiles:
        add(findings, "ERROR", "modes", "default_batch_profile is not listed in batch_profiles")
    for name, profile in batch_profiles.items():
        if not isinstance(profile, dict):
            add(findings, "ERROR", "modes", f"batch profile {name!r} must be an object")
            continue
        for key in ("target_min_hours", "target_max_hours", "min_gpu_packages", "force_fill_idle_gpus", "max_codex_turns"):
            if not isinstance(profile.get(key), int) or profile.get(key) < 0:
                add(findings, "WARN", "modes", f"batch profile {name!r} has missing/non-negative-int field {key!r}")


def check_numeric_config(findings: list[Finding], cfg: dict[str, Any]) -> None:
    supervisor = cfg.get("supervisor", {})
    for key in ("check_interval_seconds", "heartbeat_seconds", "min_cycle_gap_seconds", "cycle_timeout_seconds", "retry_base_seconds", "retry_max_seconds"):
        value = supervisor.get(key)
        if not isinstance(value, int) or value <= 0:
            add(findings, "ERROR", "supervisor", f"supervisor.{key} must be a positive integer")
    if isinstance(supervisor.get("retry_base_seconds"), int) and isinstance(supervisor.get("retry_max_seconds"), int):
        if supervisor["retry_base_seconds"] > supervisor["retry_max_seconds"]:
            add(findings, "WARN", "supervisor", "retry_base_seconds is greater than retry_max_seconds")

    supplemental = cfg.get("batch", {}).get("supplemental", {})
    if not isinstance(supplemental, dict):
        add(findings, "ERROR", "batch", "batch.supplemental must be an object")
        return
    if not isinstance(supplemental.get("enabled", False), bool):
        add(findings, "ERROR", "batch", "batch.supplemental.enabled must be a boolean")
    for key in ("min_active_seconds", "min_cycle_gap_seconds", "result_change_gap_seconds", "min_idle_gpus", "idle_gpu_memory_max_mb", "idle_gpu_util_max"):
        value = supplemental.get(key)
        if not isinstance(value, int) or value < 0:
            add(findings, "ERROR", "batch", f"batch.supplemental.{key} must be a non-negative integer")


def check_regexes(findings: list[Finding], cfg: dict[str, Any]) -> None:
    detection = cfg.get("job_detection", {})
    for section in ("patterns",):
        for item in detection.get(section, []):
            regex = item.get("regex") if isinstance(item, dict) else None
            if not regex:
                add(findings, "ERROR", "job_detection", f"{section} entry missing regex")
                continue
            try:
                re.compile(regex)
            except re.error as exc:
                add(findings, "ERROR", "job_detection", f"invalid regex {regex!r}: {exc}")
    for regex in detection.get("exclude_patterns", []):
        try:
            re.compile(str(regex))
        except re.error as exc:
            add(findings, "ERROR", "job_detection", f"invalid exclude regex {regex!r}: {exc}")


def check_paths(findings: list[Finding], cfg: dict[str, Any]) -> None:
    for section in ("workspaces", "originals"):
        entries = cfg.get(section, {})
        if not isinstance(entries, dict):
            add(findings, "ERROR", section, f"{section} must be an object")
            continue
        for name, spec in entries.items():
            path_text = spec if isinstance(spec, str) else spec.get("path", "") if isinstance(spec, dict) else ""
            if not path_text:
                add(findings, "ERROR", section, f"{section}.{name} is missing path")
                continue
            path = resolve_path(path_text)
            if not path.exists():
                add(findings, "WARN", section, f"{section}.{name} path does not exist yet: {path}")


def check_project_docs(findings: list[Finding], cfg: dict[str, Any]) -> None:
    docs = cfg.get("project_docs", {})
    for key in ("cycle_brief", "agents_policy"):
        path_text = docs.get(key, "")
        if not path_text:
            add(findings, "WARN", "project_docs", f"project_docs.{key} is not configured")
            continue
        path = resolve_path(path_text)
        if not path.exists():
            add(findings, "ERROR", "project_docs", f"project_docs.{key} does not exist: {path}")
    for path_text in docs.get("reference_docs", []):
        path = resolve_path(path_text)
        if not path.exists():
            add(findings, "WARN", "project_docs", f"reference doc does not exist yet: {path}")


def check_results(findings: list[Finding], cfg: dict[str, Any]) -> None:
    results = cfg.get("results", {})
    paths = results.get("watch_paths", [])
    patterns = results.get("file_patterns", [])
    if not isinstance(paths, list) or not paths:
        add(findings, "ERROR", "results", "results.watch_paths must be a non-empty list")
    else:
        for path_text in paths:
            path = resolve_path(str(path_text))
            if not path.exists():
                add(findings, "WARN", "results", f"watch path does not exist yet: {path}")
    if not isinstance(patterns, list) or not patterns:
        add(findings, "WARN", "results", "results.file_patterns is empty; every file under watch_paths may be ignored")
    manifest_columns = cfg.get("batch", {}).get("manifest_columns", [])
    if not isinstance(manifest_columns, list) or not manifest_columns or not all(isinstance(item, str) and item for item in manifest_columns):
        add(findings, "ERROR", "batch", "batch.manifest_columns must be a non-empty list of strings")


def check_tools(findings: list[Finding], cfg: dict[str, Any]) -> None:
    if cfg.get("codex", {}).get("auth_required", True) and shutil.which("codex") is None:
        add(findings, "WARN", "tools", "`codex` is not on PATH in this shell")
    if cfg.get("results", {}).get("include_tmux_sessions", True) and shutil.which("tmux") is None:
        add(findings, "WARN", "tools", "`tmux` is not on PATH; supervisor launch and tmux signatures need it")
    if cfg.get("results", {}).get("include_gpu_compute_apps", True) and shutil.which("nvidia-smi") is None:
        add(findings, "INFO", "tools", "`nvidia-smi` is not on PATH; GPU signatures will be empty")
    conda_init = cfg.get("codex", {}).get("conda_init", "")
    if conda_init and not Path(conda_init).exists():
        add(findings, "WARN", "tools", f"configured conda_init does not exist: {conda_init}")


def check_publish_safety(findings: list[Finding]) -> None:
    sensitive = [root() / ".codex-home" / "auth.json", root() / "configs" / "project.json"]
    for path in sensitive:
        if path.exists():
            add(findings, "INFO", "publish", f"local machine-specific file exists and should not be committed: {path}")


def run_checks() -> list[Finding]:
    findings: list[Finding] = []
    try:
        cfg = load_config()
    except Exception as exc:
        return [Finding("ERROR", "config", f"cannot load {config_path()}: {exc}")]
    add(findings, "INFO", "config", f"using config: {config_path()}")
    check_modes(findings, cfg)
    check_numeric_config(findings, cfg)
    check_regexes(findings, cfg)
    check_paths(findings, cfg)
    check_project_docs(findings, cfg)
    check_results(findings, cfg)
    check_tools(findings, cfg)
    check_publish_safety(findings)
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run setup and publish-safety checks.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args(argv)

    findings = run_checks()
    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        errors = [item for item in findings if item.severity == "ERROR"]
        warnings = [item for item in findings if item.severity == "WARN"]
        infos = [item for item in findings if item.severity == "INFO"]
        print("== agent doctor ==")
        print(f"errors={len(errors)} warnings={len(warnings)} info={len(infos)}")
        for item in findings:
            print(f"{item.severity}: {item.check}: {item.message}")
    if any(item.severity == "ERROR" for item in findings):
        return 1
    if args.strict and any(item.severity == "WARN" for item in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
