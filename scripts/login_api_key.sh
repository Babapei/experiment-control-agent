#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$BASE_DIR:${PYTHONPATH:-}"

codex_home="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" codex.home .codex-home)"
if [[ "$codex_home" != /* ]]; then
  codex_home="$BASE_DIR/$codex_home"
fi
export CODEX_HOME="$codex_home"
mkdir -p "$CODEX_HOME"

conda_init="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" codex.conda_init '')"
conda_env="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" codex.conda_env '')"
if [[ -n "$conda_init" && -f "$conda_init" ]]; then
  # shellcheck source=/dev/null
  source "$conda_init"
fi
if [[ -n "$conda_env" ]]; then
  conda activate "$conda_env"
fi

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  printf '%s' "$OPENAI_API_KEY" | codex login --with-api-key
else
  read -r -s -p "Enter OPENAI_API_KEY: " api_key
  echo
  [[ -z "$api_key" ]] && echo "OPENAI_API_KEY is empty" >&2 && exit 1
  printf '%s' "$api_key" | codex login --with-api-key
  unset api_key
fi

codex login status

