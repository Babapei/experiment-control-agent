# Experiment Control Agent

A configurable server-side LLM control plane for planning, launching, and
monitoring long-running research experiments.

The agent is intentionally split into two parts:

- **Core control layer**: tmux supervisors, pause/stop state, batch planning,
  LLM invocation, usage logs, active-job detection, and result-change
  signatures. The current implementation uses `codex exec` as its first
  provider.
- **Project profile**: research objective, workspaces, environment activation,
  managed job patterns, watched result files, metric policy, lane templates, and
  safety rules.

This repository should not contain private credentials, historical logs,
checkpoints, generated datasets, or paper-specific runtime ledgers.

## Quick Start

```bash
cp configs/project.example.json configs/project.json
$EDITOR configs/project.json

python3 scripts/bootstrap_layout.py
python3 scripts/doctor.py
scripts/run_checks.sh
scripts/show_runtime_status.sh

scripts/set_mode.sh agent target_recovery
scripts/set_mode.sh execution batch_low_api
scripts/set_mode.sh batch_profile auto
rm -f runtime/PAUSE
scripts/launch_tmux_agent.sh
```

## Repository Layout

- `agent_core/`: small Python helpers shared by scripts.
- `scripts/`: supervisor, Codex runner, state, validation, and job tools.
- `prompts/`: generic prompts used by `codex exec`.
- `configs/project.example.json`: machine/project configuration template.
- `profiles/default/`: runnable generic placeholder profile.
- `profiles/`: optional example project profiles.
- `templates/`: reusable status, lane, batch, and dashboard templates.
- `runtime/`: local mutable state. Keep it out of git.
- `logs/`: Codex runner/supervisor logs. Keep it out of git.
- `ROADMAP.md`: implementation scope and phase plan.

## Checks

```bash
scripts/run_checks.sh
```

This runs shell syntax checks, Python compilation, unit tests, doctor checks,
runtime validation, and prompt rendering smoke tests.

## Public Release

Before pushing to a public GitHub repository:

```bash
scripts/run_checks.sh
python3 scripts/doctor.py --strict
git status --short
```

Do not commit `configs/project.json` if it contains private paths, API provider
data, or unpublished project details.

## Execution Modes

- `event`: run an LLM planning cycle when jobs/results/tmux state change or on a
  heartbeat.
- `interval`: run an LLM planning cycle on a fixed interval.
- `batch_low_api`: run the LLM only at batch boundaries; training runs without
  further LLM calls.
- `manual`: no automatic supervisor; invoke a cycle by hand.

## Design Principles

- Keep the core generic and conservative.
- Put domain decisions in the project profile, not in shell/Python supervisors.
- Treat long-running training as ordinary processes. The LLM plans, launches,
  records, and later analyzes.
- Never overwrite experiment evidence by default.
- Prefer explicit batch manifests over implicit memory.

## Prompt Rendering

`run_codex_cycle.sh` and `run_batch_low_api_cycle.sh` call
`scripts/render_prompt.py` before invoking `codex exec`. The rendered prompt
prepends the resolved config path, project docs, active modes, batch profile
settings, and manifest schema. This keeps project-specific policy in profiles
while making each planning call self-describing.
