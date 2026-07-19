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
3. the configured project policy and cycle brief under `project_docs`
4. `runtime/AGENT_MODE`
5. `runtime/EXECUTION_MODE`; expect `batch_low_api`
6. `runtime/BATCH_PROFILE`
7. `runtime/current_status.md` if it exists
8. `runtime/research_lanes.md` if it exists
9. the last 80-120 lines of `runtime/agent_journal.md` if it exists

Batch-planning rules:

- Check active managed jobs first. If substantial work is still active, do not
  launch conflicting work.
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

Required low-API artifacts:

1. Create `runtime/batch_low_api/batches/<timestamp>/`.
2. Write `plan.md`.
3. Write `manifest.tsv` using the configured manifest columns.
4. Update `runtime/batch_low_api/current_batch.md`.
5. Update `runtime/current_status.md`.
6. Append to `runtime/agent_journal.md`.
7. Update project-specific ledgers or dashboards if state changed.

Final response: short operational summary including whether jobs were launched
and the batch directory.
