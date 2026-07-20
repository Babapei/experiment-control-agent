# Default Project Policy

This default profile is intentionally generic. Replace it with a project-specific
profile before running real experiments.

## Mission

Manage long-running experiments with bounded LLM planning cycles. The agent
should inspect state, launch documented non-conflicting work, update ledgers,
and exit.

## Objective Modes

Objective modes are configured as contracts in `configs/project.json`. The
default lifecycle is:

- `method_exploration`: propose and test early candidate methods.
- `audit_validation`: validate data, metrics, runners, provenance, or safety
  assumptions before promotion.
- `target_recovery`: push predefined targets with reproducible evidence.

Do not add a mode unless its purpose, required artifacts, success criteria, and
escalation criteria are clear enough for unattended planning.

## Safety Rules

- Treat `originals/*` as read-only.
- Write only inside configured writable workspaces or this control root.
- Do not overwrite prior outputs or logs.
- Record commands, resources, outputs, and expected decision points.
- Stop if the project-specific next action is ambiguous or unsafe.

## Status Vocabulary

Projects may replace this vocabulary. A useful default set is:

- `open`: work remains.
- `running`: a package is active.
- `completed`: evidence is available.
- `failed`: the exact package failed.
- `blocked`: no safe local next action exists.
