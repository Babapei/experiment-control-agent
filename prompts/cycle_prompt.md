You are running one bounded autonomous cycle for a server-side experiment agent.

Start by reading:

1. the rendered recent validated decision history and state-attention notes
2. `configs/project.json` if present, otherwise `configs/project.example.json`
3. the rendered `active_agent_mode_contract`
4. the configured project policy and cycle brief under `project_docs`
5. `runtime/AGENT_MODE`
6. `runtime/EXECUTION_MODE`
7. `runtime/current_status.md` if it exists
8. `runtime/research_lanes.md` if it exists
9. the last 80-120 lines of `runtime/agent_journal.md` if it exists

Perform one bounded research-management pass:

- inspect active managed jobs and resource occupancy;
- analyze newly completed results only as needed for a concrete decision;
- reconcile planned/running historical actions with live jobs and files before
  launching a duplicate or incompatible action;
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
5. `runtime/pending_cycle_outcome.json`

Write `runtime/pending_cycle_outcome.json` using
`templates/CYCLE_OUTCOME_TEMPLATE.json` as the schema. The runner validates and
archives it only after the cycle exits. It must record the active agent mode,
execution mode, reads performed, actions taken, artifacts/evidence created or
inspected, exactly one satisfied success criterion or escalation criterion from
the active mode contract, and the next decision.

Keep the decision lineage explicit in the outcome:

- `evidence_records` must give each evidence item an id, a state of `observed`
  or `planned`, a path, a short summary, and its impact on this cycle. Observed
  evidence must point to an existing file; a future output may be `planned`.
- `action_records` must identify whether each action was completed, running,
  planned, or deliberately not taken, and cite the evidence ids behind it.
- `decision_evidence_ids` must cite the evidence that supports the next
  decision. Do not present a proposed output as observed evidence.
- Set `mode_transition` to `null` when staying in the current mode. If you
  change mode, update `runtime/AGENT_MODE` and record the previous mode, new
  mode, reason, and supporting evidence ids. A mode switch is optional and
  must follow the project evidence, not a fixed global sequence.

Populate `mode_details` according to the active mode:

- `method_exploration`: `research_question`, `hypothesis`,
  `candidate_method`, `validation_design`, `evaluation_signal`, `decision`.
- `audit_validation`: `uncertainty`, `audit_action`, `evidence_path`,
  `verdict`, `promotion_or_followup`.
- `target_recovery`: `selected_target`, `hypothesis`,
  `output_root_or_evidence`, `target_state_update`,
  `decision_after_completion`.

Final response: short operational summary only.
