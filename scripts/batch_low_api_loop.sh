#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"
CONFIG_VALUE="$BASE_DIR/scripts/config_value.py"

cfg() {
  "$PYTHON_BIN" "$CONFIG_VALUE" "$1" "${2:-}"
}

CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-$(cfg supervisor.check_interval_seconds 900)}"
MIN_CYCLE_GAP_SECONDS="${MIN_CYCLE_GAP_SECONDS:-$(cfg supervisor.min_cycle_gap_seconds 3600)}"
RETRY_BASE_SECONDS="${RETRY_BASE_SECONDS:-$(cfg supervisor.retry_base_seconds 300)}"
RETRY_MAX_SECONDS="${RETRY_MAX_SECONDS:-$(cfg supervisor.retry_max_seconds 3600)}"

PRIMARY_CODEX_MODEL="${PRIMARY_CODEX_MODEL:-$(cfg codex.default_model '')}"
PRIMARY_CODEX_REASONING_EFFORT="${PRIMARY_CODEX_REASONING_EFFORT:-$(cfg codex.default_reasoning_effort '')}"
FALLBACK_AFTER_FAILURES="${FALLBACK_AFTER_FAILURES:-$(cfg codex.fallback_after_failures 3)}"
FALLBACK_CODEX_MODEL="${FALLBACK_CODEX_MODEL:-$(cfg codex.fallback_model "$PRIMARY_CODEX_MODEL")}"
FALLBACK_CODEX_REASONING_EFFORT="${FALLBACK_CODEX_REASONING_EFFORT:-$(cfg codex.fallback_reasoning_effort "$PRIMARY_CODEX_REASONING_EFFORT")}"
SECONDARY_FALLBACK_AFTER_FAILURES="${SECONDARY_FALLBACK_AFTER_FAILURES:-$(cfg codex.secondary_fallback_after_failures 5)}"
SECONDARY_FALLBACK_CODEX_MODEL="${SECONDARY_FALLBACK_CODEX_MODEL:-$(cfg codex.secondary_fallback_model "$FALLBACK_CODEX_MODEL")}"
SECONDARY_FALLBACK_CODEX_REASONING_EFFORT="${SECONDARY_FALLBACK_CODEX_REASONING_EFFORT:-$(cfg codex.secondary_fallback_reasoning_effort "$FALLBACK_CODEX_REASONING_EFFORT")}"

ENABLE_SUPPLEMENTAL_BATCH="${ENABLE_SUPPLEMENTAL_BATCH:-$(cfg batch.supplemental.enabled true)}"
SUPPLEMENTAL_MIN_ACTIVE_SECONDS="${SUPPLEMENTAL_MIN_ACTIVE_SECONDS:-$(cfg batch.supplemental.min_active_seconds 7200)}"
SUPPLEMENTAL_MIN_CYCLE_GAP_SECONDS="${SUPPLEMENTAL_MIN_CYCLE_GAP_SECONDS:-$(cfg batch.supplemental.min_cycle_gap_seconds 14400)}"
SUPPLEMENTAL_RESULT_CHANGE_GAP_SECONDS="${SUPPLEMENTAL_RESULT_CHANGE_GAP_SECONDS:-$(cfg batch.supplemental.result_change_gap_seconds 1800)}"
SUPPLEMENTAL_MIN_IDLE_GPUS="${SUPPLEMENTAL_MIN_IDLE_GPUS:-$(cfg batch.supplemental.min_idle_gpus 4)}"
SUPPLEMENTAL_IDLE_GPU_MEMORY_MAX_MB="${SUPPLEMENTAL_IDLE_GPU_MEMORY_MAX_MB:-$(cfg batch.supplemental.idle_gpu_memory_max_mb 1000)}"
SUPPLEMENTAL_IDLE_GPU_UTIL_MAX="${SUPPLEMENTAL_IDLE_GPU_UTIL_MAX:-$(cfg batch.supplemental.idle_gpu_util_max 10)}"

STATE_DIR="$BASE_DIR/runtime/batch_low_api_supervisor"
LOG_FILE="$BASE_DIR/logs/batch_low_api_supervisor.log"
mkdir -p "$STATE_DIR" "$BASE_DIR/logs"

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG_FILE"
}

