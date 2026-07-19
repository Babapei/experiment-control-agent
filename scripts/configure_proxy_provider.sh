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
CONFIG_FILE="$CODEX_HOME/config.toml"
BACKUP_DIR="$CODEX_HOME/backups"
mkdir -p "$CODEX_HOME" "$BACKUP_DIR"

conda_init="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" codex.conda_init '')"
conda_env="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" codex.conda_env '')"
if [[ -n "$conda_init" && -f "$conda_init" ]]; then
  # shellcheck source=/dev/null
  source "$conda_init"
fi
if [[ -n "$conda_env" ]]; then
  conda activate "$conda_env"
fi

provider_id="${CODEX_MODEL_PROVIDER:-proxy}"
provider_name="${CODEX_MODEL_PROVIDER_NAME:-API Proxy}"
default_model="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" codex.default_model gpt-5)"
default_effort="$("$PYTHON_BIN" "$BASE_DIR/scripts/config_value.py" codex.default_reasoning_effort high)"

read -r -p "Provider id [$provider_id]: " input_provider_id
provider_id="${input_provider_id:-$provider_id}"
read -r -p "Provider display name [$provider_name]: " input_provider_name
provider_name="${input_provider_name:-$provider_name}"
read -r -p "Base URL, e.g. https://example.com/v1: " base_url
[[ -z "$base_url" ]] && echo "Base URL is required." >&2 && exit 1
read -r -p "Model name [$default_model]: " model
model="${model:-$default_model}"
read -r -p "Reasoning effort [$default_effort]: " effort
effort="${effort:-$default_effort}"

if [[ -f "$CONFIG_FILE" ]]; then
  cp -p "$CONFIG_FILE" "$BACKUP_DIR/config.toml.$(date '+%Y%m%d_%H%M%S').bak"
fi

cat > "$CONFIG_FILE" <<EOF
model_provider = "$provider_id"
model = "$model"
model_reasoning_effort = "$effort"
disable_response_storage = true

[model_providers.$provider_id]
name = "$provider_name"
base_url = "$base_url"
wire_api = "responses"
requires_openai_auth = true
supports_websockets = false
EOF

chmod 600 "$CONFIG_FILE"
echo "Wrote $CONFIG_FILE"

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  printf '%s' "$OPENAI_API_KEY" | codex login --with-api-key
else
  read -r -s -p "Enter API key: " api_key
  echo
  [[ -z "$api_key" ]] && echo "API key is empty" >&2 && exit 1
  printf '%s' "$api_key" | codex login --with-api-key
  unset api_key
fi

codex login status

