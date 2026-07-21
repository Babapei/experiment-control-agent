#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import load_config, root
from agent_core.provider import codex_exec_args, planning_provider, selected_model, selected_reasoning_effort, shell_environment


def write_nul_args(args: list[str]) -> None:
    for item in args:
        sys.stdout.buffer.write(item.encode("utf-8") + b"\0")


def print_shell_env(provider: dict[str, object]) -> None:
    for key, value in shell_environment(provider).items():
        print(f"export {key}={shlex.quote(str(value))}")
    for item in provider.get("extra_path_entries", []):
        if str(item).strip():
            print(f"export PATH=\"$PATH\":{shlex.quote(str(item))}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render planning-provider command details.")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("json", help="print normalized provider config")
    sub.add_parser("shell-env", help="print shell exports for the selected provider")

    args_parser = sub.add_parser("exec-args", help="print NUL-separated provider exec arguments")
    args_parser.add_argument("--last-message", required=True)
    args_parser.add_argument("--model-override", default="")
    args_parser.add_argument("--reasoning-effort-override", default="")
    args_parser.add_argument("--cwd", default=str(root()))

    selected_parser = sub.add_parser("selected", help="print selected model/reasoning labels as shell assignments")
    selected_parser.add_argument("--model-override", default="")
    selected_parser.add_argument("--reasoning-effort-override", default="")

    args = parser.parse_args(argv)
    provider = planning_provider(load_config())
    if not provider.get("supported", False):
        print(provider.get("error", "unsupported planning provider"), file=sys.stderr)
        return 2

    if args.action == "json":
        print(json.dumps(provider, ensure_ascii=False, indent=2))
        return 0
    if args.action == "shell-env":
        print_shell_env(provider)
        return 0
    if args.action == "selected":
        print(f"PROVIDER_SELECTED_MODEL={shlex.quote(selected_model(provider, args.model_override) or 'config-default')}")
        print(
            "PROVIDER_SELECTED_REASONING_EFFORT="
            + shlex.quote(selected_reasoning_effort(provider, args.reasoning_effort_override) or "config-default")
        )
        return 0

    write_nul_args(
        codex_exec_args(
            provider,
            cwd=args.cwd,
            last_message_path=args.last_message,
            model_override=args.model_override,
            reasoning_effort_override=args.reasoning_effort_override,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
