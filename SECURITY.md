# Security

Do not report private API keys, access tokens, credentials, private datasets, or
unpublished research material in public issues.

## Sensitive Files

The following should remain local and untracked:

- `.codex-home/`
- `configs/project.json` when it contains private paths or model provider data
- `runtime/`
- `logs/`
- `workspaces/`
- `originals/`
- checkpoints, datasets, generated artifacts, and raw experiment outputs

## Before Publishing

Run:

```bash
scripts/run_checks.sh
python3 scripts/doctor.py --strict
git status --short
```

Review `.gitignore` and `git status` before pushing to a public remote.

