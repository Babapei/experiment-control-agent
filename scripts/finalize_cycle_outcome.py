#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import resolve_path
from scripts.validate_cycle_outcome import Finding, run_checks


def safe_cycle_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("cycle id must contain only letters, digits, dot, underscore, or hyphen")
    return value


def copy_atomically(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.", delete=False) as fh:
        temporary = Path(fh.name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def finalize_cycle_outcome(source: Path, archive_dir: Path, latest_path: Path, cycle_id: str) -> list[Finding]:
    cycle_id = safe_cycle_id(cycle_id)
    findings = run_checks(source, missing_severity="ERROR")
    if any(item.severity == "ERROR" for item in findings):
        return findings

    archive_path = archive_dir / f"{cycle_id}.json"
    if archive_path.exists():
        return [Finding("ERROR", "cycle_outcome", f"refusing to overwrite existing archived cycle outcome: {archive_path}")]

    copy_atomically(source, archive_path)
    copy_atomically(source, latest_path)
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate, archive, and publish one pending cycle outcome.")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--source", default="runtime/pending_cycle_outcome.json")
    parser.add_argument("--archive-dir", default="runtime/cycle_outcomes")
    parser.add_argument("--latest", default="runtime/last_cycle_outcome.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    source = resolve_path(args.source)
    archive_dir = resolve_path(args.archive_dir)
    latest_path = resolve_path(args.latest)
    try:
        findings = finalize_cycle_outcome(source, archive_dir, latest_path, args.cycle_id)
    except ValueError as exc:
        findings = [Finding("ERROR", "cycle_outcome", str(exc))]

    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item.severity}: {item.check}: {item.message}")
        if not findings:
            print(f"Archived cycle outcome: {archive_dir / (args.cycle_id + '.json')}")
    return 1 if any(item.severity == "ERROR" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
