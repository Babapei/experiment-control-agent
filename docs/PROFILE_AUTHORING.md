# Profile Authoring

A profile is the project-specific layer that tells the generic agent what the
experiment means.

## Minimal Steps

1. Copy `configs/project.example.json` to `configs/project.json`.
2. Create a directory under `profiles/<your-project>/`.
3. Add `AGENTS.project.md` for policy and safety rules.
4. Add `CYCLE_BRIEF.md` for compact per-cycle context.
5. Point `project_docs` in `configs/project.json` to those files.
6. Configure workspaces, job detection regexes, result watch paths, and batch
   manifest columns.
7. Run `python3 scripts/doctor.py`.

## What Belongs In A Profile

- Research objective.
- Agent mode contracts for project-specific objective modes.
- Trusted and untrusted evidence sources.
- Writability rules for workspaces and originals.
- Target rows, metrics, or acceptance criteria.
- Preferred final runners and helper runners.
- Job categories and expected process patterns.
- Result file locations and aggregate naming conventions.
- Status vocabulary.
- Lane and dashboard templates.

## What Does Not Belong In Core

- A paper's exact table values.
- Dataset paths.
- Conda environment names.
- Runner script names.
- Domain-specific metric interpretations.
- Private historical notes.

## Mode Contract Tips

Do not add an `AGENT_MODE` only because the name sounds useful. A good mode
contract says what the planner must do differently in that mode.

For example, an audit mode should say which uncertainty it reduces, what audit
artifact it must produce, and what evidence promotes a probe into a larger run.
A target-recovery mode should say how targets are ranked, what counts as a
concrete push, and when a failed candidate leaves the target open.

## Job Detection Tips

`job_detection.managed_hints` narrows process matching to your project. Include
the control root and distinctive workspace names. Then add regexes for the
actual long-running commands.

Example:

```json
{
  "managed_hints": ["{root}", "my-rerun-workspace"],
  "patterns": [
    {"category": "batch_wrapper", "regex": "runtime/batch_low_api/batches/.*/run_.*\\.sh"},
    {"category": "training", "regex": "(^|/|\\s)train\\.py(\\s|$)"}
  ]
}
```

## Result Signature Tips

The event and batch supervisors use `results.watch_paths` and
`results.file_patterns` to decide whether state changed enough to call Codex.
Keep these patterns narrow enough to avoid waking on every log write, but broad
enough to catch final aggregates and completion markers.
