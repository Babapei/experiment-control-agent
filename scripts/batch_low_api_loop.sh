#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-900}"
MIN_CYCLE_GAP_SECONDS="${MIN_CYCLE_GAP_SECONDS:-3600}"
STATE_DIR="$BASE_DIR/runtime/batch_low_api_supervisor"
LOG_FILE="$BASE_DIR/logs/batch_low_api_supervisor.log"
mkdir -p "$STATE_DIR" "$BASE_DIR/logs"

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG_FILE"
}

last_cycle_epoch() {
  cat "$STATE_DIR/last_cycle_epoch" 2>/dev/null || echo 0
}

record_cycle_epoch() {
  date '+%s' > "$STATE_DIR/last_cycle_epoch"
}

training_running() {
  local count
  count="$("$BASE_DIR/scripts/list_active_jobs.py" --count 2>/dev/null || echo 0)"
  [[ "$count" =~ ^[0-9]+$ ]] && (( count > 0 ))
}

cycle_running() {
  ps -eo args= | grep -E "$BASE_DIR/scripts/run_batch_low_api_cycle.sh|codex exec .* -C $BASE_DIR" | grep -v grep >/dev/null 2>&1
}

log "low-API batch supervisor started"

while true; do
  [[ -f "$BASE_DIR/runtime/STOP" ]] && log "STOP file detected; exiting." && exit 0
  [[ -f "$BASE_DIR/runtime/PAUSE" ]] && sleep "$CHECK_INTERVAL_SECONDS" && continue

  mode="$(cat "$BASE_DIR/runtime/EXECUTION_MODE" 2>/dev/null || echo manual)"
  [[ "$mode" != "batch_low_api" ]] && log "EXECUTION_MODE=$mode; exiting." && exit 0
  cycle_running && sleep "$CHECK_INTERVAL_SECONDS" && continue

  if training_running; then
    count="$("$BASE_DIR/scripts/list_active_jobs.py" --count 2>/dev/null || echo unknown)"
    printf 'waiting-for-training active_jobs=%s\n' "$count" > "$STATE_DIR/state"
    sleep "$CHECK_INTERVAL_SECONDS"
    continue
  fi

  now="$(date '+%s')"
  current_sig="$("$PYTHON_BIN" "$BASE_DIR/scripts/compute_signature.py")"
  previous_sig="$(cat "$STATE_DIR/result.sha" 2>/dev/null || true)"
  reason=""
  if [[ -z "$previous_sig" ]]; then
    reason="initial-no-active-training"
  elif [[ "$current_sig" != "$previous_sig" ]]; then
    reason="batch-results-changed"
  fi

  if [[ -n "$reason" && $((now - $(last_cycle_epoch))) -ge "$MIN_CYCLE_GAP_SECONDS" ]]; then
    log "triggering one low-API planning cycle: reason=$reason"
    printf 'running-planning reason=%s\n' "$reason" > "$STATE_DIR/state"
    record_cycle_epoch
    set +e
    HONOR_PAUSE=1 "$BASE_DIR/scripts/run_batch_low_api_cycle.sh"
    status=$?
    set -e
    log "low-API cycle exited with status=$status"
    if [[ "$status" -eq 0 ]]; then
      "$PYTHON_BIN" "$BASE_DIR/scripts/compute_signature.py" > "$STATE_DIR/result.sha" || true
      printf 'idle-after-success\n' > "$STATE_DIR/state"
    elif [[ "$status" -eq 2 ]]; then
      exit 2
    else
      printf 'last-cycle-failed status=%s\n' "$status" > "$STATE_DIR/state"
    fi
  fi

  sleep "$CHECK_INTERVAL_SECONDS"
done
