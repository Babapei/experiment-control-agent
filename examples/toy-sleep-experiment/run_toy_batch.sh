#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="$(date '+%Y%m%d_%H%M%S')"
BATCH_DIR="$BASE_DIR/runtime/batch_low_api/batches/toy_${STAMP}"
RESULT_ROOT="$BASE_DIR/examples/toy-sleep-experiment/results/toy_${STAMP}"
LOG_DIR="$BASE_DIR/logs"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$BATCH_DIR" "$RESULT_ROOT" "$LOG_DIR" "$BASE_DIR/runtime/batch_low_api"

cat > "$BATCH_DIR/manifest.tsv" <<EOF
id	lane	target	resources	output_root	log_path	decision_after_completion
toy-a	toy_lane	toy-a	cpu	$RESULT_ROOT/toy-a	$LOG_DIR/toy-a_${STAMP}.log	completed.json exists
toy-b	toy_lane	toy-b	cpu	$RESULT_ROOT/toy-b	$LOG_DIR/toy-b_${STAMP}.log	completed.json exists
toy-c	toy_lane	toy-c	cpu	$RESULT_ROOT/toy-c	$LOG_DIR/toy-c_${STAMP}.log	completed.json exists
EOF

cat > "$BATCH_DIR/plan.md" <<EOF
# Toy Batch Plan

- Batch: \`toy_${STAMP}\`
- Objective: launch three CPU-only toy sleep jobs.
- Output root: \`$RESULT_ROOT\`
- Decision: each package completes when its \`completed.json\` exists.

No Codex, GPU, tmux, dataset, or model training is required.
EOF

cat > "$BASE_DIR/runtime/batch_low_api/current_batch.md" <<EOF
# Current Low-API Batch

- Batch directory: \`$BATCH_DIR\`
- Plan: \`$BATCH_DIR/plan.md\`
- Manifest: \`$BATCH_DIR/manifest.tsv\`
- Launched at: $(date '+%F %T')
- Profile: toy
EOF

cat > "$BASE_DIR/runtime/current_status.md" <<EOF
# Current Status

- State: toy batch launched.
- Agent mode: \`$(cat "$BASE_DIR/runtime/AGENT_MODE" 2>/dev/null || echo method_exploration)\`
- Execution mode: \`$(cat "$BASE_DIR/runtime/EXECUTION_MODE" 2>/dev/null || echo manual)\`
- Current phase: three toy sleep tasks are running or have completed.
- Active/background jobs: inspect with \`scripts/list_active_jobs.py\`.
- Latest completed evidence: inspect \`$RESULT_ROOT/*/completed.json\`.
- Next planned action: wait for toy tasks to finish, then inspect results.
- Blockers: none.
EOF

cat > "$BASE_DIR/runtime/research_lanes.md" <<EOF
# Research Lanes

### toy_lane

- Status: running
- Target: toy-a, toy-b, toy-c
- Current hypothesis: sleep jobs should complete and write JSON results.
- Active command/resource/log: see \`$BATCH_DIR/manifest.tsv\`.
- Latest evidence: pending.
- Next action: inspect completed JSON files.
EOF

{
  echo
  echo "## $(date '+%F %T') toy batch toy_${STAMP}"
  echo
  echo "- Batch directory: $BATCH_DIR"
  echo "- Result root: $RESULT_ROOT"
  echo "- Manifest: $BATCH_DIR/manifest.tsv"
} >> "$BASE_DIR/runtime/agent_journal.md"

for task in toy-a toy-b toy-c; do
  duration=5
  [[ "$task" == "toy-b" ]] && duration=6
  [[ "$task" == "toy-c" ]] && duration=7
  "$BASE_DIR/scripts/launch_batch_job.sh" \
    "$BATCH_DIR" \
    "$task" \
    "$RESULT_ROOT/$task" \
    "$LOG_DIR/${task}_${STAMP}.log" \
    -- \
    "$PYTHON_BIN" "$BASE_DIR/examples/toy-sleep-experiment/toy_task.py" \
    --task-id "$task" \
    --duration "$duration" \
    --output-dir "$RESULT_ROOT/$task"
done

echo "Launched toy batch: $BATCH_DIR"
echo "Result root: $RESULT_ROOT"
echo "Run: scripts/list_active_jobs.py"
echo "Status: $BATCH_DIR/status.tsv"
