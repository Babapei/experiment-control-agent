#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
kind="${1:-}"
value="${2:-}"

case "$kind" in
  agent)
    file="$BASE_DIR/runtime/AGENT_MODE"
    ;;
  execution)
    file="$BASE_DIR/runtime/EXECUTION_MODE"
    ;;
  batch_profile)
    file="$BASE_DIR/runtime/BATCH_PROFILE"
    ;;
  *)
    echo "Usage: $0 {agent|execution|batch_profile} VALUE" >&2
    exit 2
    ;;
esac

[[ -z "$value" ]] && echo "missing value" >&2 && exit 2
mkdir -p "$BASE_DIR/runtime"
printf '%s\n' "$value" > "$file"
echo "$(basename "$file")=$value"

