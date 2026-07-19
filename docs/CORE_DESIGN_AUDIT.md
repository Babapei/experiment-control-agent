# Core Design Audit

This document tracks design-level issues in the agent itself. It is not a bug
list for one extracted project. Use it to decide what to improve before adding
new providers, schedulers, or project-specific features.

## Audit Position

The current repository is a usable generic baseline, but the control-plane
design is not finished. The main risk is not that one script is broken. The main
risk is that an LLM planner may receive vague objective labels, broad prompts,
and weak runtime checks, then perform shallow or inconsistent work while still
appearing operational.

The next hardening work should focus on planner semantics and verification:

1. make objective modes executable;
2. make each cycle prove it satisfied the active objective;
3. make batch boundaries and result ledgers strong enough for resumption;
4. validate agent outputs, not only config shape.

## Current Model

The agent currently has three mode axes:

- `AGENT_MODE`: the project objective.
- `EXECUTION_MODE`: how often the planner is called.
- `BATCH_PROFILE`: how deep a low-API batch should try to be.

This split is correct and should stay. The problem is that the original agent
treated the first axis too lightly: objective modes could behave like labels
instead of enforceable operating contracts.

## Design Issues Found

### 1. Objective Modes Can Become Labels

Problem:

An objective mode such as `audit_exploration` or `target_recovery` is not useful
unless it changes the planner's required reads, allowed actions, artifacts,
success criteria, and escalation behavior.

Current mitigation:

- `modes.agent_mode_contracts` now defines a contract for every allowed
  `AGENT_MODE`.
- `scripts/render_prompt.py` injects the active contract into the prompt.
- `scripts/doctor.py` fails configs that define an agent mode without a full
  contract.

Remaining work:

- Add validators that check whether each completed cycle actually produced the
  contract's required artifacts.
- Add examples of project-specific contracts beyond the toy and sanitized paper
  profiles.

### 2. Target-Recovery Modes Can Become Overloaded

Problem:

A recovery objective often mixes several different jobs:

- select targets;
- evaluate evidence;
- design candidates;
- launch result-bearing work;
- run unblocking audits;
- update dashboards;
- decide when a failed candidate leaves the target open.

If all of this is expressed as one broad mode, the planner may do a shallow
version of everything instead of completing one valuable step.

Recommended design:

Keep `target_recovery` as a user-facing objective, but require the active cycle
to choose one explicit recovery operation:

- `target_selection`: choose and rank the frontier.
- `evidence_update`: incorporate completed results into target state.
- `candidate_design`: convert a blocker or failed candidate into a runnable
  package.
- `batch_launch`: launch documented result-bearing work.
- `unblocking_audit`: produce an artifact needed before result-bearing work.

These do not need to become top-level execution modes. They can be required
fields in plan/status artifacts and validated after the cycle.

### 3. Audit/Exploration Needs Promotion Rules

Problem:

Audit and exploration work can drift forever if it only records that more
inspection is needed.

A good audit cycle must answer:

- What uncertainty is being reduced?
- What artifact proves the audit happened?
- What evidence promotes the lane to a larger run?
- What evidence rejects the candidate package?
- What external dependency blocks progress?

Recommended design:

Every audit/exploration contract should require one of these outcomes:

- `promote_to_candidate`;
- `continue_probe_with_reason`;
- `candidate_rejected`;
- `waiting_dependency`;
- `hard_blocked`.

### 4. Batch Boundaries Need Stronger Completion Semantics

Problem:

`batch_low_api` is useful only if the agent can tell when a batch has meaningful
new evidence. File signatures and active process checks are necessary but not
enough. A changed file does not necessarily mean the manifest rows completed,
and a completed manifest row may not have been interpreted.

Recommended design:

Add an explicit batch state model:

- `planned`;
- `launched`;
- `running`;
- `partially_completed`;
- `completed_unreviewed`;
- `reviewed`;
- `failed_or_stale`.

