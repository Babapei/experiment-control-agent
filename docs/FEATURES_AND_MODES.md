# Features And Modes

This document explains what the agent can do and how to choose a mode.

## Quick Choice

| Situation | Use |
| --- | --- |
| First setup, debugging, or no automatic API calls | `manual` |
| Long-running GPU/server jobs with limited API budget | `batch_low_api` |
| Predictable periodic checks | `interval` |
| Fast reaction to reliable result changes | `event` |

If you are unsure, start in `manual`, render the prompt, run one controlled
`batch_low_api` cycle by hand, and only then start a supervisor.

## Capability Summary

Experiment Control Agent is useful for projects where experiments are ordinary
shell/Python jobs, but the decision of what to run next benefits from an LLM
planner reading the latest status and evidence.

It can:

- render project-specific planner context from config and profile docs;
- call the current planning provider implementation (`codex exec`);
- launch bounded planning cycles;
- detect active jobs using process patterns;
- track result signatures across configured files and runtime state;
- keep human-readable ledgers for status, lanes, journals, plans, and manifests;
- run in manual, interval, event-triggered, or low-API batch modes;
- pause or stop supervisors with runtime files;
- retry transient planning-provider failures and optionally fall back to another
  configured model profile.

It does not:

- train models by itself;
- invent a scheduler for every cluster environment;
- guarantee experimental correctness;
- replace project-specific safety rules;
- store private credentials, datasets, checkpoints, or unpublished logs.

## Core Features

### Bounded Planning Cycles

The LLM planner is called for one bounded cycle. A cycle should inspect state,
make a scheduling decision, launch documented work if appropriate, update
ledgers, and exit.

The supervisors handle repetition. The LLM should not run its own infinite
loop.

### Profile-Driven Project Context

Project-specific decisions live in profiles and `configs/project.json`, not in
core scripts. This includes:

- workspace paths
- environment activation
- job patterns
- result file patterns
- metric definitions
- target rows
- safety rules

### Active Job Detection

`scripts/list_active_jobs.py` reads process state and classifies jobs using
`job_detection.managed_hints` and `job_detection.patterns`.

Use it to answer:

- What managed jobs are running?
- How long have they been running?
- What category are they?
- Which resources do they appear to use?

### Result Signatures

`scripts/compute_signature.py` hashes configured result files, tmux sessions,
and GPU compute apps. Supervisors use this to decide whether meaningful state
changed.

Do not watch noisy logs unless you want frequent wakeups.

### Runtime Ledgers

The agent expects concise runtime files:

- `runtime/current_status.md`
- `runtime/agent_journal.md`
- `runtime/research_lanes.md`
- `runtime/batch_low_api/current_batch.md`
- `runtime/batch_low_api/batches/<id>/plan.md`
- `runtime/batch_low_api/batches/<id>/manifest.tsv`
- `runtime/batch_low_api/batches/<id>/status.tsv`

These files let another planning cycle resume without relying on memory.

### Prompt Rendering

`scripts/render_prompt.py` prepends resolved config context before the generic
prompt body. The planner sees:

- config path
- project name
- agent mode
- execution mode
- batch profile
- project docs
- manifest columns

This is the main visibility tool for new users. If the rendered prompt does not
explain the project clearly, the profile is not ready for unattended use.

### Doctor And Checks

- `python3 scripts/doctor.py`: setup and publish-safety checks.
- `scripts/run_checks.sh`: shell syntax, Python compile, unit tests, doctor,
  runtime validation, and prompt rendering smoke tests.
- `scripts/show_runtime_status.sh`: operational status.

## Mode Axes

The agent uses separate mode files because they answer different questions.

### `AGENT_MODE`

`runtime/AGENT_MODE` means: **what objective should the project pursue?**

Examples:

- `method_exploration`
- `audit_validation`
- `target_recovery`

These values are project-defined. Configure allowed values in
`modes.agent_modes`, and define each mode in `modes.agent_mode_contracts`.

An agent mode is a contract, not just a label. Each mode should define:

- purpose;
- entry conditions;
- required reads;
- allowed actions;
- required artifacts;
- success criteria;
- escalation criteria.

If a mode cannot define those fields clearly, it is not ready to be an
unattended objective mode.

The default public lifecycle is:

- `method_exploration`: early-stage research automation. The planner proposes
  candidate hypotheses or method changes, chooses a cheap validation design,
  runs or prepares a bounded probe, records evidence, and decides whether to
  promote, revise, reject, or continue the route.
- `audit_validation`: trust-building work. The planner reduces one uncertainty
  about data, metrics, runner behavior, provenance, leakage, comparability, or
  safety before any route is promoted.
- `target_recovery`: late-stage result work. The planner chooses a predefined
  target, launches or evaluates documented result-bearing work, records
  evidence, and keeps failed candidates separate from target closure.

Every completed cycle should write `runtime/last_cycle_outcome.json`. The
validator checks that the outcome names the active mode, records reads/actions,
points to evidence, and includes mode-specific details.

### `EXECUTION_MODE`

`runtime/EXECUTION_MODE` means: **how often should the LLM planner be called?**

Supported core values:

- `manual`
- `interval`
- `event`
- `batch_low_api`

### `BATCH_PROFILE`

