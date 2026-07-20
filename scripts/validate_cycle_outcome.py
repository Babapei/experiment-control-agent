#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import load_config, resolve_path, state_file


@dataclass
class Finding:
    severity: str
    check: str
    message: str


def add(findings: list[Finding], severity: str, check: str, message: str) -> None:
    findings.append(Finding(severity, check, message))


def read_state(name: str, default: str = "") -> str:
    try:
        return state_file(name).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return default


def load_outcome(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except FileNotFoundError:
        return None, None
    except Exception as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "cycle outcome root must be a JSON object"
    return payload, None


def require_string(findings: list[Finding], payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        add(findings, "ERROR", "cycle_outcome", f"{key} must be a non-empty string")
        return ""
    return value.strip()


def require_list(findings: list[Finding], payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        add(findings, "ERROR", "cycle_outcome", f"{key} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            add(findings, "ERROR", "cycle_outcome", f"{key}[{index}] must be a non-empty string")
        else:
            result.append(item.strip())
    return result


def check_contract_reference(
    findings: list[Finding],
    payload: dict[str, Any],
    contract: dict[str, Any],
) -> None:
    success = str(payload.get("success_criterion_met") or "").strip()
    escalation = str(payload.get("escalation_criterion_used") or "").strip()
    if not success and not escalation:
        add(
            findings,
            "ERROR",
            "cycle_outcome",
            "one of success_criterion_met or escalation_criterion_used must be set",
        )
        return
    if success and escalation:
        add(
            findings,
            "WARN",
            "cycle_outcome",
            "both success_criterion_met and escalation_criterion_used are set; prefer exactly one",
        )

    success_options = contract.get("success_criteria", [])
    escalation_options = contract.get("escalation_criteria", [])
    if success and isinstance(success_options, list) and success not in success_options:
        add(findings, "WARN", "cycle_outcome", "success_criterion_met does not exactly match the active mode contract")
    if escalation and isinstance(escalation_options, list) and escalation not in escalation_options:
        add(findings, "WARN", "cycle_outcome", "escalation_criterion_used does not exactly match the active mode contract")


def check_evidence_paths(findings: list[Finding], evidence_paths: list[str]) -> None:
    for item in evidence_paths:
        path = resolve_path(item)
        if not path.exists():
            add(findings, "WARN", "cycle_outcome", f"evidence path does not exist: {path}")


def check_outcome(findings: list[Finding], config: dict[str, Any], payload: dict[str, Any]) -> None:
    modes = config.get("modes", {})
    default_agent_mode = modes.get("default_agent_mode", "")
    default_execution_mode = modes.get("default_execution_mode", "")
    active_agent_mode = read_state("AGENT_MODE", str(default_agent_mode))
    active_execution_mode = read_state("EXECUTION_MODE", str(default_execution_mode))

    agent_mode = require_string(findings, payload, "agent_mode")
    execution_mode = require_string(findings, payload, "execution_mode")
    require_string(findings, payload, "cycle_kind")
    require_string(findings, payload, "summary")
    require_string(findings, payload, "next_decision")
    require_list(findings, payload, "reads")
    require_list(findings, payload, "actions")
    require_list(findings, payload, "artifacts")
    evidence_paths = require_list(findings, payload, "evidence_paths")

    if agent_mode and active_agent_mode and agent_mode != active_agent_mode:
        add(findings, "ERROR", "cycle_outcome", f"agent_mode {agent_mode!r} does not match runtime AGENT_MODE {active_agent_mode!r}")
    if execution_mode and active_execution_mode and execution_mode != active_execution_mode:
        add(
            findings,
            "ERROR",
            "cycle_outcome",
            f"execution_mode {execution_mode!r} does not match runtime EXECUTION_MODE {active_execution_mode!r}",
        )

    contracts = modes.get("agent_mode_contracts", {})
    contract = contracts.get(agent_mode, {}) if isinstance(contracts, dict) else {}
    if not isinstance(contract, dict) or not contract:
        add(findings, "ERROR", "cycle_outcome", f"agent_mode {agent_mode!r} has no active contract")
    else:
        check_contract_reference(findings, payload, contract)
    check_evidence_paths(findings, evidence_paths)


def default_outcome_path() -> Path:
    return state_file("last_cycle_outcome.json")


def run_checks(path: Path | None = None, missing_severity: str = "WARN") -> list[Finding]:
    outcome_path = path or default_outcome_path()
    findings: list[Finding] = []
    payload, error = load_outcome(outcome_path)
    if error:
        add(findings, "ERROR", "cycle_outcome", f"cannot read {outcome_path}: {error}")
        return findings
    if payload is None:
        add(findings, missing_severity, "cycle_outcome", f"missing cycle outcome file: {outcome_path}")
        return findings
    check_outcome(findings, load_config(), payload)
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate the latest machine-readable cycle outcome.")
    parser.add_argument("--path", default="", help="outcome JSON path; defaults to runtime/last_cycle_outcome.json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-missing", action="store_true", help="treat a missing outcome file as informational")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else default_outcome_path()
    if not path.is_absolute():
        path = resolve_path(path)
    findings = run_checks(path, "INFO" if args.allow_missing else "WARN")

    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        errors = [item for item in findings if item.severity == "ERROR"]
        warnings = [item for item in findings if item.severity == "WARN"]
        infos = [item for item in findings if item.severity == "INFO"]
        print("== cycle outcome validation ==")
        print(f"errors={len(errors)} warnings={len(warnings)} info={len(infos)}")
        for item in findings:
            print(f"{item.severity}: {item.check}: {item.message}")
        if not findings:
            print("OK: cycle outcome is valid")

    if any(item.severity == "ERROR" for item in findings):
        return 1
    if args.strict and any(item.severity == "WARN" for item in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
