#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

usage() {
  echo "Usage: $0 BATCH_DIR PACKAGE_ID OUTPUT_ROOT LOG_PATH -- COMMAND [ARG ...]" >&2
}

if [[ "$#" -lt 6 ]]; then
  usage
  exit 2
fi

BATCH_DIR="$1"
PACKAGE_ID="$2"
OUTPUT_ROOT="$3"
LOG_PATH="$4"
shift 4

if [[ "${1:-}" != "--" ]]; then
  usage
  exit 2
fi
shift

if [[ "$#" -eq 0 ]]; then
  usage
  exit 2
fi

mkdir -p "$OUTPUT_ROOT" "$(dirname "$LOG_PATH")" "$BATCH_DIR"
if [[ -e "$LOG_PATH" ]]; then
  echo "Refusing to overwrite existing log: $LOG_PATH" >&2
  exit 1
fi

printf -v COMMAND_TEXT '%q ' "$@"

(
  set +e
  "$@" > "$LOG_PATH" 2>&1
  exit_code=$?
  status="completed"
  [[ "$exit_code" -ne 0 ]] && status="failed"
  record_pid="${BASHPID:-$$}"
  "$PYTHON_BIN" "$BASE_DIR/scripts/batch_status.py" record \
    --batch-dir "$BATCH_DIR" \
    --package-id "$PACKAGE_ID" \
    --status "$status" \
    --pid "$record_pid" \
    --exit-code "$exit_code" \
    --output-root "$OUTPUT_ROOT" \
    --log-path "$LOG_PATH" \
    --command "$COMMAND_TEXT" >/dev/null || true
  exit "$exit_code"
) &

pid=$!
"$PYTHON_BIN" "$BASE_DIR/scripts/batch_status.py" record \
  --batch-dir "$BATCH_DIR" \
  --package-id "$PACKAGE_ID" \
  --status running \
  --pid "$pid" \
  --output-root "$OUTPUT_ROOT" \
  --log-path "$LOG_PATH" \
  --command "$COMMAND_TEXT" >/dev/null

echo "Launched package $PACKAGE_ID pid=$pid"
echo "Log: $LOG_PATH"
