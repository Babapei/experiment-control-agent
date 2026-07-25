# Experiment Control Agent

A configurable server-side LLM control plane for planning, launching, and
monitoring long-running research experiments.

The default planning provider adapter uses `codex exec`, but the repository is
structured around a generic control-plane idea: an LLM planner reads experiment
state, launches ordinary long-running jobs, records evidence, and waits until a
meaningful boundary before spending more API calls.

## What This Is

- A scaffold for server-side experiment management.
- A low-API planning loop around long-running jobs.
- A profile-driven way to separate project policy from generic supervisors.
- A runtime ledger system for batches, status, and evidence paths.

Use it when you already have experiment scripts and want a cautious LLM planner
to decide what to run next, track evidence, and avoid spending API calls while
jobs are still running.

## What This Is Not

- A training framework.
- A replacement for your experiment scripts.
- A domain-specific paper-recovery agent.
- A place to store datasets, checkpoints, logs, credentials, or private notes.

## First Decisions

| Question | Recommended Choice |
| --- | --- |
| Do you just want to see the repository work? | Run the toy example. |
| Are you configuring a real project for the first time? | Use `manual` mode. |
| Are your jobs long-running and expensive? | Use `batch_low_api`. |
| Do you need fast reaction to state changes? | Use `event` after setup is stable. |
| Do you need zero automatic API calls? | Use `manual` and keep `runtime/PAUSE` present. |

## Start Here

If you are new, run the CPU-only toy example first:

```bash
git clone git@github.com:Babapei/experiment-control-agent.git
cd experiment-control-agent
scripts/run_checks.sh

cp examples/toy-sleep-experiment/project.json configs/project.json
python3 scripts/bootstrap_layout.py
examples/toy-sleep-experiment/run_toy_batch.sh
scripts/list_active_jobs.py
```

After a few seconds:

```bash
find examples/toy-sleep-experiment/results -name completed.json -print
scripts/show_runtime_status.sh
```

Full walkthrough: [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md).

## Documentation

You do not need to read every file before trying the agent.

Recommended first path:

1. [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md): run the toy demo.
2. [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md): understand how to adapt it.
3. [`docs/FEATURES_AND_MODES.md`](docs/FEATURES_AND_MODES.md): choose a mode.
4. [`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md): edit fields safely.
5. [`docs/PROFILE_AUTHORING.md`](docs/PROFILE_AUTHORING.md): write project
   policy and cycle context.

Use these when needed:

- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md): common warnings and
  failure modes.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): control flow and runtime
  state model.
- [`docs/TRUST_MODEL.md`](docs/TRUST_MODEL.md): enforced safeguards, advisory
  profile boundaries, and safe deployment assumptions.
- [`docs/AUTH_SETUP.md`](docs/AUTH_SETUP.md): current Codex CLI provider setup.
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) and [`SECURITY.md`](SECURITY.md):
  public release and sensitive-file checks.

## Repository Layout

- `agent_core/`: shared Python helpers.
- `scripts/`: supervisors, runners, validators, and diagnostics.
- `prompts/`: generic prompt bodies.
- `configs/project.example.json`: default config template.
- `profiles/default/`: generic placeholder profile.
- `profiles/example-ea-sbm/`: sanitized profile example.
- `examples/toy-sleep-experiment/`: CPU-only demo project.
- `templates/`: reusable status, lane, batch, and dashboard templates.
- `runtime/`: local mutable state, ignored by git.
- `logs/`: local logs, ignored by git.

## Planning Provider

The config has a `provider` section for the planner execution boundary. The
bundled adapter is `type: "codex"`, backed by the Codex CLI. Codex-specific
home, auth, model, and fallback settings remain in the `codex` section for
compatibility.

## Execution Modes

- `manual`: no automatic supervisor; run cycles by hand.
- `interval`: run planning cycles on a fixed interval.
- `event`: run planning cycles when watched state changes or on heartbeat.
- `batch_low_api`: plan one long batch, run jobs without more LLM calls, then
  plan again only at a result boundary.

## Core Commands

```bash
python3 scripts/bootstrap_layout.py
python3 scripts/doctor.py
python3 scripts/inspect_config.py
python3 scripts/render_prompt.py batch_low_api
scripts/launch_batch_job.sh
scripts/list_active_jobs.py
scripts/show_runtime_status.sh
scripts/run_checks.sh
```

## Design Principles

- Keep core scripts generic and conservative.
- Put domain knowledge in profiles.
- Let the agent own research judgment: hypotheses, candidate methods,
  experiment design, prioritization, interpretation, and mode-switching
  decisions should come from the planner and project profile, not from
  hardcoded core workflows.
- Let the framework own state and boundaries: runtime ledgers, evidence paths,
  batch/job status, pause/stop behavior, and safety checks should be explicit
  and recoverable.
- Use explicit logs, output roots, and batch manifests.
- Treat original/historical workspaces as read-only unless a profile says
  otherwise.
- Do not overwrite experiment evidence.
- Keep API usage at planning boundaries when using `batch_low_api`.

## Public Release Safety

Before pushing or tagging:

```bash
scripts/run_checks.sh
python3 scripts/doctor.py
git status --short
```

Do not commit `configs/project.json` if it contains private paths, API provider
details, unpublished target metrics, or project-specific notes.
