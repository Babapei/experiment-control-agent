# Toy Project Policy

This profile is a toy example. It has no scientific meaning.

## Mission

Launch small CPU-only jobs, wait for them to write `completed.json`, and update
runtime ledgers.

## Safety

- Write only under `examples/toy-sleep-experiment/results` and `runtime/`.
- Do not require Codex auth.
- Do not require GPUs or tmux.
- Use explicit logs and output directories.

## Status Vocabulary

- `open`: task has not run.
- `running`: task process is active.
- `completed`: `completed.json` exists.
- `failed`: process exited without result.

