#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-1800}"

while true; do
  if [[ -f "$BASE_DIR/runtime/STOP" ]]; then
    echo "[agent_loop] STOP file detected. Exiting."
    exit 0
  fi
  mode="$(cat "$BASE_DIR/runtime/EXECUTION_MODE" 2>/dev/null || "$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" modes.default_execution_mode interval)"
  case "$mode" in
    interval)
      ;;
    event)
      echo "[agent_loop] EXECUTION_MODE=event detected; handing off."
      exec "$BASE_DIR/scripts/event_agent_loop.sh"
      ;;
    batch_low_api)
      echo "[agent_loop] EXECUTION_MODE=batch_low_api detected; handing off."
      exec "$BASE_DIR/scripts/batch_low_api_loop.sh"
      ;;
    manual)
      sleep "$INTERVAL_SECONDS"
      continue
      ;;
    *)
      echo "[agent_loop] unsupported EXECUTION_MODE=$mode; exiting." >&2
      exit 1
      ;;
  esac
  set +e
  "$BASE_DIR/scripts/run_codex_cycle.sh"
  status=$?
  set -e
  [[ "$status" -eq 2 ]] && exit 2
  sleep "$INTERVAL_SECONDS"
done
