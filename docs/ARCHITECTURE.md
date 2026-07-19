# Architecture

Codex Experiment Agent is a control plane around long-running experiments. It
does not train models itself. It asks Codex to perform bounded planning cycles,
then launches ordinary shell, Python, tmux, or scheduler jobs.

## Control Flow

```text
launch_tmux_agent.sh
  -> event_agent_loop.sh | agent_loop.sh | batch_low_api_loop.sh
     -> run_codex_cycle.sh | run_batch_low_api_cycle.sh
        -> codex exec
           -> project scripts launched by Codex
```

## Runtime State

- `runtime/AGENT_MODE`: project objective mode.
- `runtime/EXECUTION_MODE`: Codex call cadence.
- `runtime/BATCH_PROFILE`: low-API batch depth target.
- `runtime/PAUSE`: supervisors should not start new Codex cycles.
- `runtime/STOP`: supervisors should exit.
- `runtime/batch_low_api/current_batch.md`: pointer to the latest batch plan.
- `runtime/batch_low_api/usage_log.tsv`: token usage history.

## Config-Driven Parts

`configs/project.json` controls:

- Codex home and optional conda activation.
- Allowed modes and defaults.
- Workspace/original symlinks.
- Active-job regexes.
- Watched result paths and filename patterns.
- Batch manifest columns.
- Project-specific docs.

## Public/Private Split

Public repository:

- core scripts
- generic prompts
- templates
- sanitized examples
- documentation

Private project profile:

- private paths
- manuscript targets
- private datasets
- exact metrics
- private result ledgers
- unpublished notes

