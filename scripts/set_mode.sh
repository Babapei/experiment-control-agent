#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"
kind="${1:-}"
value="${2:-}"

case "$kind" in
  agent)
    file="$BASE_DIR/runtime/AGENT_MODE"
    config_key="modes.agent_modes"
    ;;
  execution)
    file="$BASE_DIR/runtime/EXECUTION_MODE"
    config_key="modes.execution_modes"
    ;;
  batch_profile)
    file="$BASE_DIR/runtime/BATCH_PROFILE"
    config_key="modes.batch_profiles"
    ;;
  *)
    echo "Usage: $0 {agent|execution|batch_profile} VALUE" >&2
    exit 2
    ;;
esac

[[ -z "$value" ]] && echo "missing value" >&2 && exit 2

allowed_json="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" "$config_key" '[]')"
if ! "$PYTHON_BIN" - "$kind" "$value" "$allowed_json" <<'PY'
import json
import sys

kind, value, raw = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    parsed = json.loads(raw)
except Exception:
    parsed = []
if isinstance(parsed, dict):
    allowed = sorted(str(key) for key in parsed)
elif isinstance(parsed, list):
    allowed = [str(item) for item in parsed]
else:
    allowed = []
if allowed and value not in allowed:
    print(f"invalid {kind} mode/profile: {value}", file=sys.stderr)
    print("allowed: " + ", ".join(allowed), file=sys.stderr)
    raise SystemExit(1)
PY
then
  exit 2
fi

mkdir -p "$BASE_DIR/runtime"
printf '%s\n' "$value" > "$file"
echo "$(basename "$file")=$value"
