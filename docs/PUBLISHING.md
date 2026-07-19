# Publishing Checklist

- Remove `configs/project.json` if it contains machine paths.
- Keep `.codex-home/`, `runtime/`, `logs/`, `workspaces/`, and `originals/` out
  of git.
- Do not commit API keys, access tokens, private manuscripts, raw datasets,
  checkpoints, or historical experiment logs.
- Add a license before making the repository public.
- Replace example profile text with either sanitized examples or a separate
  private project profile.
- Run `scripts/run_checks.sh` before tagging or pushing a release.