read_int_file() {
  local path="$1"
  local default_value="$2"
  local value=""
  if [[ -f "$path" ]]; then
    value="$(tr -d '[:space:]' < "$path")"
    [[ "$value" =~ ^[0-9]+$ ]] && echo "$value" && return 0
  fi
  echo "$default_value"
}

last_cycle_epoch() {
  read_int_file "$STATE_DIR/last_cycle_epoch" 0
}

last_supplemental_epoch() {
  read_int_file "$STATE_DIR/last_supplemental_epoch" 0
}

retry_count() {
  read_int_file "$STATE_DIR/retry_count" 0
}

retry_after_epoch() {
  read_int_file "$STATE_DIR/retry_after_epoch" 0
}

record_cycle_epoch() {
  date '+%s' > "$STATE_DIR/last_cycle_epoch"
}

record_supplemental_epoch() {
  date '+%s' > "$STATE_DIR/last_supplemental_epoch"
}

training_running() {
  local count
  count="$("$BASE_DIR/scripts/list_active_jobs.py" --count 2>/dev/null || echo 0)"
  [[ "$count" =~ ^[0-9]+$ ]] && (( count > 0 ))
}

active_job_count() {
  local count
  count="$("$BASE_DIR/scripts/list_active_jobs.py" --count 2>/dev/null || echo unknown)"
  [[ "$count" =~ ^[0-9]+$ ]] && echo "$count" || echo unknown
}

cycle_running() {
  ps -eo args= | grep -E "$BASE_DIR/scripts/run_batch_low_api_cycle.sh|codex exec .* -C $BASE_DIR" | grep -v grep >/dev/null 2>&1
}

compute_sig() {
  "$PYTHON_BIN" "$BASE_DIR/scripts/compute_signature.py"
}

save_current_sig() {
  compute_sig > "$STATE_DIR/result.sha"
}

retry_delay_seconds() {
  local count="$1"
  local delay="$RETRY_BASE_SECONDS"
  local i
  for ((i = 1; i < count; i++)); do
    delay=$((delay * 2))
    (( delay >= RETRY_MAX_SECONDS )) && delay="$RETRY_MAX_SECONDS" && break
  done
  (( delay > RETRY_MAX_SECONDS )) && delay="$RETRY_MAX_SECONDS"
  echo "$delay"
}

clear_retry_state() {
  rm -f \
    "$STATE_DIR/retry_count" \
    "$STATE_DIR/retry_after_epoch" \
    "$STATE_DIR/pending_reason" \
    "$STATE_DIR/pending_sig" \
    "$STATE_DIR/pending_cycle_kind" \
    "$STATE_DIR/last_failure_status" \
    "$STATE_DIR/active_model" \
    "$STATE_DIR/active_reasoning_effort" \
    "$STATE_DIR/active_profile"
}

schedule_retry() {
  local status="$1"
  local reason="$2"
  local current_sig="$3"
  local cycle_kind="$4"
  local count delay retry_after

  count=$(( $(retry_count) + 1 ))
  delay="$(retry_delay_seconds "$count")"
  retry_after=$(( $(date '+%s') + delay ))
  printf '%s\n' "$count" > "$STATE_DIR/retry_count"
  printf '%s\n' "$retry_after" > "$STATE_DIR/retry_after_epoch"
  printf '%s\n' "$reason" > "$STATE_DIR/pending_reason"
  printf '%s\n' "$current_sig" > "$STATE_DIR/pending_sig"
  printf '%s\n' "$cycle_kind" > "$STATE_DIR/pending_cycle_kind"
  printf '%s\n' "$status" > "$STATE_DIR/last_failure_status"
  printf 'pending-retry kind=%s status=%s reason=%s attempt=%s retry_after_epoch=%s\n' \
    "$cycle_kind" "$status" "$reason" "$count" "$retry_after" > "$STATE_DIR/state"
  log "planning cycle failed; pending retry: kind=$cycle_kind reason=$reason status=$status attempt=$count delay=${delay}s"
}

pending_cycle_kind() {
  cat "$STATE_DIR/pending_cycle_kind" 2>/dev/null || echo normal
}