`runtime/BATCH_PROFILE` means: **how deep should one low-API batch try to be?**

Profiles are soft targets. They should guide planning, not force bad work.

Examples:

- `auto`: normal batch depth.
- `long`: fewer calls, larger batches.
- `overnight`: unattended long batches.

## Execution Modes

### `manual`

No supervisor starts planning cycles automatically.

Use when:

- configuring a new profile;
- debugging;
- avoiding any automatic API usage;
- running toy examples.

Typical commands:

```bash
scripts/set_mode.sh execution manual
scripts/show_runtime_status.sh
scripts/run_batch_low_api_cycle.sh
```

### `interval`

Calls the planner on a fixed interval.

Use when:

- you want predictable periodic planning;
- result files are not reliable completion markers;
- API budget is acceptable.

Configure with:

```bash
INTERVAL_SECONDS=1800 scripts/launch_tmux_agent.sh
```

### `event`

Calls the planner when result signatures, tmux sessions, GPU apps, or heartbeat
state changes.

Use when:

- you want responsive supervision;
- result artifacts are meaningful;
- API usage is not very constrained.

Avoid when:

- logs or watched files update constantly;
- you need strict low API usage.

### `batch_low_api`

The recommended server default for expensive, long-running experiments.

Behavior:

1. Planner runs once at a batch boundary.
2. It writes a plan and manifest.
3. It launches ordinary jobs, preferably through `scripts/launch_batch_job.sh`
   so `status.tsv` records running/completed/failed events.
4. It exits.
5. Training runs without more LLM calls.
6. The next planning cycle happens after active jobs finish and watched results
   change.

Use when:

- jobs run for hours;
- API quota matters;
- you want documented batch boundaries;
- results are available as completion files or aggregates.

This mode is usually the best fit for GPU servers because the LLM plans at
experiment boundaries instead of polling continuously while training is still
running.

## Supplemental Low-API Cycles

Supplemental cycles are optional. They allow a planning call while long jobs are
still active if:

- supplemental mode is enabled;
- active jobs have been running long enough;
- enough GPUs/resources are idle;
- rate limits are satisfied.

The planner receives `supplemental_context.md` and must leave active jobs
untouched. It may only launch independent work.

Disable this for simple projects:

```json
{
  "batch": {
    "supplemental": {
      "enabled": false
    }
  }
}
```

## Retry And Fallback

Temporary planning-provider failures can return retry status. The batch
supervisor records a pending retry and backs off.

Configurable fields:

- `supervisor.retry_base_seconds`
- `supervisor.retry_max_seconds`
- `codex.fallback_after_failures`
- `codex.fallback_model`
- `codex.fallback_reasoning_effort`
- `codex.secondary_fallback_after_failures`
- `codex.secondary_fallback_model`
- `codex.secondary_fallback_reasoning_effort`

Use fallback profiles when the primary model is temporarily unavailable or too
expensive for repeated retries.

## Configuration Responsibility

| Concern | Where To Configure |
| --- | --- |
| Project objective and safety policy | `profiles/<project>/AGENTS.project.md` |
| Per-cycle operating brief | `profiles/<project>/CYCLE_BRIEF.md` |
| Planner provider, environment, model defaults | `configs/project.json` `codex` section |
| Writable workspaces and read-only references | `configs/project.json` `workspaces` / `originals` |
| Active job detection | `configs/project.json` `job_detection` |
| Watched result artifacts | `configs/project.json` `results` |
| Allowed modes and batch targets | `configs/project.json` `modes` |
| Batch manifest schema | `configs/project.json` `batch.manifest_columns` |
| Local mutable state | `runtime/` |
| Logs | `logs/` |

## Pause And Stop

Create `runtime/PAUSE` to prevent supervisors from starting new planning
cycles. Existing training jobs keep running.

```bash
touch runtime/PAUSE
```

Remove it to resume:

```bash
rm runtime/PAUSE
```

Create `runtime/STOP` to tell supervisors to exit:

```bash
touch runtime/STOP
```

## Recommended Presets

### New Project Setup

```bash
scripts/set_mode.sh execution manual
python3 scripts/doctor.py
scripts/show_runtime_status.sh
```

### Normal Long-Running Server Work

```bash
scripts/set_mode.sh execution batch_low_api
scripts/set_mode.sh batch_profile auto
rm -f runtime/PAUSE
scripts/launch_tmux_agent.sh
```

### Very Low API Usage

```bash
scripts/set_mode.sh execution manual
touch runtime/PAUSE
```

Manually trigger only when ready:

```bash
scripts/run_batch_low_api_cycle.sh
```

### Responsive Monitoring

```bash
scripts/set_mode.sh execution event
rm -f runtime/PAUSE
scripts/launch_tmux_agent.sh
```

## Mode Selection Checks

Before switching out of `manual`, confirm:

- `python3 scripts/doctor.py` reports no errors.
- `scripts/list_active_jobs.py --json` classifies your jobs correctly.
- `python3 scripts/compute_signature.py` changes only for meaningful results.
- `python3 scripts/render_prompt.py batch_low_api` contains the right policy,
  workspaces, metrics, and safety boundaries.
- `runtime/PAUSE` is absent only when you intentionally want supervisors to
  start new planning cycles.
