#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-900}"
HEARTBEAT_SECONDS="${HEARTBEAT_SECONDS:-3600}"
MIN_CYCLE_GAP_SECONDS="${MIN_CYCLE_GAP_SECONDS:-300}"
STATE_DIR="$BASE_DIR/runtime/event_supervisor"
LOG_FILE="$BASE_DIR/logs/event_supervisor.log"
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

cycle_running() {
  ps -eo args= | grep -E "$BASE_DIR/scripts/run_codex_cycle.sh|codex exec .* -C $BASE_DIR" | grep -v grep >/dev/null 2>&1
}

log "event supervisor started"

while true; do
  [[ -f "$BASE_DIR/runtime/STOP" ]] && log "STOP file detected; exiting." && exit 0
  [[ -f "$BASE_DIR/runtime/PAUSE" ]] && sleep "$CHECK_INTERVAL_SECONDS" && continue

  mode="$(cat "$BASE_DIR/runtime/EXECUTION_MODE" 2>/dev/null || echo event)"
  case "$mode" in
    event)
      ;;
    interval)
      log "EXECUTION_MODE=interval detected; handing off."
      exec "$BASE_DIR/scripts/agent_loop.sh"
      ;;
    batch_low_api)
      log "EXECUTION_MODE=batch_low_api detected; handing off."
      exec "$BASE_DIR/scripts/batch_low_api_loop.sh"
      ;;
    manual)
      sleep "$CHECK_INTERVAL_SECONDS"
      continue
      ;;
    *)
      log "unsupported EXECUTION_MODE=$mode; exiting."
      exit 1
      ;;
  esac

  now="$(date '+%s')"
  current_sig="$("$PYTHON_BIN" "$BASE_DIR/scripts/compute_signature.py")"
  previous_sig="$(cat "$STATE_DIR/event.sha" 2>/dev/null || true)"
  reason=""

  if [[ -z "$previous_sig" ]]; then
    printf '%s\n' "$current_sig" > "$STATE_DIR/event.sha"
    record_cycle_epoch
    log "baseline event signature recorded"
  elif [[ "$current_sig" != "$previous_sig" ]]; then
    reason="event-signature-changed"
  elif (( now - $(last_cycle_epoch) >= HEARTBEAT_SECONDS )); then
    reason="heartbeat"
  fi

  if [[ -n "$reason" && $((now - $(last_cycle_epoch))) -ge "$MIN_CYCLE_GAP_SECONDS" ]] && ! cycle_running; then
    log "triggering Codex cycle: reason=$reason"
    printf '%s\n' "$current_sig" > "$STATE_DIR/event.sha"
    record_cycle_epoch
    set +e
    "$BASE_DIR/scripts/run_codex_cycle.sh"
    status=$?
    set -e
    log "Codex cycle exited with status=$status"
    [[ "$status" -eq 2 ]] && exit 2
    "$PYTHON_BIN" "$BASE_DIR/scripts/compute_signature.py" > "$STATE_DIR/event.sha" || true
  fi

  sleep "$CHECK_INTERVAL_SECONDS"
done
