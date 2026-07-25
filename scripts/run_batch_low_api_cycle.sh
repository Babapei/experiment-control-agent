#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG_VALUE="$BASE_DIR/scripts/config_value.py"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

mkdir -p "$BASE_DIR/logs" "$BASE_DIR/runtime" "$BASE_DIR/runtime/batch_low_api" "$BASE_DIR/runtime/batch_low_api_supervisor"

# shellcheck source=scripts/load_provider_env.sh
source "$BASE_DIR/scripts/load_provider_env.sh"

LOCK_FILE="$BASE_DIR/runtime/run_batch_low_api_cycle.lock"
PID_FILE="$BASE_DIR/runtime/run_batch_low_api_cycle.pid"
PENDING_OUTCOME="$BASE_DIR/runtime/pending_cycle_outcome.json"
REVIEW_REQUIRED="$BASE_DIR/runtime/REVIEW_REQUIRED"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "[run_batch_low_api_cycle] another low-API cycle is already running; skipping." | tee -a "$BASE_DIR/logs/batch_low_api_runner.log"
  exit 0
fi
printf '%s\n' "$$" > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

if [[ -f "$BASE_DIR/runtime/STOP" ]]; then
  echo "[run_batch_low_api_cycle] STOP file present, exiting."
  exit 0
fi
if [[ "${HONOR_PAUSE:-0}" == "1" && -f "$BASE_DIR/runtime/PAUSE" ]]; then
  echo "[run_batch_low_api_cycle] PAUSE file present, skipping."
  exit 0
fi
if [[ -f "$REVIEW_REQUIRED" ]]; then
  echo "[run_batch_low_api_cycle] REVIEW_REQUIRED present; inspect and remove it before starting another automatic cycle."
  exit 0
fi

if [[ "${PROVIDER_AUTH_REQUIRED:-true}" == "true" && ! -f "$CODEX_HOME/auth.json" ]]; then
  echo "[run_batch_low_api_cycle] missing Codex auth at $CODEX_HOME/auth.json" | tee -a "$BASE_DIR/logs/batch_low_api_runner.log"
  exit 2
fi

STAMP="$(date '+%Y%m%d_%H%M%S')"
JSONL_LOG="$BASE_DIR/logs/batch_low_api_cycle_${STAMP}.jsonl"
TEXT_LOG="$BASE_DIR/logs/batch_low_api_cycle_${STAMP}.last_message.txt"
rm -f "$PENDING_OUTCOME"
CYCLE_TIMEOUT_SECONDS="${CYCLE_TIMEOUT_SECONDS:-$("$PYTHON_BIN" "$CONFIG_VALUE" supervisor.cycle_timeout_seconds 7200)}"
BATCH_PROFILE="${BATCH_PROFILE:-$(cat "$BASE_DIR/runtime/BATCH_PROFILE" 2>/dev/null || "$PYTHON_BIN" "$CONFIG_VALUE" modes.default_batch_profile auto)}"
CODEX_MODEL_OVERRIDE="${CODEX_MODEL_OVERRIDE:-}"
CODEX_REASONING_EFFORT_OVERRIDE="${CODEX_REASONING_EFFORT_OVERRIDE:-}"
SUPPLEMENTAL_BATCH="${SUPPLEMENTAL_BATCH:-0}"
PROVIDER_SELECTED_MODEL="config-default"
PROVIDER_SELECTED_REASONING_EFFORT="config-default"
eval "$("$PYTHON_BIN" "$BASE_DIR/scripts/provider_command.py" selected \
  --model-override "$CODEX_MODEL_OVERRIDE" \
  --reasoning-effort-override "$CODEX_REASONING_EFFORT_OVERRIDE")"
PROVIDER_EXEC_ARGS=()
while IFS= read -r -d '' arg; do
  PROVIDER_EXEC_ARGS+=("$arg")
done < <("$PYTHON_BIN" "$BASE_DIR/scripts/provider_command.py" exec-args \
  --last-message "$TEXT_LOG" \
  --model-override "$CODEX_MODEL_OVERRIDE" \
  --reasoning-effort-override "$CODEX_REASONING_EFFORT_OVERRIDE" \
  --cwd "$BASE_DIR")