select_codex_profile() {
  local failures="$1"
  SELECTED_CODEX_MODEL="$PRIMARY_CODEX_MODEL"
  SELECTED_CODEX_REASONING_EFFORT="$PRIMARY_CODEX_REASONING_EFFORT"
  SELECTED_CODEX_PROFILE="primary"
  if (( failures >= SECONDARY_FALLBACK_AFTER_FAILURES )); then
    SELECTED_CODEX_MODEL="$SECONDARY_FALLBACK_CODEX_MODEL"
    SELECTED_CODEX_REASONING_EFFORT="$SECONDARY_FALLBACK_CODEX_REASONING_EFFORT"
    SELECTED_CODEX_PROFILE="secondary-fallback"
  elif (( failures >= FALLBACK_AFTER_FAILURES )); then
    SELECTED_CODEX_MODEL="$FALLBACK_CODEX_MODEL"
    SELECTED_CODEX_REASONING_EFFORT="$FALLBACK_CODEX_REASONING_EFFORT"
    SELECTED_CODEX_PROFILE="fallback"
  fi
  printf '%s\n' "$SELECTED_CODEX_MODEL" > "$STATE_DIR/active_model"
  printf '%s\n' "$SELECTED_CODEX_REASONING_EFFORT" > "$STATE_DIR/active_reasoning_effort"
  printf '%s\n' "$SELECTED_CODEX_PROFILE" > "$STATE_DIR/active_profile"
}

idle_gpu_indexes() {
  command -v nvidia-smi >/dev/null 2>&1 || return 0
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | \
    awk -F, -v mem_max="$SUPPLEMENTAL_IDLE_GPU_MEMORY_MAX_MB" -v util_max="$SUPPLEMENTAL_IDLE_GPU_UTIL_MAX" '
      {
        idx=$1; mem=$2; util=$3
        gsub(/^[ \t]+|[ \t]+$/, "", idx)
        gsub(/^[ \t]+|[ \t]+$/, "", mem)
        gsub(/^[ \t]+|[ \t]+$/, "", util)
        if (mem + 0 <= mem_max && util + 0 <= util_max) {
          if (out != "") out=out ","
          out=out idx
        }
      }
      END { print out }
    '
}

idle_gpu_count() {
  local indexes="$1"
  [[ -z "$indexes" ]] && echo 0 || awk -F, '{print NF}' <<< "$indexes"
}

active_job_stats() {
  local jobs_json
  jobs_json="$("$BASE_DIR/scripts/list_active_jobs.py" --json 2>/dev/null || echo '[]')"
  "$PYTHON_BIN" - "$SUPPLEMENTAL_MIN_ACTIVE_SECONDS" "$jobs_json" <<'PY'
import json
import sys

threshold = int(sys.argv[1])
try:
    jobs = json.loads(sys.argv[2])
except Exception:
    jobs = []

max_elapsed = 0
long_count = 0
categories = {}
for job in jobs:
    elapsed = int(job.get("elapsed_seconds") or 0)
    category = str(job.get("category") or "")
    max_elapsed = max(max_elapsed, elapsed)
    categories[category] = categories.get(category, 0) + 1
    if elapsed >= threshold:
        long_count += 1

print(f"max_elapsed={max_elapsed}")
print(f"long_count={long_count}")
print("categories=" + ",".join(f"{key}:{categories[key]}" for key in sorted(categories)))
PY
}

stat_value() {
  local key="$1"
  local stats="$2"
  awk -F= -v key="$key" '$1 == key {print $2}' <<< "$stats" | tail -n 1
}

