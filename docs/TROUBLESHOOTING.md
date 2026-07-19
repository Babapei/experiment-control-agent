# Troubleshooting

## `codex` is not on PATH

`doctor.py` may show:

```text
WARN: tools: `codex` is not on PATH in this shell
```

Fix by either:

- installing a `codex` wrapper on `PATH`;
- configuring `codex.conda_init` and `codex.conda_env`;
- running from a shell where Codex CLI is already available.

For the toy example, this warning is harmless because `auth_required=false` and
the demo does not call Codex.

## `tmux` is not on PATH

`launch_tmux_agent.sh` needs tmux. Install tmux on the server or use manual
commands only. The toy example does not require tmux.

## `nvidia-smi` is not on PATH

This is harmless for CPU-only projects. For GPU projects, install NVIDIA drivers
or disable GPU signatures:

```json
{
  "results": {
    "include_gpu_compute_apps": false
  }
}
```

## `doctor.py --strict` fails on a laptop

Strict mode treats warnings as failures. Use normal `doctor.py` on development
machines and strict mode on the actual target server.

## Active jobs are not detected

Check:

```bash
scripts/list_active_jobs.py --json
ps -eo pid,ppid,stat,etime,args | head
```

Then adjust:

- `job_detection.managed_hints`
- `job_detection.patterns`
- `job_detection.exclude_patterns`

The command must contain at least one managed hint and match one category regex.

## Too many unrelated jobs are detected

Make `managed_hints` more specific. Include the control root, workspace name, or
batch directory prefix. Add exclude patterns for unrelated tools.

## Supervisor does not trigger a new batch

Check:

```bash
cat runtime/EXECUTION_MODE
cat runtime/PAUSE 2>/dev/null
cat runtime/batch_low_api_supervisor/state 2>/dev/null
python3 scripts/compute_signature.py
scripts/list_active_jobs.py
```

Common causes:

- `EXECUTION_MODE` is `manual`.
- `runtime/PAUSE` exists.
- active jobs are still running.
- result signature did not change.
- `min_cycle_gap_seconds` has not elapsed.

## The agent wakes too often

Do not watch log files that update every few seconds. Narrow
`results.file_patterns` to final artifacts such as `completed.json`,
`metrics_summary.json`, or aggregate JSON files.

## Prompt points to missing project docs

Run:

```bash
python3 scripts/doctor.py
python3 scripts/render_prompt.py cycle | sed -n '1,40p'
```

Fix `project_docs.cycle_brief`, `project_docs.agents_policy`, and
`project_docs.reference_docs`.

## I accidentally created local runtime files

That is normal. `runtime/`, `logs/`, `workspaces/`, and result directories are
ignored. Do not commit `configs/project.json` if it contains local/private
paths.

