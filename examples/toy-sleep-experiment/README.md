# Toy Sleep Experiment

This example is intentionally boring: it launches a few CPU-only sleep jobs that
write `completed.json` files. It exists so new users can exercise the control
plane without Codex auth, GPUs, datasets, or a real training codebase.

It demonstrates:

- project config
- active job detection
- result signature changes
- low-API batch artifacts
- status, journal, and lane ledgers

Run it from the repository root:

```bash
cp examples/toy-sleep-experiment/project.json configs/project.json
python3 scripts/bootstrap_layout.py
scripts/run_checks.sh

examples/toy-sleep-experiment/run_toy_batch.sh
scripts/list_active_jobs.py
sleep 8
find examples/toy-sleep-experiment/results -name completed.json -print
scripts/show_runtime_status.sh
```

Remove `configs/project.json` before publishing if it contains local machine
paths or private project details.

