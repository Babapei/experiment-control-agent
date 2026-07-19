#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a tiny CPU-only toy task.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    time.sleep(args.duration)
    completed = time.time()
    payload = {
        "task_id": args.task_id,
        "status": "completed",
        "duration_seconds": round(completed - started, 3),
        "started_epoch": started,
        "completed_epoch": completed
    }
    (output_dir / "completed.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

