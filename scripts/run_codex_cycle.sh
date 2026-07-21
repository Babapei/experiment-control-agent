#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG_VALUE="$BASE_DIR/scripts/config_value.py"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

mkdir -p "$BASE_DIR/logs" "$BASE_DIR/runtime"

# shellcheck source=scripts/load_provider_env.sh
source "$BASE_DIR/scripts/load_provider_env.sh"

LOCK_FILE="$BASE_DIR/runtime/run_codex_cycle.lock"
PID_FILE="$BASE_DIR/runtime/run_codex_cycle.pid"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "[run_codex_cycle] another Codex cycle is already running; skipping." | tee -a "$BASE_DIR/logs/runner.log"
  exit 0
fi
printf '%s\n' "$$" > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

if [[ -f "$BASE_DIR/runtime/STOP" ]]; then
  echo "[run_codex_cycle] STOP file present, exiting."
  exit 0
fi
if [[ -f "$BASE_DIR/runtime/PAUSE" ]]; then
  echo "[run_codex_cycle] PAUSE file present, skipping cycle."
  exit 0
fi

if [[ "${PROVIDER_AUTH_REQUIRED:-true}" == "true" && ! -f "$CODEX_HOME/auth.json" ]]; then
  echo "[run_codex_cycle] missing Codex auth at $CODEX_HOME/auth.json" | tee -a "$BASE_DIR/logs/runner.log"
  exit 2
fi

STAMP="$(date '+%Y%m%d_%H%M%S')"
JSONL_LOG="$BASE_DIR/logs/cycle_${STAMP}.jsonl"
TEXT_LOG="$BASE_DIR/logs/cycle_${STAMP}.last_message.txt"
CYCLE_TIMEOUT_SECONDS="${CYCLE_TIMEOUT_SECONDS:-$("$PYTHON_BIN" "$CONFIG_VALUE" supervisor.cycle_timeout_seconds 1800)}"
PROVIDER_EXEC_ARGS=()
while IFS= read -r -d '' arg; do
  PROVIDER_EXEC_ARGS+=("$arg")
done < <("$PYTHON_BIN" "$BASE_DIR/scripts/provider_command.py" exec-args --last-message "$TEXT_LOG" --cwd "$BASE_DIR")

set +e
"$PYTHON_BIN" "$BASE_DIR/scripts/render_prompt.py" cycle | \
  timeout "$CYCLE_TIMEOUT_SECONDS" \
    "${PROVIDER_EXEC_ARGS[@]}" \
    >"$JSONL_LOG"
status=$?
set -e

if [[ "$status" -eq 124 ]]; then
  echo "[$(date '+%F %T')] cycle $STAMP timed out after ${CYCLE_TIMEOUT_SECONDS}s" >> "$BASE_DIR/logs/runner.log"
  exit 124
elif [[ "$status" -ne 0 ]]; then
  echo "[$(date '+%F %T')] cycle $STAMP failed with status $status" >> "$BASE_DIR/logs/runner.log"
  exit "$status"
fi

{
  echo "[$(date '+%F %T')] completed cycle $STAMP"
  echo "  jsonl: $JSONL_LOG"
  echo "  last_message: $TEXT_LOG"
} >> "$BASE_DIR/logs/runner.log"

{
  echo "[$(date '+%F %T')] validating cycle outcome for $STAMP"
  "$PYTHON_BIN" "$BASE_DIR/scripts/validate_cycle_outcome.py" || true
} >> "$BASE_DIR/logs/runner.log" 2>&1
