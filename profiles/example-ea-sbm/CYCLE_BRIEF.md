# Example Cycle Brief

This file is the compact context a planning cycle should read before targeted
lookup in longer project references.

## Mission

Operate on a row-centric recovery queue for an ML paper. A failed candidate
does not close the manuscript row unless the profile says it does.

If the active mode is `method_exploration`, first formulate a bounded method
hypothesis and a cheap validation signal. If the active mode is
`audit_validation`, reduce one concrete uncertainty before promotion. If the
active mode is `target_recovery`, choose the most useful open row or blocker.

## Required Reads

1. `runtime/AGENT_MODE`
2. `runtime/EXECUTION_MODE`
3. `runtime/BATCH_PROFILE` if present
4. `runtime/current_status.md`
5. `runtime/research_lanes.md`
6. project-specific dashboard if configured
7. recent `runtime/agent_journal.md`

## Scheduling Policy

- Inspect active jobs and resources.
- Keep healthy long-running work active.
- Use idle resources for independent non-conflicting lanes.
- Prefer full result-bearing bundles when the candidate is high confidence.
- Use small probes for risky code paths, data-pipeline smoke tests, or quick
  failure gates.

## Per-Cycle Output

- Update concise status.
- Append journal entry.
- Update lane ledger.
- State the next action.
