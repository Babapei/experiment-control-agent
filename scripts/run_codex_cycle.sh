#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG_VALUE="$BASE_DIR/scripts/config_value.py"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

mkdir -p "$BASE_DIR/logs" "$BASE_DIR/runtime"

codex_home="$("$PYTHON_BIN" "$CONFIG_VALUE" codex.home .codex-home)"
if [[ "$codex_home" != /* ]]; then
  codex_home="$BASE_DIR/$codex_home"
fi
export CODEX_HOME="$codex_home"

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

conda_init="$("$PYTHON_BIN" "$CONFIG_VALUE" codex.conda_init '')"
conda_env="$("$PYTHON_BIN" "$CONFIG_VALUE" codex.conda_env '')"
if [[ -n "$conda_init" && -f "$conda_init" ]]; then
  # shellcheck source=/dev/null
  source "$conda_init"
fi
if [[ -n "$conda_env" ]]; then
  conda activate "$conda_env"
fi

extra_paths="$("$PYTHON_BIN" "$CONFIG_VALUE" codex.extra_path_entries '[]')"
"$PYTHON_BIN" - "$extra_paths" <<'PY' > "$BASE_DIR/runtime/.extra_path_exports"
import json
import sys
items = json.loads(sys.argv[1]) if sys.argv[1] else []
for item in items:
    print(item)
PY
while IFS= read -r path_entry; do
  [[ -n "$path_entry" ]] && export PATH="$PATH:$path_entry"
done < "$BASE_DIR/runtime/.extra_path_exports"
rm -f "$BASE_DIR/runtime/.extra_path_exports"

auth_required="$("$PYTHON_BIN" "$CONFIG_VALUE" codex.auth_required true)"
if [[ "$auth_required" == "true" && ! -f "$CODEX_HOME/auth.json" ]]; then
  echo "[run_codex_cycle] missing Codex auth at $CODEX_HOME/auth.json" | tee -a "$BASE_DIR/logs/runner.log"
  exit 2
fi

STAMP="$(date '+%Y%m%d_%H%M%S')"
JSONL_LOG="$BASE_DIR/logs/cycle_${STAMP}.jsonl"
TEXT_LOG="$BASE_DIR/logs/cycle_${STAMP}.last_message.txt"
CYCLE_TIMEOUT_SECONDS="${CYCLE_TIMEOUT_SECONDS:-$("$PYTHON_BIN" "$CONFIG_VALUE" supervisor.cycle_timeout_seconds 1800)}"

set +e
cat "$BASE_DIR/prompts/cycle_prompt.md" | \
  timeout "$CYCLE_TIMEOUT_SECONDS" \
    codex exec \
      --skip-git-repo-check \
      -C "$BASE_DIR" \
      --dangerously-bypass-approvals-and-sandbox \
      --output-last-message "$TEXT_LOG" \
      --json \
      - \
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
