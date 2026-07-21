# Architecture

Experiment Control Agent is a control plane around long-running experiments. It
does not train models itself. It asks an LLM planner to perform bounded planning
cycles, then launches ordinary shell, Python, tmux, or scheduler jobs. The
bundled planning-provider adapter uses `codex exec`.

## Research Judgment Boundary

The core framework should not decide the science. It should preserve state,
record evidence, enforce local operating boundaries, and make runs resumable.
The planner, guided by the project profile, owns research judgment:

- proposing hypotheses and candidate methods;
- deciding whether to explore, audit, recover targets, or stop;
- designing validation experiments and ablations;
- interpreting evidence and choosing the next scientific move.

Core validators should check that decisions are recorded and recoverable. They
should not hardcode a domain strategy or force a single linear research path.

## Control Flow

```text
launch_tmux_agent.sh
  -> event_agent_loop.sh | agent_loop.sh | batch_low_api_loop.sh
     -> run_codex_cycle.sh | run_batch_low_api_cycle.sh
        -> planning provider adapter
           -> project scripts launched during the planning cycle
```

## Runtime State

- `runtime/AGENT_MODE`: project objective mode.
- `runtime/EXECUTION_MODE`: LLM planning-call cadence.
- `runtime/BATCH_PROFILE`: low-API batch depth target.
- `runtime/PAUSE`: supervisors should not start new planning cycles.
- `runtime/STOP`: supervisors should exit.
- `runtime/batch_low_api/current_batch.md`: pointer to the latest batch plan.
- `runtime/batch_low_api/batches/<id>/status.tsv`: package status events when
  the batch registry wrapper is used.
- `runtime/last_cycle_outcome.json`: machine-readable summary of the planner's
  reads, actions, evidence, success/escalation criterion, and next decision.
- `runtime/batch_low_api/usage_log.tsv`: token usage history.

## Config-Driven Parts

`configs/project.json` controls:

- Planning provider type/command.
- Codex home and optional conda activation for the bundled Codex adapter.
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
