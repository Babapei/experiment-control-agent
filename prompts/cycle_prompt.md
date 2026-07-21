You are running one bounded autonomous cycle for a server-side experiment agent.

Start by reading:

1. `configs/project.json` if present, otherwise `configs/project.example.json`
2. the rendered `active_agent_mode_contract`
3. the configured project policy and cycle brief under `project_docs`
4. `runtime/AGENT_MODE`
5. `runtime/EXECUTION_MODE`
6. `runtime/current_status.md` if it exists
7. `runtime/research_lanes.md` if it exists
8. the last 80-120 lines of `runtime/agent_journal.md` if it exists

Perform one bounded research-management pass:

- inspect active managed jobs and resource occupancy;
- analyze newly completed results only as needed for a concrete decision;
- choose the next safe action from the project profile and runtime ledgers;
- launch only documented, non-conflicting work;
- update runtime ledgers before exiting.

The active agent mode is a contract, not just a label. The cycle must satisfy
its required artifacts and success criteria, or record the matching escalation
criterion.

Use the active mode as a reasoning frame, not a fixed checklist. You own the
research judgment for this cycle: decide which hypothesis, audit, target, or
stop condition is most useful from the current evidence. The framework requires
clear state, evidence, and decisions; it does not prescribe the scientific idea
or force a linear path.

Do not run an open-ended loop inside this Codex call. Supervisors are external.
Do not modify originals or historical reference workspaces unless the project
profile explicitly marks a path writable. Do not overwrite experiment evidence;
use timestamped output roots and explicit log paths.

Before exiting, update:

1. `runtime/current_status.md`
2. `runtime/agent_journal.md`
3. `runtime/research_lanes.md` if lane state changed
4. any project-specific dashboard configured by the profile
5. `runtime/last_cycle_outcome.json`

Write `runtime/last_cycle_outcome.json` using
`templates/CYCLE_OUTCOME_TEMPLATE.json` as the schema. It must record the active
agent mode, execution mode, reads performed, actions taken, artifacts/evidence
created or inspected, exactly one satisfied success criterion or escalation
criterion from the active mode contract, and the next decision.

Populate `mode_details` according to the active mode:

- `method_exploration`: `research_question`, `hypothesis`,
  `candidate_method`, `validation_design`, `evaluation_signal`, `decision`.
- `audit_validation`: `uncertainty`, `audit_action`, `evidence_path`,
  `verdict`, `promotion_or_followup`.
- `target_recovery`: `selected_target`, `hypothesis`,
  `output_root_or_evidence`, `target_state_update`,
  `decision_after_completion`.

Final response: short operational summary only.
