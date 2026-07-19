# Generic Experiment Agent Rules

This repository is the control root for a server-side Codex experiment agent.

## Core Contract

- The core scripts manage scheduling, state, Codex invocation, active-job
  detection, result-change signatures, and low-API batch boundaries.
- Project-specific scientific policy belongs in the configured profile under
  `project_docs`, not in core scripts.
- Keep credentials, logs, runtime ledgers, datasets, checkpoints, and private
  manuscript material out of git.

## Operating Rules

- Read `configs/project.json` before making project decisions.
- Respect `runtime/PAUSE` and `runtime/STOP`.
- Do not modify read-only originals.
- Use timestamped outputs and explicit log paths.
- Update `runtime/current_status.md` and `runtime/agent_journal.md` after every
  cycle that changes state.
- In `batch_low_api`, plan once, launch once, perform a short startup check, and
  exit.

## Safety

Stop and report instead of continuing if:

- Codex authentication is missing,
- required environments or workspaces are unavailable,
- the next step would overwrite evidence,
- the project profile does not provide enough information to launch safely.

