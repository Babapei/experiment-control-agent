# Example Project Policy

This is a sanitized example profile showing where project-specific research
policy belongs. Replace it for your own project.

## Mission

Recover and audit a set of already-written experiment-table rows for a machine
learning paper. The core agent does not know what the rows mean; this profile
defines the target rows, trusted rows, metrics, runners, and safety boundaries.

## Safety Boundaries

- Treat `originals/*` as read-only.
- Write only inside configured writable workspaces or this control root.
- Do not overwrite prior result directories.
- Record exact commands, inputs, checkpoints, logs, and aggregate paths.
- Do not tune blindly on test metrics; write the validation-facing rationale.

## Project Vocabulary

- `row_open`: target row still needs a new candidate or audit.
- `candidate_failed`: the exact candidate failed; the row may remain open.
- `row_recovered`: evidence is sufficient for the target.
- `usable_with_caveat`: evidence is likely usable but needs a caveat.
- `waiting_dependency`: a prerequisite is unavailable and cannot be produced
  locally.
- `hard_blocked`: no safe local next action exists.

## Metrics

Define the primary metric fields, auxiliary metrics, and recovery thresholds in
your own profile. Avoid ambiguous labels like "F1" when the code emits several
variants.

## Runner Map

List preferred final runners and any helper runners here. For each experiment
family, state which scripts/configs/data roots determine the result.

