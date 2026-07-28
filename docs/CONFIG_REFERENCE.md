# Config Reference

The main config file is `configs/project.json`. If it is missing, scripts use
`configs/project.example.json`.

## `project`

```json
{
  "name": "my-project",
  "description": "Short project description",
  "control_root": "."
}
```

- `name`: shown in rendered prompts and doctor output.
- `description`: human-facing context.
- `control_root`: reserved for future use; keep `"."` for now.

## `provider`

The planning-provider execution boundary:

```json
{
  "type": "codex",
  "command": "codex"
}
```

- `type`: provider adapter. The bundled adapter is `codex`.
- `command`: executable used by the adapter.

Codex-specific authentication, home, model, and fallback settings remain in the
`codex` section. `provider.codex` may override those legacy fields when needed.

## `codex`

```json
{
  "home": ".codex-home",
  "auth_required": true,
  "conda_init": "/path/to/conda.sh",
  "conda_env": "codexcli",
  "extra_path_entries": ["/path/to/env/bin"],
  "default_model": "gpt-5.5",
  "default_reasoning_effort": "high"
}
```

- `home`: directory used as `CODEX_HOME`.
- `auth_required`: set `false` only for dry runs or non-Codex demos.
- `conda_init`: optional shell script sourced before running `codex`.
- `conda_env`: optional conda environment activated before running `codex`.
- `extra_path_entries`: appended to `PATH` for Codex-launched commands.
- `default_model` / `default_reasoning_effort`: optional Codex CLI defaults.
- fallback fields control retry profiles after repeated temporary failures.

## `supervisor`

Controls loop timing:

- `session_name`: tmux session name for `launch_tmux_agent.sh`.
- `check_interval_seconds`: sleep interval between supervisor checks.
- `heartbeat_seconds`: event mode heartbeat.
- `min_cycle_gap_seconds`: minimum gap between LLM planning cycles.
- `cycle_timeout_seconds`: timeout for one `codex exec` call.
- `retry_base_seconds` / `retry_max_seconds`: backoff bounds after temporary
  failures.

## `modes`

Defines allowed mode values and defaults:

- `agent_modes`: project objective modes.
- `agent_mode_contracts`: required contract for each project objective mode.
- `execution_modes`: normally `event`, `interval`, `batch_low_api`, `manual`.
- `batch_profiles`: soft targets for low-API planning depth.

Profiles are guidance for the prompt and supervisor state, not blind quotas.

Each `agent_mode_contracts.<mode>` object must include:

- `purpose`: short string.
- `entry_conditions`: when to use the mode.
- `required_reads`: state/docs the planner must inspect.
- `allowed_actions`: what the planner may do.
- `required_artifacts`: what the cycle must write or produce.
- `success_criteria`: how the cycle counts as useful.
- `escalation_criteria`: when to stop or ask for help.

The default example modes are:

- `method_exploration`: early-stage candidate method generation and bounded
  validation.
- `audit_validation`: data, metric, runner, provenance, and safety validation.
- `target_recovery`: predefined target recovery or improvement.

For built-in mode names, `runtime/last_cycle_outcome.json` should include
mode-specific `mode_details`; `scripts/validate_cycle_outcome.py` checks those
fields after a cycle.

## `workspaces`

Writable project roots. `bootstrap_layout.py` creates symlinks under
`workspaces/`. Link names must be simple names, not paths. Bootstrap refuses to
replace existing regular files or directories under `workspaces/`; move those
manually before rerunning bootstrap.

```json
{
  "workspaces": {
    "main": {"path": "/srv/my-project-rerun", "writable": true}
  }
}
```

## `originals`

Read-only reference roots. `bootstrap_layout.py` creates symlinks under
`originals/`. Link names must be simple names, not paths. Bootstrap refuses to
replace existing regular files or directories under `originals/`; move those
manually before rerunning bootstrap.

```json
{
  "originals": {
    "main": {"path": "/srv/my-project-original", "writable": false}
  }
}
```

The core scripts do not enforce filesystem permissions. The profile and prompts
tell the LLM planner what is safe.

Set host filesystem permissions as well: the `writable` field is an explicit
planner/reviewer declaration, not a sandbox. `doctor.py` warns about omitted
declarations and originals marked writable. See [`TRUST_MODEL.md`](TRUST_MODEL.md).

## `job_detection`

Used by `scripts/list_active_jobs.py`.

```json
{
  "managed_hints": ["{root}", "my-rerun-workspace"],
  "patterns": [
    {"category": "training", "regex": "(^|/|\\s)train\\.py(\\s|$)"}
  ],
  "exclude_patterns": ["\\bcodex exec\\b"]
}
```

- `managed_hints`: process command must contain at least one hint.
- `patterns`: category regexes for managed jobs.
- `exclude_patterns`: filters for supervisors, validators, and unrelated tools.

Keep hints narrow enough that the agent does not count unrelated jobs.

## `planner_observation`

Sets the operational context the planner may inspect during a cycle. This is
separate from `results`, which controls supervisor change detection.

```json
{
  "managed_jobs": true,
  "tmux_sessions": false,
  "gpu_compute_apps": false,
  "additional_read_paths": ["workspaces/main/results"]
}
```

- `managed_jobs`: permit the bounded `scripts/list_active_jobs.py --json`
  inspection for processes belonging to this project profile.
- `tmux_sessions`: permit direct tmux inspection. Keep this false unless the
  project needs a declared tmux-based runner.
- `gpu_compute_apps`: permit direct GPU occupancy inspection. Keep this false
  for projects that do not schedule GPU work.
- `additional_read_paths`: project paths beyond the configured docs,
  workspaces, originals, runtime state, and result watch paths.

The planner is instructed not to recursively inventory the repository or read
unconfigured paths. This configuration documents and narrows the intended
operational boundary; deploy an OS/container sandbox when strict enforcement
against an untrusted provider is required.

## `results`

Used by event and batch supervisors to detect meaningful changes.

```json
{
  "watch_paths": ["runtime", "workspaces/main/results"],
  "file_patterns": ["completed.json", "*aggregate*.json"],
  "include_tmux_sessions": true,
  "include_gpu_compute_apps": true
}
```

Avoid watching constantly changing training logs unless you want frequent
planning cycles.

## `batch`

Defines low-API manifest shape and supplemental-cycle policy.

- `manifest_columns`: required header for `manifest.tsv`.
- `supplemental.enabled`: allow extra planning while long jobs are still active.
- `supplemental.min_active_seconds`: active job age before supplemental cycles.
- `supplemental.min_idle_gpus`: idle GPU threshold.
- `supplemental.*gap_seconds`: rate limits.

Set `supplemental.enabled=false` for simple projects.

## `project_docs`

Project policy files injected into rendered prompts:

```json
{
  "cycle_brief": "profiles/my-project/CYCLE_BRIEF.md",
  "agents_policy": "profiles/my-project/AGENTS.project.md",
  "reference_docs": ["profiles/my-project/TARGETS.md"]
}
```

Use these files for domain-specific details. Do not hardcode domain knowledge in
core scripts.
