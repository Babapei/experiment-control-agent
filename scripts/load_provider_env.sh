#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

eval "$("$PYTHON_BIN" "$BASE_DIR/scripts/provider_command.py" shell-env)"

if [[ -n "${PROVIDER_CONDA_INIT:-}" && -f "$PROVIDER_CONDA_INIT" ]]; then
  # shellcheck source=/dev/null
  source "$PROVIDER_CONDA_INIT"
fi
if [[ -n "${PROVIDER_CONDA_ENV:-}" ]]; then
  conda activate "$PROVIDER_CONDA_ENV"
fi

if [[ "${CODEX_HOME:-}" != "" ]]; then
  export CODEX_HOME
fi