supplemental_reason() {
  local now="$1"
  local active_jobs="$2"
  local idle_indexes_value="$3"
  local idle_count_value="$4"
  local job_stats="$5"
  local current_sig="$6"
  local previous_sig="$7"
  local max_elapsed long_count gap_seconds sig_changed last_epoch last_supplemental

  [[ "$ENABLE_SUPPLEMENTAL_BATCH" != "true" && "$ENABLE_SUPPLEMENTAL_BATCH" != "1" ]] && return 1
  [[ "$active_jobs" == "unknown" || "$active_jobs" == "0" ]] && return 1
  (( idle_count_value < SUPPLEMENTAL_MIN_IDLE_GPUS )) && return 1

  max_elapsed="$(stat_value max_elapsed "$job_stats")"
  long_count="$(stat_value long_count "$job_stats")"
  max_elapsed="${max_elapsed:-0}"
  long_count="${long_count:-0}"
  (( long_count == 0 && max_elapsed < SUPPLEMENTAL_MIN_ACTIVE_SECONDS )) && return 1

  sig_changed=0
  [[ -n "$previous_sig" && "$current_sig" != "$previous_sig" ]] && sig_changed=1
  gap_seconds="$SUPPLEMENTAL_MIN_CYCLE_GAP_SECONDS"
  (( sig_changed == 1 )) && gap_seconds="$SUPPLEMENTAL_RESULT_CHANGE_GAP_SECONDS"

  last_epoch="$(last_cycle_epoch)"
  (( now - last_epoch < gap_seconds )) && return 1
  last_supplemental="$(last_supplemental_epoch)"
  (( now - last_supplemental < gap_seconds )) && return 1

  printf 'supplemental-idle-resource-fill active_jobs=%s idle_gpus=%s idle_indexes=%s max_elapsed=%s long_jobs=%s result_sig_changed=%s gap_seconds=%s' \
    "$active_jobs" "$idle_count_value" "${idle_indexes_value:-none}" "$max_elapsed" "$long_count" "$sig_changed" "$gap_seconds"
}

write_supplemental_context() {
  local reason="$1"
  local active_jobs="$2"
  local idle_indexes_value="$3"
  local idle_count_value="$4"
  local job_stats="$5"
  local current_batch="$BASE_DIR/runtime/batch_low_api/current_batch.md"
  {
    echo "# Supplemental Low-API Batch Context"
    echo
    echo "- timestamp: $(date '+%F %T')"
    echo "- reason: ${reason}"
    echo "- active_jobs: ${active_jobs}"
    echo "- idle_gpu_indexes: ${idle_indexes_value:-none}"
    echo "- idle_gpu_count: ${idle_count_value}"
    echo "- job_stats:"
    sed 's/^/  - /' <<< "$job_stats"
    echo
    echo "## Required Behavior"
    echo
    echo "- This is supplemental, not a normal batch-boundary cycle."
    echo "- Do not stop, restart, modify, or overwrite active jobs."
    echo "- Launch only independent work that can use idle resources safely."
    echo "- If resources are left idle, document why in the new plan."
    echo "- Exit after launch and a short startup check."
    echo
    echo "## Current Batch"
    if [[ -f "$current_batch" ]]; then
      sed -n '1,120p' "$current_batch"
    else
      echo "No current batch pointer exists."
    fi
    echo
    echo "## Active Managed Jobs"
    "$BASE_DIR/scripts/list_active_jobs.py" 2>/dev/null || true
  } > "$STATE_DIR/supplemental_context.md"
}

run_planning_cycle() {
  local reason="$1"
  local current_sig="$2"
  local cycle_kind="$3"
  local failures="$4"
  local status

  select_codex_profile "$failures"
  log "triggering low-API planning cycle: kind=$cycle_kind reason=$reason failures=$failures profile=$SELECTED_CODEX_PROFILE model=${SELECTED_CODEX_MODEL:-config-default} effort=${SELECTED_CODEX_REASONING_EFFORT:-config-default}"
  printf 'running-planning kind=%s reason=%s\n' "$cycle_kind" "$reason" > "$STATE_DIR/state"
  record_cycle_epoch
  [[ "$cycle_kind" == "supplemental" ]] && record_supplemental_epoch

  set +e
  HONOR_PAUSE=1 \
    SUPPLEMENTAL_BATCH="$([[ "$cycle_kind" == "supplemental" ]] && echo 1 || echo 0)" \
    CODEX_MODEL_OVERRIDE="$SELECTED_CODEX_MODEL" \
    CODEX_REASONING_EFFORT_OVERRIDE="$SELECTED_CODEX_REASONING_EFFORT" \
    "$BASE_DIR/scripts/run_batch_low_api_cycle.sh"
  status=$?
  set -e

  if [[ "$cycle_kind" == "supplemental" && -f "$STATE_DIR/supplemental_context.md" ]]; then
    cp "$STATE_DIR/supplemental_context.md" "$STATE_DIR/last_supplemental_context.md" 2>/dev/null || true
    rm -f "$STATE_DIR/supplemental_context.md"
  fi

  log "low-API cycle exited with status=$status kind=$cycle_kind reason=$reason"
  if [[ "$status" -eq 0 ]]; then
    save_current_sig
    clear_retry_state
    printf 'idle-after-success kind=%s\n' "$cycle_kind" > "$STATE_DIR/state"
  elif [[ "$status" -eq 2 ]]; then
    log "auth missing; exiting supervisor."
    exit 2
  else
    schedule_retry "$status" "$reason" "$current_sig" "$cycle_kind"
  fi
}

