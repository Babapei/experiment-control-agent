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


EVIDENCE_STATES = {"observed", "planned"}
ACTION_STATES = {"completed", "running", "planned", "not_taken"}


def require_record_string(findings: list[Finding], record: dict[str, Any], field: str, index: int, group: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        add(findings, "ERROR", "cycle_outcome", f"{group}[{index}].{field} must be a non-empty string")
        return ""
    return value.strip()


def check_evidence_records(findings: list[Finding], payload: dict[str, Any]) -> tuple[set[str], dict[str, str]]:
    records = payload.get("evidence_records")
    if not isinstance(records, list) or not records:
        add(findings, "ERROR", "cycle_outcome", "evidence_records must be a non-empty list")
        return set(), {}

    ids: set[str] = set()
    states: dict[str, str] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            add(findings, "ERROR", "cycle_outcome", f"evidence_records[{index}] must be an object")
            continue
        record_id = require_record_string(findings, record, "id", index, "evidence_records")
        state = require_record_string(findings, record, "state", index, "evidence_records")
        path_text = require_record_string(findings, record, "path", index, "evidence_records")
        require_record_string(findings, record, "summary", index, "evidence_records")
        require_record_string(findings, record, "impact", index, "evidence_records")
        if record_id in ids:
            add(findings, "ERROR", "cycle_outcome", f"evidence_records has duplicate id: {record_id!r}")
        elif record_id:
            ids.add(record_id)
            states[record_id] = state
        if state and state not in EVIDENCE_STATES:
            add(findings, "ERROR", "cycle_outcome", f"evidence_records[{index}].state must be one of {sorted(EVIDENCE_STATES)}")
        if state == "observed" and path_text and not resolve_path(path_text).exists():
            add(findings, "ERROR", "cycle_outcome", f"observed evidence path does not exist: {resolve_path(path_text)}")
    return ids, states


def check_evidence_ids(
    findings: list[Finding],
    value: Any,
    known_ids: set[str],
    field: str,
) -> list[str]:
    if not isinstance(value, list) or not value:
        add(findings, "ERROR", "cycle_outcome", f"{field} must be a non-empty list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            add(findings, "ERROR", "cycle_outcome", f"{field}[{index}] must be a non-empty evidence id")
            continue
        item = item.strip()
        result.append(item)
        if item not in known_ids:
            add(findings, "ERROR", "cycle_outcome", f"{field}[{index}] references unknown evidence id: {item!r}")
    return result


def check_action_records(findings: list[Finding], payload: dict[str, Any], evidence_ids: set[str]) -> None:
    records = payload.get("action_records")
    if not isinstance(records, list) or not records:
        add(findings, "ERROR", "cycle_outcome", "action_records must be a non-empty list")
        return
    record_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            add(findings, "ERROR", "cycle_outcome", f"action_records[{index}] must be an object")
            continue
        record_id = require_record_string(findings, record, "id", index, "action_records")
        state = require_record_string(findings, record, "state", index, "action_records")
        require_record_string(findings, record, "description", index, "action_records")
        require_record_string(findings, record, "rationale", index, "action_records")
        if record_id in record_ids:
            add(findings, "ERROR", "cycle_outcome", f"action_records has duplicate id: {record_id!r}")
        elif record_id:
            record_ids.add(record_id)
        if state and state not in ACTION_STATES:
            add(findings, "ERROR", "cycle_outcome", f"action_records[{index}].state must be one of {sorted(ACTION_STATES)}")
        check_evidence_ids(findings, record.get("evidence_ids"), evidence_ids, f"action_records[{index}].evidence_ids")


def check_mode_transition(findings: list[Finding], payload: dict[str, Any], agent_mode: str, modes: dict[str, Any], evidence_ids: set[str]) -> None:
    transition = payload.get("mode_transition", None)
    if transition is None:
        return
    if not isinstance(transition, dict):
        add(findings, "ERROR", "cycle_outcome", "mode_transition must be null or an object")
        return
    from_mode = require_record_string(findings, transition, "from", 0, "mode_transition")
    to_mode = require_record_string(findings, transition, "to", 0, "mode_transition")
    require_record_string(findings, transition, "reason", 0, "mode_transition")
    check_evidence_ids(findings, transition.get("evidence_ids"), evidence_ids, "mode_transition.evidence_ids")
    known_modes = modes.get("agent_modes", [])
    if isinstance(known_modes, list):
        if from_mode and from_mode not in known_modes:
            add(findings, "ERROR", "cycle_outcome", f"mode_transition.from is not a configured agent mode: {from_mode!r}")
        if to_mode and to_mode not in known_modes:
            add(findings, "ERROR", "cycle_outcome", f"mode_transition.to is not a configured agent mode: {to_mode!r}")
    if from_mode and to_mode and from_mode == to_mode:
        add(findings, "ERROR", "cycle_outcome", "mode_transition.from and mode_transition.to must differ")
    if to_mode and agent_mode and to_mode != agent_mode:
        add(findings, "ERROR", "cycle_outcome", "mode_transition.to must match the outcome agent_mode")


MODE_DETAIL_FIELDS = {
    "method_exploration": (
        "research_question",
        "hypothesis",
        "candidate_method",
        "validation_design",
        "evaluation_signal",
        "decision",
    ),
    "audit_validation": (
        "uncertainty",
        "audit_action",
        "evidence_path",
        "verdict",
        "promotion_or_followup",
    ),
    "target_recovery": (
        "selected_target",
        "hypothesis",
        "output_root_or_evidence",
        "target_state_update",
        "decision_after_completion",
    ),
}


def check_mode_details(findings: list[Finding], payload: dict[str, Any], agent_mode: str) -> None:
    expected = MODE_DETAIL_FIELDS.get(agent_mode)
    if expected is None:
        return
    details = payload.get("mode_details")
    if not isinstance(details, dict):
        add(findings, "ERROR", "cycle_outcome", f"mode_details must be an object for agent_mode={agent_mode!r}")
        return
    for field in expected:
        value = details.get(field)
        if not isinstance(value, str) or not value.strip():
            add(findings, "ERROR", "cycle_outcome", f"mode_details.{field} must be a non-empty string for agent_mode={agent_mode!r}")


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
    evidence_ids, evidence_states = check_evidence_records(findings, payload)
    check_action_records(findings, payload, evidence_ids)
    decision_evidence_ids = check_evidence_ids(findings, payload.get("decision_evidence_ids"), evidence_ids, "decision_evidence_ids")
    if decision_evidence_ids and all(evidence_states.get(item) == "planned" for item in decision_evidence_ids):
        add(findings, "WARN", "cycle_outcome", "next_decision is supported only by planned evidence")

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
    check_mode_details(findings, payload, agent_mode)
    check_mode_transition(findings, payload, agent_mode, modes, evidence_ids)
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
