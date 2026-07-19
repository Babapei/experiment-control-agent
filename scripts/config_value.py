#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import get_value, load_config


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: config_value.py dotted.key [default]", file=sys.stderr)
        return 2
    cfg = load_config()
    default = argv[1] if len(argv) > 1 else ""
    value = get_value(cfg, argv[0], default)
    if isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False))
    elif value is None:
        print("")
    else:
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