log "low-API batch supervisor started: check=${CHECK_INTERVAL_SECONDS}s min_gap=${MIN_CYCLE_GAP_SECONDS}s retry_base=${RETRY_BASE_SECONDS}s retry_max=${RETRY_MAX_SECONDS}s supplemental=${ENABLE_SUPPLEMENTAL_BATCH}"

while true; do
  [[ -f "$BASE_DIR/runtime/STOP" ]] && log "STOP file detected; exiting." && exit 0
  [[ -f "$BASE_DIR/runtime/PAUSE" ]] && sleep "$CHECK_INTERVAL_SECONDS" && continue

  mode="$(cat "$BASE_DIR/runtime/EXECUTION_MODE" 2>/dev/null || echo manual)"
  [[ "$mode" != "batch_low_api" ]] && log "EXECUTION_MODE=$mode; exiting." && exit 0
  cycle_running && sleep "$CHECK_INTERVAL_SECONDS" && continue

  now="$(date '+%s')"
  retry_after="$(retry_after_epoch)"
  retry_count_now="$(retry_count)"
  if (( retry_count_now > 0 )); then
    if (( retry_after > now )); then
      printf 'pending-retry remaining_seconds=%s\n' "$((retry_after - now))" > "$STATE_DIR/state"
      sleep "$CHECK_INTERVAL_SECONDS"
      continue
    fi
    reason="$(cat "$STATE_DIR/pending_reason" 2>/dev/null || echo retry)"
    current_sig="$(cat "$STATE_DIR/pending_sig" 2>/dev/null || compute_sig)"
    run_planning_cycle "$reason" "$current_sig" "$(pending_cycle_kind)" "$retry_count_now"
    sleep "$CHECK_INTERVAL_SECONDS"
    continue
  fi

  if training_running; then
    active_jobs="$(active_job_count)"
    current_sig="$(compute_sig)"
    previous_sig="$(cat "$STATE_DIR/result.sha" 2>/dev/null || true)"
    idle_indexes_value="$(idle_gpu_indexes || true)"
    idle_count_value="$(idle_gpu_count "$idle_indexes_value")"
    job_stats="$(active_job_stats)"
    reason="$(supplemental_reason "$now" "$active_jobs" "$idle_indexes_value" "$idle_count_value" "$job_stats" "$current_sig" "$previous_sig" || true)"
    if [[ -n "$reason" ]]; then
      write_supplemental_context "$reason" "$active_jobs" "$idle_indexes_value" "$idle_count_value" "$job_stats"
      run_planning_cycle "$reason" "$current_sig" "supplemental" 0
      sleep "$CHECK_INTERVAL_SECONDS"
      continue
    fi
    printf 'waiting-for-training active_jobs=%s idle_gpus=%s supplemental_enabled=%s\n' "$active_jobs" "$idle_count_value" "$ENABLE_SUPPLEMENTAL_BATCH" > "$STATE_DIR/state"
    sleep "$CHECK_INTERVAL_SECONDS"
    continue
  fi

  current_sig="$(compute_sig)"
  previous_sig="$(cat "$STATE_DIR/result.sha" 2>/dev/null || true)"
  reason=""
  [[ -z "$previous_sig" ]] && reason="initial-no-active-training"
  [[ -n "$previous_sig" && "$current_sig" != "$previous_sig" ]] && reason="batch-results-changed"

  if [[ -n "$reason" && $((now - $(last_cycle_epoch))) -ge "$MIN_CYCLE_GAP_SECONDS" ]]; then
    run_planning_cycle "$reason" "$current_sig" "normal" 0
  fi

  sleep "$CHECK_INTERVAL_SECONDS"
done
