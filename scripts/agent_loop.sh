#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-1800}"

while true; do
  if [[ -f "$BASE_DIR/runtime/STOP" ]]; then
    echo "[agent_loop] STOP file detected. Exiting."
    exit 0
  fi
  set +e
  "$BASE_DIR/scripts/run_codex_cycle.sh"
  status=$?
  set -e
  [[ "$status" -eq 2 ]] && exit 2
  sleep "$INTERVAL_SECONDS"
done

