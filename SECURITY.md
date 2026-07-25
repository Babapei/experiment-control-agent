# Security

Do not report private API keys, access tokens, credentials, private datasets, or
unpublished research material in public issues.

Read [`docs/TRUST_MODEL.md`](docs/TRUST_MODEL.md) before enabling automatic
planning cycles. In particular, the bundled Codex runner uses a sandbox-bypass
flag and must run only in a deliberately scoped trusted environment.

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
