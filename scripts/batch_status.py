#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import resolve_path


STATUS_COLUMNS = [
    "timestamp",
    "package_id",
    "status",
    "pid",
    "exit_code",
    "output_root",
    "log_path",
    "command",
]
ALLOWED_STATUSES = {"running", "completed", "failed"}


@dataclass
class Finding:
    severity: str
    check: str
    message: str


def add(findings: list[Finding], severity: str, check: str, message: str) -> None:
    findings.append(Finding(severity, check, message))


def status_path(batch_dir: Path) -> Path:
    return batch_dir / "status.tsv"


def clean_field(value: str | int | None) -> str:
    if value is None:
        return ""
    return str(value).replace("\t", " ").replace("\n", " ").strip()


def timestamp_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_header(path: Path) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(STATUS_COLUMNS)


def append_event(
    batch_dir: Path,
    package_id: str,
    status: str,
    pid: str = "",
    exit_code: str = "",
    output_root: str = "",
    log_path: str = "",
    command: str = "",
    timestamp: str = "",
) -> Path:
    if not package_id.strip():
        raise ValueError("package_id is required")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")
    if status in {"completed", "failed"} and exit_code == "":
        raise ValueError("exit_code is required for completed/failed status")

    batch_dir.mkdir(parents=True, exist_ok=True)
    path = status_path(batch_dir)
    lock_path = batch_dir / ".status.tsv.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ensure_header(path)
        with path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
            writer.writerow(
                [
                    clean_field(timestamp or timestamp_now()),
                    clean_field(package_id),
                    clean_field(status),
                    clean_field(pid),
                    clean_field(exit_code),
                    clean_field(output_root),
                    clean_field(log_path),
                    clean_field(command),
                ]
            )
        fcntl.flock(lock, fcntl.LOCK_UN)
    return path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return [dict(row) for row in reader]


def validate_status_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not path.exists():
        add(findings, "WARN", "batch_status", f"missing status.tsv: {path.parent}")
        return findings
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh, delimiter="\t")
            rows = list(reader)
    except OSError as exc:
        add(findings, "ERROR", "batch_status", f"cannot read {path}: {exc}")
        return findings
    if not rows:
        add(findings, "ERROR", "batch_status", f"empty status.tsv: {path}")
        return findings
    header = rows[0]
    if header != STATUS_COLUMNS:
        add(findings, "ERROR", "batch_status", f"status.tsv header differs from expected columns: {header}")
        return findings
    seen_running: set[str] = set()
    for index, row in enumerate(rows[1:], start=2):
        if len(row) != len(STATUS_COLUMNS):
            add(findings, "ERROR", "batch_status", f"row {index} has {len(row)} columns, expected {len(STATUS_COLUMNS)}")
            continue
        record = dict(zip(STATUS_COLUMNS, row))
        package_id = record["package_id"].strip()
        status = record["status"].strip()
        if not package_id:
            add(findings, "ERROR", "batch_status", f"row {index} has empty package_id")
        if status not in ALLOWED_STATUSES:
            add(findings, "ERROR", "batch_status", f"row {index} has invalid status {status!r}")
            continue
        if status == "running":
            seen_running.add(package_id)
            if not record["pid"].strip():
                add(findings, "WARN", "batch_status", f"running row {index} has no pid")
        else:
            if not record["exit_code"].strip().lstrip("-").isdigit():
                add(findings, "ERROR", "batch_status", f"{status} row {index} has invalid exit_code")
            if package_id and package_id not in seen_running:
                add(findings, "WARN", "batch_status", f"{status} row {index} has no prior running event")
    return findings


def latest_by_package(path: Path) -> dict[str, dict[str, str]]:
    latest: dict[str, dict[str, str]] = {}
    if not path.exists():
        return latest
    for row in read_rows(path):
        package_id = row.get("package_id", "")
        if package_id:
            latest[package_id] = row
    return latest


def status_summary(path: Path) -> dict[str, Any]:
    findings = validate_status_file(path)
    errors = [item for item in findings if item.severity == "ERROR"]
    latest = latest_by_package(path) if path.exists() and not errors else {}
    running = sorted(package_id for package_id, row in latest.items() if row.get("status") == "running")
    completed = sorted(package_id for package_id, row in latest.items() if row.get("status") == "completed")
    failed = sorted(package_id for package_id, row in latest.items() if row.get("status") == "failed")
    terminal = sorted(completed + failed)
    incomplete = sorted(package_id for package_id in latest if package_id not in terminal)
    return {
        "has_status": path.exists(),
        "valid": not errors,
        "total": len(latest),
        "running": len(running),
        "completed": len(completed),
        "failed": len(failed),
        "terminal": len(terminal),
        "complete": bool(latest) and not incomplete,
        "running_ids": running,
        "completed_ids": completed,
        "failed_ids": failed,
        "incomplete_ids": incomplete,
        "findings": [asdict(item) for item in findings],
    }


def print_shell_summary(summary: dict[str, Any]) -> None:
    for key in ("has_status", "valid", "complete"):
        print(f"{key}={1 if summary[key] else 0}")
    for key in ("total", "running", "completed", "failed", "terminal"):
        print(f"{key}={summary[key]}")
    for key in ("running_ids", "completed_ids", "failed_ids", "incomplete_ids"):
        print(f"{key}={','.join(summary[key])}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Record or validate low-API batch job status.")
    sub = parser.add_subparsers(dest="action", required=True)

    record = sub.add_parser("record", help="append one status event")
    record.add_argument("--batch-dir", required=True)
    record.add_argument("--package-id", required=True)
    record.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    record.add_argument("--pid", default="")
    record.add_argument("--exit-code", default="")
    record.add_argument("--output-root", default="")
    record.add_argument("--log-path", default="")
    record.add_argument("--command", dest="command_text", default="")
    record.add_argument("--timestamp", default="")

    validate = sub.add_parser("validate", help="validate a status.tsv file")
    validate.add_argument("--batch-dir", required=True)
    validate.add_argument("--json", action="store_true")
    validate.add_argument("--strict", action="store_true")

    summary = sub.add_parser("summary", help="summarize latest package status events")
    summary.add_argument("--batch-dir", required=True)
    summary.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.action == "record":
        path = append_event(
            resolve_path(args.batch_dir),
            args.package_id,
            args.status,
            args.pid,
            args.exit_code,
            args.output_root,
            args.log_path,
            args.command_text,
            args.timestamp,
        )
        print(path)
        return 0

    path = status_path(resolve_path(args.batch_dir))
    if args.action == "summary":
        payload = status_summary(path)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_shell_summary(payload)
        return 0 if payload["valid"] else 1

    findings = validate_status_file(path)
    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        errors = [item for item in findings if item.severity == "ERROR"]
        warnings = [item for item in findings if item.severity == "WARN"]
        print("== batch status validation ==")
        print(f"errors={len(errors)} warnings={len(warnings)}")
        for item in findings:
            print(f"{item.severity}: {item.check}: {item.message}")
        if not findings:
            print("OK: batch status is valid")
    if any(item.severity == "ERROR" for item in findings):
        return 1
    if args.strict and any(item.severity == "WARN" for item in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
