# User Guide

This guide explains how to understand the repository and which document to read
next. It is the best starting point after the toy demo works.

## Mental Model

Experiment Control Agent has three layers:

1. **Core control plane**
   - supervisors
   - planning-cycle runners
   - job detection
   - result signatures
   - runtime ledgers
   - validation and diagnostics

2. **Project profile**
   - research goal
   - writable workspaces
   - read-only originals
   - job regexes
   - watched result files
   - metric and target definitions
   - safety rules

3. **Your existing experiment code**
   - training scripts
   - evaluation scripts
   - data preprocessing
   - scheduler wrappers
   - result aggregators

The agent does not replace your experiment code. It helps an LLM planner manage
that code in bounded cycles.

## Documentation Map

| Need | Read |
| --- | --- |
| Prove the install works | `docs/GETTING_STARTED.md` |
| Understand what this agent can and cannot do | this guide, then `docs/FEATURES_AND_MODES.md` |
| Configure your own project | `docs/CONFIG_REFERENCE.md` and `docs/PROFILE_AUTHORING.md` |
| Debug local/server behavior | `docs/TROUBLESHOOTING.md` |
| Understand internals before modifying core scripts | `docs/ARCHITECTURE.md` |
| Prepare a public fork or release | `docs/PUBLISHING.md` and `SECURITY.md` |

## What A User Configures

Most users should only need to edit:

- `configs/project.json`
- one profile directory under `profiles/<project>/`
- their own experiment repository or scripts outside this control-plane repo

Most users should not need to edit:

- supervisor loops in `scripts/*loop.sh`
- prompt plumbing in `scripts/render_prompt.py`
- runtime validation helpers
- generic templates

If a project needs custom behavior, put the instruction in the project profile
first. Change core code only when the same behavior would be useful across many
projects.

## Typical Adoption Path

### Phase 1: Prove The Installation

Run the toy example. This proves Python scripts, runtime layout, status files,
job detection, and result signatures work without a GPU or LLM auth.

### Phase 2: Map Your Project

Create a private profile and configure:

- where the agent may write;
- which existing workspaces are read-only references;
- how to recognize your training/evaluation jobs;
- which result files prove progress;
- which metrics matter;
- which commands are allowed or preferred.

At this stage, stay in `manual` mode.

### Phase 3: Dry-Run The Planner Context

Render the prompt before launching any automatic supervisor:

```bash
python3 scripts/render_prompt.py batch_low_api | sed -n '1,160p'
```

The rendered prompt should be understandable to a new teammate. If it is vague,
fix the profile before running unattended.

### Phase 4: Run One Controlled Batch

Trigger one low-API cycle manually:

```bash
scripts/run_batch_low_api_cycle.sh
```

Then inspect the plan, manifest, status file, and result artifacts. Do not start
the long-running supervisor until one manual batch produces sensible evidence.

### Phase 5: Start The Server Supervisor

After job detection and result signatures are reliable, use `batch_low_api` for
normal server work.

## Setup Checklist For A Real Project

Create a project profile:

```bash
mkdir -p profiles/my-project
cp profiles/default/AGENTS.project.md profiles/my-project/AGENTS.project.md
cp profiles/default/CYCLE_BRIEF.md profiles/my-project/CYCLE_BRIEF.md
cp configs/project.example.json configs/project.json
```

Edit `configs/project.json`:

- `project.name`
- `codex.home`
- `codex.conda_init`
- `codex.conda_env`
- `codex.extra_path_entries`
- `workspaces`
- `originals`
- `job_detection.managed_hints`
- `job_detection.patterns`
- `results.watch_paths`
- `results.file_patterns`
- `modes.agent_modes`
- `modes.agent_mode_contracts`
- `project_docs`

Edit `profiles/my-project/AGENTS.project.md`:

- what the agent is allowed to do
- what it must not touch
- what counts as progress
- what status labels mean
- how to compare results

Edit `profiles/my-project/CYCLE_BRIEF.md`:

- compact per-cycle objective
- required runtime files to read
- current queues or lanes
- preferred runners
- result interpretation rules

Then run:

```bash
python3 scripts/bootstrap_layout.py
python3 scripts/doctor.py
python3 scripts/render_prompt.py batch_low_api | sed -n '1,120p'
scripts/show_runtime_status.sh
```

## Choosing A First Mode

Start with:

```bash
scripts/set_mode.sh execution manual
```

Use manual mode until `doctor.py`, job detection, and prompt rendering look
right.

Then move to:

```bash
scripts/set_mode.sh execution batch_low_api
```

Use `batch_low_api` as the default server mode for long experiments.

Use `event` only when you are comfortable with more frequent planning calls.

## Ready For Unattended Runs

Before leaving the agent running, confirm:

- What objective mode is active, and what contract defines success?
- Which directories can the agent modify?
- Which commands can it launch?
- How are active jobs detected?
- What files count as completed results?
- Where are logs and batch manifests written?
- How do I pause or stop new planning cycles?
- What API provider, model, and fallback settings are being used?
- Does `runtime/last_cycle_outcome.json` contain the active mode's required
  details after a manual cycle?

If any answer is unclear, keep the project in `manual` mode and improve the
profile/config first.

Also check the actual context sent to the planner:

```bash
python3 scripts/render_prompt.py batch_low_api | sed -n '1,200p'
```

The prompt should be specific enough that a teammate could predict the next
safe action from the same information.

## What To Inspect After A Batch

For every batch, check:

- `runtime/batch_low_api/current_batch.md`
- `runtime/batch_low_api/batches/<id>/plan.md`
- `runtime/batch_low_api/batches/<id>/manifest.tsv`
- `runtime/current_status.md`
- `runtime/research_lanes.md`
- result files under configured `results.watch_paths`
- logs listed in the manifest

## What Good Project Profiles Do

Good profiles are explicit about:

- safe write locations
- read-only references
- exact command families
- result artifacts
- target metrics
- promotion rules
- stopping conditions
- what not to rerun

Weak profiles make the LLM guess. Strong profiles make the LLM schedule.
