#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import ensure_runtime_dirs, load_config, resolve_path, root, state_file


def safe_link_path(parent: Path, name: str) -> Path:
    item = Path(name)
    if item.is_absolute() or item.name != name or name in {"", ".", ".."}:
        raise ValueError(f"unsafe {parent.name} link name: {name!r}")
    return parent / name


def ensure_symlink(link: Path, target: Path) -> None:
    if link.is_symlink():
        if os.readlink(link) == str(target):
            return
        link.unlink()
    elif link.exists():
        raise RuntimeError(f"refusing to replace non-symlink path: {link}")
    os.symlink(target, link)


def link_map(section: str, target_parent: str, config: dict) -> None:
    entries = config.get(section, {})
    if not isinstance(entries, dict):
        return
    parent = root() / target_parent
    parent.mkdir(parents=True, exist_ok=True)
    for name, spec in entries.items():
        if isinstance(spec, str):
            path = spec
        elif isinstance(spec, dict):
            path = spec.get("path", "")
        else:
            continue
        if not path:
            continue
        link = safe_link_path(parent, name)
        target = resolve_path(path)
        ensure_symlink(link, target)


def init_state(config: dict) -> None:
    modes = config.get("modes", {})
    defaults = {
        "AGENT_MODE": modes.get("default_agent_mode", "method_exploration"),
        "EXECUTION_MODE": modes.get("default_execution_mode", "manual"),
        "BATCH_PROFILE": modes.get("default_batch_profile", "auto"),
    }
    for name, value in defaults.items():
        path = state_file(name)
        if not path.exists():
            path.write_text(f"{value}\n", encoding="utf-8")


def main() -> int:
    cfg = load_config()
    ensure_runtime_dirs()
    try:
        link_map("workspaces", "workspaces", cfg)
        link_map("originals", "originals", cfg)
    except (RuntimeError, ValueError) as exc:
        print(f"bootstrap_layout: {exc}", file=sys.stderr)
        return 1
    init_state(cfg)
    print(f"Bootstrapped agent layout at {root()}")
    for parent_name in ("workspaces", "originals"):
        parent = root() / parent_name
        for item in sorted(parent.iterdir()):
            if item.is_symlink():
                print(f"{parent_name}/{item.name} -> {os.readlink(item)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
