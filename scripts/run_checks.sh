#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

cd "$BASE_DIR"

echo "== shell syntax =="
bash -n scripts/*.sh

echo "== python compile =="
"$PYTHON_BIN" -m py_compile agent_core/*.py scripts/*.py tests/*.py

echo "== unit tests =="
"$PYTHON_BIN" -m unittest discover -s tests -v

echo "== doctor =="
"$PYTHON_BIN" scripts/doctor.py

echo "== runtime validation =="
"$PYTHON_BIN" scripts/validate_agent_state.py

echo "== cycle outcome validation =="
"$PYTHON_BIN" scripts/validate_cycle_outcome.py --allow-missing

echo "== prompt render =="
"$PYTHON_BIN" scripts/render_prompt.py cycle >/dev/null
"$PYTHON_BIN" scripts/render_prompt.py batch_low_api >/dev/null

echo "OK"
