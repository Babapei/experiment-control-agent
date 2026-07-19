#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"
SESSION_NAME="${1:-$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" supervisor.session_name experiment-control-agent)}"

mode="${EXECUTION_MODE:-$(cat "$BASE_DIR/runtime/EXECUTION_MODE" 2>/dev/null || "$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" modes.default_execution_mode manual)}"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "tmux session already exists: $SESSION_NAME"
  exit 0
fi

case "$mode" in
  event)
    loop_script="$BASE_DIR/scripts/event_agent_loop.sh"
    ;;
  interval)
    loop_script="$BASE_DIR/scripts/agent_loop.sh"
    ;;
  batch_low_api)
    loop_script="$BASE_DIR/scripts/batch_low_api_loop.sh"
    ;;
  manual)
    echo "EXECUTION_MODE=manual does not start a supervisor."
    exit 0
    ;;
  *)
    echo "Unsupported EXECUTION_MODE=$mode" >&2
    exit 1
    ;;
esac

tmux new-session -d -s "$SESSION_NAME" "cd '$BASE_DIR' && '$loop_script'"
echo "Started tmux session: $SESSION_NAME (execution_mode=$mode)"
