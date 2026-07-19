# Codex Authentication

The scripts use `codex.home` from `configs/project.json`; by default this is
`.codex-home` under the repo root.

## API Key

```bash
scripts/login_api_key.sh
```

If `OPENAI_API_KEY` is already exported, the script reads it. Otherwise it
prompts silently.

## API Proxy

```bash
scripts/configure_proxy_provider.sh
```

This writes `.codex-home/config.toml` and then runs `codex login --with-api-key`.
Do not commit `.codex-home/`.

