#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import load_config


@dataclass
class ActiveJob:
    pid: int
    ppid: int
    stat: str
    elapsed_seconds: int
    category: str
    resources: str
    command: str


def run_ps() -> list[str]:
    commands = [
        ["ps", "-eo", "pid=,ppid=,stat=,etimes=,args="],
        ["ps", "-eo", "pid=,ppid=,stat=,etime=,args="],
    ]
    for command in commands:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        if proc.returncode == 0:
            return proc.stdout.splitlines()
    return []


def parse_elapsed(value: str) -> int:
    if value.isdigit():
        return int(value)
    days = 0
    if "-" in value:
        day_text, value = value.split("-", 1)
        try:
            days = int(day_text)
        except ValueError:
            days = 0
    parts = value.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = [int(part) for part in parts]
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = [int(part) for part in parts]
        else:
            return 0
    except ValueError:
        return 0
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def parse_ps_line(line: str) -> tuple[int, int, str, int, str] | None:
    parts = line.strip().split(None, 4)
    if len(parts) < 5:
        return None
    try:
        return int(parts[0]), int(parts[1]), parts[2], parse_elapsed(parts[3]), parts[4]
    except ValueError:
        return None


def read_resources(pid: int, command: str) -> str:
    env_path = Path("/proc") / str(pid) / "environ"
    try:
        raw = env_path.read_bytes()
        for item in raw.split(b"\0"):
            if item.startswith(b"CUDA_VISIBLE_DEVICES="):
                return item.split(b"=", 1)[1].decode("utf-8", errors="replace") or "<empty>"
    except OSError:
        pass
    match = re.search(r"CUDA_VISIBLE_DEVICES=([^\s;]+)", command)
    return match.group(1) if match else ""


def compile_patterns(items: list[dict[str, str]]) -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for item in items:
        category = item.get("category", "managed")
        regex = item.get("regex")
        if regex:
            patterns.append((category, re.compile(regex)))
    return patterns


def collect_jobs(config: dict) -> list[ActiveJob]:
    detection = config.get("job_detection", {})
    hints = [str(item) for item in detection.get("managed_hints", [])]
    patterns = compile_patterns(detection.get("patterns", []))
    exclude = [re.compile(str(item)) for item in detection.get("exclude_patterns", [])]

    jobs: list[ActiveJob] = []
    seen: set[int] = set()
    for line in run_ps():
        parsed = parse_ps_line(line)
        if parsed is None:
            continue
        pid, ppid, stat, elapsed, command = parsed
        if pid == os.getpid() or pid in seen:
            continue
        if stat.startswith("Z"):
            continue
        if hints and not any(hint in command for hint in hints):
            continue
        if any(pattern.search(command) for pattern in exclude):
            continue
        category = None
        for label, pattern in patterns:
            if pattern.search(command):
                category = label
                break
        if category is None:
            continue
        seen.add(pid)
        jobs.append(ActiveJob(pid, ppid, stat, elapsed, category, read_resources(pid, command), command))
    return sorted(jobs, key=lambda job: (job.category, job.pid))


def format_elapsed(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def print_plain(jobs: list[ActiveJob]) -> None:
    if not jobs:
        print("no active managed jobs detected")
        return
    header = f"{'pid':>8} {'ppid':>8} {'stat':<6} {'elapsed':>12} {'category':<22} {'resources':<12} command"
    print(header)
    print("-" * len(header))
    for job in jobs:
        command = job.command if len(job.command) <= 180 else job.command[:177] + "..."
        print(f"{job.pid:>8} {job.ppid:>8} {job.stat:<6} {format_elapsed(job.elapsed_seconds):>12} {job.category:<22} {job.resources or '-':<12} {command}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List active jobs managed by this agent profile.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--count", action="store_true")
    args = parser.parse_args(argv)

    jobs = collect_jobs(load_config())
    if args.count:
        print(len(jobs))
    elif args.json:
        print(json.dumps([asdict(job) for job in jobs], ensure_ascii=False, indent=2))
    else:
        print_plain(jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