record_usage() {
  local status_label="$1"
  local usage_log="$BASE_DIR/runtime/batch_low_api/usage_log.tsv"
  local usage_tmp="$BASE_DIR/runtime/batch_low_api/usage_${STAMP}.tmp"

  "$PYTHON_BIN" - "$JSONL_LOG" > "$usage_tmp" <<'PY' || true
import json
import sys
usage = None
try:
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") == "turn.completed" and isinstance(obj.get("usage"), dict):
                usage = obj["usage"]
except FileNotFoundError:
    pass
if not usage:
    print("NA\tNA\tNA\tNA\tNA")
else:
    input_tokens = int(usage.get("input_tokens") or 0)
    cached = int(usage.get("cached_input_tokens") or 0)
    output = int(usage.get("output_tokens") or 0)
    reasoning = int(usage.get("reasoning_output_tokens") or 0)
    print(f"{input_tokens}\t{cached}\t{max(input_tokens - cached, 0)}\t{output}\t{reasoning}")
PY

  if [[ ! -f "$usage_log" ]]; then
    printf 'timestamp\tstatus\tbatch_profile\tmodel\treasoning_effort\tinput_tokens\tcached_input_tokens\tuncached_input_tokens\toutput_tokens\treasoning_output_tokens\tjsonl\tlast_message\n' > "$usage_log"
  fi
  local usage_fields
  usage_fields="$(cat "$usage_tmp" 2>/dev/null || printf 'NA\tNA\tNA\tNA\tNA')"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date '+%F %T')" "$status_label" "$BATCH_PROFILE" \
    "$PROVIDER_SELECTED_MODEL" "$PROVIDER_SELECTED_REASONING_EFFORT" \
    "$usage_fields" "$JSONL_LOG" "$TEXT_LOG" >> "$usage_log"
  rm -f "$usage_tmp"
}

{
  echo "[$(date '+%F %T')] starting low-API cycle $STAMP"
  echo "  batch_profile: $BATCH_PROFILE"
  echo "  jsonl: $JSONL_LOG"
  echo "  last_message: $TEXT_LOG"
} >> "$BASE_DIR/logs/batch_low_api_runner.log"

is_transient_codex_failure() {
  local log_file="$1"
  [[ -f "$log_file" ]] || return 1
  grep -Eiq \
    'Selected model is at capacity|model is at capacity|rate limit|temporar(il)?y|try again|overloaded|429|502|503|504|gateway|timeout|timed out|connection reset|connection refused|network|ECONN|ETIMEDOUT|service unavailable' \
    "$log_file"
}

set +e
"$PYTHON_BIN" "$BASE_DIR/scripts/render_prompt.py" batch_low_api | \
  timeout "$CYCLE_TIMEOUT_SECONDS" \
    "${PROVIDER_EXEC_ARGS[@]}" \
    >"$JSONL_LOG"
status=$?
set -e

if [[ "$status" -eq 124 ]]; then
  record_usage "timeout"
  echo "[$(date '+%F %T')] low-API cycle $STAMP timed out" >> "$BASE_DIR/logs/batch_low_api_runner.log"
  exit 75
elif [[ "$status" -ne 0 ]]; then
  record_usage "failed"
  echo "[$(date '+%F %T')] low-API cycle $STAMP failed with status $status" >> "$BASE_DIR/logs/batch_low_api_runner.log"
  if is_transient_codex_failure "$JSONL_LOG"; then
    echo "[$(date '+%F %T')] classified as transient failure" >> "$BASE_DIR/logs/batch_low_api_runner.log"
    exit 75
  fi
  exit "$status"
fi

record_usage "completed"
echo "[$(date '+%F %T')] completed low-API cycle $STAMP" >> "$BASE_DIR/logs/batch_low_api_runner.log"

if ! "$PYTHON_BIN" "$BASE_DIR/scripts/finalize_cycle_outcome.py" --cycle-id "$STAMP" >> "$BASE_DIR/logs/batch_low_api_runner.log" 2>&1; then
  {
    echo "cycle_id=$STAMP"
    echo "pending_outcome=$PENDING_OUTCOME"
    echo "log=$BASE_DIR/logs/batch_low_api_runner.log"
    echo "Resolve the outcome validation problem, then remove this file before another automatic cycle."
  } > "$REVIEW_REQUIRED"
  echo "[run_batch_low_api_cycle] outcome was not valid; REVIEW_REQUIRED created." | tee -a "$BASE_DIR/logs/batch_low_api_runner.log"
  exit 65
fi
rm -f "$REVIEW_REQUIRED"
