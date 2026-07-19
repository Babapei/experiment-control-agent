#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import load_config, resolve_path


def iter_result_records(config: dict) -> list[str]:
    results = config.get("results", {})
    watch_paths = [resolve_path(path) for path in results.get("watch_paths", ["runtime"])]
    patterns = [str(item) for item in results.get("file_patterns", [])]
    records: list[str] = []
    for base in watch_paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if patterns and not any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            records.append(f"file {stat.st_mtime_ns} {stat.st_size} {path}")
    return records


def command_lines(command: list[str]) -> list[str]:
    try:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except FileNotFoundError:
        return []
    return sorted(line for line in proc.stdout.splitlines() if line.strip())


def signature(config: dict) -> str:
    results = config.get("results", {})
    records = iter_result_records(config)
    if results.get("include_tmux_sessions", True):
        records.extend(f"tmux {line}" for line in command_lines(["tmux", "ls"]))
    if results.get("include_gpu_compute_apps", True):
        records.extend(
            f"gpu {line}"
            for line in command_lines(
                ["nvidia-smi", "--query-compute-apps=gpu_bus_id,pid,process_name", "--format=csv,noheader,nounits"]
            )
        )
    text = "\n".join(sorted(records)) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    print(signature(load_config()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
