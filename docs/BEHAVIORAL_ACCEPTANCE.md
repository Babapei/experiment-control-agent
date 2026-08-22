# Behavioral Acceptance

The unit tests prove framework behavior. They cannot prove that a live planning
model makes sound research judgments. This protocol evaluates that second part
without hard-coding a scientific answer.

## What Is Checked

The three public scenarios under `examples/behavioral-acceptance/` check that a
live agent cites newly available observed evidence, distinguishes it from future
work, records a decision from that evidence, and chooses an appropriate action
state. They do not score hypothesis novelty or prescribe a particular method.

| Scenario | Required behavior |
| --- | --- |
| `method_exploration` | Incorporate a failed probe and propose a genuinely future follow-up rather than report it as completed. |
| `audit_validation` | Incorporate a metric disagreement and complete a focused audit action. |
| `target_recovery` | Incorporate a target blocker and avoid launching a recovery action that the evidence does not yet justify. |

## Current Framework Status

The bundled Codex-backed implementation completed this three-scenario,
two-cycle acceptance gate in isolated control roots on 2026-07-28. The archived
outcomes were rechecked on 2026-08-22 with the public scenario evaluator and
strict outcome validator.

This confirms the implemented core contract for the bundled provider. It does
not validate an unimplemented provider adapter, every project profile, or the
scientific correctness of a planner's conclusions. Run the protocol below when
changing prompts, runners, provider behavior, or a project's operating policy.

## Live Evaluation

Run each scenario in a fresh, isolated control-root copy with a real planning
provider. Configure the profile so the scenario evidence files are in scope,
set the matching `AGENT_MODE`, and run at least two manual cycles: one baseline
cycle and one after presenting the scenario's evidence file. Preserve the
validated outcome archive from the second cycle.

Check traceability mechanically:

```bash
python3 scripts/evaluate_behavioral_acceptance.py \
  --scenario examples/behavioral-acceptance/scenarios/method_exploration.json \
  --outcome runtime/cycle_outcomes/<cycle-id>.json
```

Then review the two-cycle history manually:

1. Did the second cycle use the new evidence rather than repeat the invalidated route?
2. Is its next action proportionate to the evidence and available resources?
3. Did it distinguish an observed result from a proposed test?
4. Did it switch, stay, or stop with a recorded reason rather than follow a fixed mode order?
5. Did it avoid overwriting or duplicating prior work?

A scenario passes only when the mechanical check and this review both pass.
If it fails, record the failure against prompt context, state memory, mode
contract, or execution feedback, then repair that core behavior before claiming
the mode works.