Each manifest row should have a status and evidence pointer. A planning cycle
should say which previous batch rows were reviewed before launching more work.

### 5. Runtime Ledgers Are Human-Readable But Weakly Typed

Problem:

Markdown ledgers are easy to inspect but hard to validate. If the agent writes
vague next actions or skips required fields, scripts may still pass.

Recommended design:

Keep Markdown for humans, but add small structured sidecar files for machines:

- `runtime/current_status.json`;
- `runtime/research_lanes.json`;
- `runtime/batch_low_api/batches/<id>/manifest.jsonl`;
- optional project-specific target dashboard JSON.

Do not replace Markdown immediately. Start by writing both formats for new
batches or examples.

### 6. Validators Check Setup More Than Behavior

Problem:

Current checks catch invalid config, missing files, bad mode values, and some
manifest shape issues. They do not prove that a completed cycle satisfied the
active objective mode.

Recommended design:

Add post-cycle validators for:

- active mode required artifacts;
- selected recovery operation;
- batch plan fields;
- manifest row statuses;
- stale or repeated vague next actions;
- missing evidence paths after completed jobs.

### 7. Prompt Rules Are Still Too Broad

Problem:

The prompt tells the planner many reasonable things, but a broad prompt can make
the planner do a little planning, a little monitoring, and a little writing
without producing a strong operational result.

Recommended design:

Make each cycle choose one primary operation early and report it in the plan or
status:

```text
cycle_operation: evidence_update | candidate_design | batch_launch | unblocking_audit | status_only
```

Then require operation-specific artifacts.

### 8. Safety Boundaries Rely Mostly On Instruction

Problem:

The core scripts create workspace/original symlinks and instruct the planner not
to modify originals, but the enforcement is mostly prompt-level.

Recommended design:

Before public v1, add at least one practical guard:

- preflight warnings when writable flags conflict with `originals`;
- optional command wrapper that rejects paths under configured read-only roots;
- post-cycle audit that reports modified files under read-only roots when those
  roots are git repositories.

## Recommended Hardening Order

### Phase A: Objective Contract Completion

Status: partially implemented.

Done:

- Config supports `modes.agent_mode_contracts`.
- Prompt rendering injects the active contract.
- Doctor validates contract presence and shape.

Next:

- Add post-cycle checks for required artifacts.
- Add operation selection inside mode contracts or batch plans.

### Phase B: Recovery Operation Model

Status: not implemented.

Add a generic `cycle_operation` concept so a broad objective mode can still make
a focused cycle. Start with documentation, then require the field in
`plan.md`/`current_status.md` for new low-API batches.

### Phase C: Batch State Model

Status: not implemented.

Extend manifests with row state or add a sidecar file. The supervisor should be
able to distinguish "jobs finished" from "evidence reviewed".

### Phase D: Structured Runtime Sidecars

Status: not implemented.

Add JSON/JSONL sidecars for machine validation while keeping Markdown ledgers
for humans.

### Phase E: Safety Guardrails

Status: not implemented.

Add lightweight filesystem or git-based checks for read-only roots before
calling the planner and after cycles complete.

## What Not To Do Yet

Do not add new LLM providers, Slurm/PBS adapters, dashboards, or rich project
templates before the semantic loop is stronger. Those features would make the
agent broader, but not necessarily more correct.

Do not create many more top-level modes to paper over vague behavior. Prefer a
small number of objective modes with strong contracts and explicit
operation-level artifacts.

## Review Checklist

Before calling the design "v1-ready", answer yes to all of these:

- Does every objective mode have a contract?
- Does every cycle declare what operation it performed?
- Can a validator tell whether required artifacts were produced?
- Can a low-API batch be marked reviewed separately from completed?
- Can stale vague next actions be detected?
- Can a new user see why an unattended run is safe enough?
- Can read-only roots be audited for accidental modification?
