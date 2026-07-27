#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import resolve_path


@dataclass
class Finding:
    severity: str
    message: str


def load_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def normalized_path(value: str) -> str:
    return str(resolve_path(value))


def evaluate(expectations: dict[str, Any], outcome: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    expected_mode = str(expectations.get("expected_mode") or "")
    if expected_mode and outcome.get("agent_mode") != expected_mode:
        findings.append(Finding("ERROR", f"expected agent_mode={expected_mode!r}, got {outcome.get('agent_mode')!r}"))

    records = outcome.get("evidence_records", [])
    observed_paths = {
        normalized_path(str(record.get("path") or ""))
        for record in records
        if isinstance(record, dict) and record.get("state") == "observed" and record.get("path")
    }
    for item in expectations.get("required_observed_paths", []):
        if normalized_path(str(item)) not in observed_paths:
            findings.append(Finding("ERROR", f"required observed evidence was not cited: {item}"))
    for item in expectations.get("forbidden_observed_paths", []):
        if normalized_path(str(item)) in observed_paths:
            findings.append(Finding("ERROR", f"planned or forbidden evidence was reported as observed: {item}"))

    evidence_state = {
        str(record.get("id")): str(record.get("state"))
        for record in records
        if isinstance(record, dict) and record.get("id")
    }
    decision_ids = outcome.get("decision_evidence_ids", [])
    if expectations.get("decision_requires_observed", False) and not any(evidence_state.get(str(item)) == "observed" for item in decision_ids):
        findings.append(Finding("ERROR", "next decision is not supported by observed evidence"))

    action_states = {
        str(record.get("state"))
        for record in outcome.get("action_records", [])
        if isinstance(record, dict)
    }
    for state in expectations.get("required_action_states", []):
        if state not in action_states:
            findings.append(Finding("ERROR", f"expected an action with state={state!r}"))
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check traceability expectations for a behavioral acceptance scenario.")
    parser.add_argument("--scenario", required=True, help="scenario expectation JSON")
    parser.add_argument("--outcome", required=True, help="validated archived cycle outcome JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        findings = evaluate(load_object(resolve_path(args.scenario)), load_object(resolve_path(args.outcome)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        findings = [Finding("ERROR", str(exc))]
    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item.severity}: {item.message}")
        if not findings:
            print("PASS: scenario traceability expectations met")
    return 1 if any(item.severity == "ERROR" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
