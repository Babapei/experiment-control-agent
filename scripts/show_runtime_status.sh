#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

echo "== config =="
echo "config=$("$PYTHON_BIN" - <<'PY'
from agent_core.config import config_path
print(config_path())
PY
)"

echo
echo "== runtime mode =="
for file in AGENT_MODE EXECUTION_MODE BATCH_PROFILE; do
  printf '%s=' "$file"
  cat "$BASE_DIR/runtime/$file" 2>/dev/null || printf 'missing\n'
done
[[ -f "$BASE_DIR/runtime/PAUSE" ]] && echo "PAUSE=present" || echo "PAUSE=absent"
[[ -f "$BASE_DIR/runtime/STOP" ]] && echo "STOP=present" || echo "STOP=absent"
[[ -f "$BASE_DIR/runtime/REVIEW_REQUIRED" ]] && echo "REVIEW_REQUIRED=present" || echo "REVIEW_REQUIRED=absent"

echo
echo "== active supervisors/cycles =="
ps -eo pid,ppid,stat,etime,args | grep -E "codex exec|run_codex_cycle|run_batch_low_api_cycle|event_agent_loop|batch_low_api_loop|agent_loop.sh" | grep -v grep || true

echo
echo "== tmux sessions =="
tmux list-sessions 2>/dev/null || true

echo
echo "== active managed jobs =="
"$BASE_DIR/scripts/list_active_jobs.py" || true

echo
"$BASE_DIR/scripts/validate_agent_state.py" || true

echo
echo "== current_status.md =="
sed -n '1,180p' "$BASE_DIR/runtime/current_status.md" 2>/dev/null || true
