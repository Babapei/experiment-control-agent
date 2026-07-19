#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import load_config, root, state_file


@dataclass
class Finding:
    severity: str
    check: str
    message: str


def add(findings: list[Finding], severity: str, check: str, message: str) -> None:
    findings.append(Finding(severity, check, message))


def read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return default


def check_modes(findings: list[Finding], config: dict) -> None:
    modes = config.get("modes", {})
    agent_modes = set(modes.get("agent_modes", []))
    execution_modes = set(modes.get("execution_modes", []))
    batch_profiles = set((modes.get("batch_profiles") or {}).keys())

    agent_mode = read(state_file("AGENT_MODE"), modes.get("default_agent_mode", ""))
    execution_mode = read(state_file("EXECUTION_MODE"), modes.get("default_execution_mode", ""))
    batch_profile = read(state_file("BATCH_PROFILE"), modes.get("default_batch_profile", "auto"))
    contracts = modes.get("agent_mode_contracts", {})

    if agent_modes and agent_mode not in agent_modes:
        add(findings, "ERROR", "mode", f"invalid AGENT_MODE={agent_mode!r}")
    if agent_mode and isinstance(contracts, dict) and agent_mode not in contracts:
        add(findings, "ERROR", "mode", f"AGENT_MODE={agent_mode!r} has no agent_mode_contract")
    if execution_modes and execution_mode not in execution_modes:
        add(findings, "ERROR", "mode", f"invalid EXECUTION_MODE={execution_mode!r}")
    if batch_profiles and batch_profile not in batch_profiles:
        add(findings, "ERROR", "mode", f"invalid BATCH_PROFILE={batch_profile!r}")


def check_required_files(findings: list[Finding]) -> None:
    for rel in (
        "configs/project.example.json",
        "prompts/cycle_prompt.md",
        "prompts/batch_low_api_cycle_prompt.md",
        "scripts/run_codex_cycle.sh",
        "scripts/run_batch_low_api_cycle.sh",
        "scripts/list_active_jobs.py",
    ):
        if not (root() / rel).exists():
            add(findings, "ERROR", "required_files", f"missing {rel}")


def parse_current_batch() -> Path | None:
    current = root() / "runtime" / "batch_low_api" / "current_batch.md"
    text = read(current)
    for line in text.splitlines():
        if "Batch directory:" in line and "`" in line:
            return Path(line.split("`", 2)[1])
    return None


def check_manifest(findings: list[Finding], config: dict) -> None:
    batch_dir = parse_current_batch()
    if batch_dir is None:
        return
    manifest = batch_dir / "manifest.tsv"
    if not manifest.exists():
        add(findings, "WARN", "manifest", f"current batch has no manifest.tsv: {batch_dir}")
        return
    expected = config.get("batch", {}).get("manifest_columns", [])
    try:
        with manifest.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh, delimiter="\t"))
    except OSError as exc:
        add(findings, "ERROR", "manifest", f"cannot read {manifest}: {exc}")
        return
    if not rows:
        add(findings, "ERROR", "manifest", f"empty manifest: {manifest}")
        return
    if expected and rows[0] != expected:
        add(findings, "WARN", "manifest", f"manifest header differs from config: {rows[0]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generic agent runtime state.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_config()
    findings: list[Finding] = []
    check_required_files(findings)
    check_modes(findings, config)
    check_manifest(findings, config)

    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        errors = [item for item in findings if item.severity == "ERROR"]
        warnings = [item for item in findings if item.severity == "WARN"]
        print("== agent state self-check ==")
        print(f"errors={len(errors)} warnings={len(warnings)}")
        for item in findings:
            print(f"{item.severity}: {item.check}: {item.message}")
        if not findings:
            print("OK: no issues detected")
    return 1 if any(item.severity == "ERROR" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
