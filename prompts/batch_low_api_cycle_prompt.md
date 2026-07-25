You are running one low-API batch-planning cycle for a server-side experiment
agent.

This cycle should spend Codex reasoning once, design/launch ordinary shell,
tmux, scheduler, or Python jobs, then exit. In normal low-API mode, the next
planning call should happen after the batch finishes or when the user explicitly
asks. If a supplemental context file exists, the supervisor has intentionally
allowed a limited extra planning call while other jobs are still active.

Read:

1. `runtime/batch_low_api_supervisor/supplemental_context.md` if it exists
2. `configs/project.json` if present, otherwise `configs/project.example.json`
3. the rendered `active_agent_mode_contract`
4. the configured project policy and cycle brief under `project_docs`
5. `runtime/AGENT_MODE`
6. `runtime/EXECUTION_MODE`; expect `batch_low_api`
7. `runtime/BATCH_PROFILE`
8. `runtime/current_status.md` if it exists
9. `runtime/research_lanes.md` if it exists
10. the last 80-120 lines of `runtime/agent_journal.md` if it exists

Batch-planning rules:

- Check active managed jobs first. If substantial work is still active, do not
  launch conflicting work.
- Treat the active agent mode as a contract. The batch must satisfy its required
  artifacts and success criteria, or record the matching escalation criterion.
- Use the active mode as a reasoning frame, not a fixed checklist. You own the
  research judgment for the batch: choose the hypothesis, validation design,
  target push, or stop/escalation decision that is most informative from the
  current evidence.
- If `supplemental_context.md` exists, this is a supplemental cycle. Some
  managed jobs are still active. Leave them untouched and launch only
  independent work for currently idle resources, or explain why no such work is
  safe.
- Select a project-specific frontier or priority queue before choosing commands.
- Prefer batches that can run for hours without another Codex call when the
  active batch profile asks for that.
- Each launched package must have a hypothesis, command, resource assignment,
  output root, log path, and expected decision after completion.
- CPU/lightweight unblocking work is allowed when it moves a blocked lane toward
  a future result-bearing package.
- Avoid duplicate or low-value work merely to fill resources.
- Use timestamped output roots. Do not overwrite logs, checkpoints, aggregates,
  or audit artifacts.
- Launch with tmux/nohup/scheduler as appropriate, perform only a short startup
  check, and exit.
- Prefer `scripts/launch_batch_job.sh` for ordinary background packages so the
  batch gets a machine-readable `status.tsv` with running/completed/failed
  events. Use scheduler-specific launch commands only when the project profile
  requires them, and then record equivalent status evidence manually.
  The low-API supervisor treats a valid `status.tsv` as the strongest batch
  completion signal before falling back to process and result-signature checks.

Required low-API artifacts:

1. Create `runtime/batch_low_api/batches/<timestamp>/`.
2. Write `plan.md`.
3. Write `manifest.tsv` using the configured manifest columns.
4. Write or maintain `status.tsv` for launched packages when possible.
5. Update `runtime/batch_low_api/current_batch.md`.
6. Update `runtime/current_status.md`.
7. Append to `runtime/agent_journal.md`.
8. Update project-specific ledgers or dashboards if state changed.
9. Write `runtime/pending_cycle_outcome.json` using
   `templates/CYCLE_OUTCOME_TEMPLATE.json`. The runner validates and archives
   it only after the cycle exits.

The cycle outcome must record the active agent mode, execution mode, reads
performed, actions taken, artifacts/evidence created or inspected, exactly one
satisfied success criterion or escalation criterion from the active mode
contract, and the next decision.

Populate `mode_details` according to the active mode:

- `method_exploration`: `research_question`, `hypothesis`,
  `candidate_method`, `validation_design`, `evaluation_signal`, `decision`.
- `audit_validation`: `uncertainty`, `audit_action`, `evidence_path`,
  `verdict`, `promotion_or_followup`.
- `target_recovery`: `selected_target`, `hypothesis`,
  `output_root_or_evidence`, `target_state_update`,
  `decision_after_completion`.

Final response: short operational summary including whether jobs were launched
and the batch directory.
