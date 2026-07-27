#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import resolve_path, root


def clip(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def load_recent_outcomes(archive_dir: Path, limit: int = 6) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    outcomes: list[tuple[str, dict[str, Any]]] = []
    notices: list[str] = []
    if limit <= 0 or not archive_dir.exists():
        return outcomes, notices
    for path in sorted(archive_dir.glob("*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            notices.append(f"cannot read archived outcome {path.name}: {exc}")
            continue
        if not isinstance(payload, dict):
            notices.append(f"archived outcome is not a JSON object: {path.name}")
            continue
        outcomes.append((path.stem, payload))
        if len(outcomes) >= limit:
            break
    return outcomes, notices


def history_attention(outcomes: list[tuple[str, dict[str, Any]]], current_mode: str) -> list[str]:
    attention: list[str] = []
    if not outcomes:
        return attention
    latest_id, latest = outcomes[0]
    latest_mode = str(latest.get("agent_mode") or "").strip()
    if current_mode and latest_mode and current_mode != latest_mode:
        attention.append(
            f"current AGENT_MODE is {current_mode!r}, but latest validated cycle {latest_id!r} used {latest_mode!r}; reconcile or record a justified transition"
        )

    unresolved: list[str] = []
    missing_observed: list[str] = []
    for cycle_id, payload in outcomes:
        for record in payload.get("action_records", []):
            if isinstance(record, dict) and record.get("state") in {"running", "planned"}:
                unresolved.append(f"{cycle_id}: {record.get('id', '<unnamed>')} is {record.get('state')}")
        for record in payload.get("evidence_records", []):
            if not isinstance(record, dict) or record.get("state") != "observed":
                continue
            path_text = str(record.get("path") or "")
            if path_text and not resolve_path(path_text).exists():
                missing_observed.append(f"{cycle_id}: {path_text}")
    if unresolved:
        attention.append("reconcile unresolved historical actions with active jobs and current ledgers: " + "; ".join(unresolved[:6]))
    if missing_observed:
        attention.append("previously observed evidence is no longer present: " + "; ".join(missing_observed[:6]))
    return attention


def render_history(outcomes: list[tuple[str, dict[str, Any]]], notices: list[str], current_mode: str) -> str:
    lines = ["## Recent Validated Decision History", ""]
    if not outcomes:
        lines.append("No validated cycle outcomes exist yet. Establish a baseline from the configured project context.")
    for cycle_id, payload in outcomes:
        lines.extend(
            [
                f"### {cycle_id}",
                f"- Mode: `{payload.get('agent_mode', '')}` | Kind: `{payload.get('cycle_kind', '')}`",
                f"- Summary: {clip(payload.get('summary'))}",
            ]
        )
        transition = payload.get("mode_transition")
        if isinstance(transition, dict):
            lines.append(f"- Transition: `{transition.get('from', '')}` -> `{transition.get('to', '')}` because {clip(transition.get('reason'))}")
        lines.append("- Evidence:")
        for record in payload.get("evidence_records", [])[:4]:
            if isinstance(record, dict):
                lines.append(f"  - [{record.get('state', '')}] `{record.get('id', '')}`: {clip(record.get('impact'))} ({record.get('path', '')})")
        lines.append("- Actions:")
        for record in payload.get("action_records", [])[:4]:
            if isinstance(record, dict):
                lines.append(f"  - [{record.get('state', '')}] `{record.get('id', '')}`: {clip(record.get('description'))}")
        lines.append(f"- Next decision: {clip(payload.get('next_decision'))}")
        lines.append("")

    attention = [*notices, *history_attention(outcomes, current_mode)]
    if attention:
        lines.extend(["## State Attention", ""])
        lines.extend(f"- {item}" for item in attention)
        lines.append("")
    lines.append("Treat planned evidence and planned actions as unfinished. Reconcile this history with the live filesystem, active jobs, and current project profile before acting.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render bounded recent history from validated cycle outcomes.")
    parser.add_argument("--archive-dir", default="runtime/cycle_outcomes")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--current-mode", default="")
    args = parser.parse_args(argv)
    outcomes, notices = load_recent_outcomes(resolve_path(args.archive_dir), args.limit)
    print(render_history(outcomes, notices, args.current_mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
