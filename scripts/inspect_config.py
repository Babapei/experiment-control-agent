#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_core.config import config_path, load_config


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Print the resolved agent configuration.")
    parser.add_argument("--path", action="store_true", help="print only the config path")
    args = parser.parse_args(argv)

    if args.path:
        print(config_path())
        return 0
    print(json.dumps(load_config(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

