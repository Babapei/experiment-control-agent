# Getting Started

This guide walks through a no-GPU, no-Codex-auth demo first. After that, it
shows where to plug in a real research project.

## 1. Clone And Check

```bash
git clone git@github.com:Babapei/experiment-control-agent.git
cd experiment-control-agent
scripts/run_checks.sh
```

Expected result:

- shell syntax checks pass
- Python compilation passes
- unit tests pass
- `doctor` has no errors

Warnings about missing `tmux`, `nvidia-smi`, or `codex` can be normal on a
laptop. See `docs/TROUBLESHOOTING.md`.

## 2. Run The Toy Example

The toy example launches three CPU-only sleep jobs and writes JSON completion
files. It does not call Codex.

```bash
cp examples/toy-sleep-experiment/project.json configs/project.json
python3 scripts/bootstrap_layout.py
scripts/run_checks.sh
examples/toy-sleep-experiment/run_toy_batch.sh
```

Immediately after launch:

```bash
scripts/list_active_jobs.py
```

You should see `toy_task` processes for a few seconds.

After the tasks finish:

```bash
find examples/toy-sleep-experiment/results -name completed.json -print
scripts/show_runtime_status.sh
```

You should see three `completed.json` files and a populated
`runtime/current_status.md`.

## 3. Inspect What The Agent Watches

```bash
python3 scripts/compute_signature.py
python3 scripts/inspect_config.py
python3 scripts/render_prompt.py batch_low_api | sed -n '1,80p'
```

The signature changes when watched result files change. The rendered prompt
shows the project docs, mode, batch profile, and manifest schema that would be
sent to the LLM planner.

## 4. Try A Real Project

Create a private profile:

```bash
mkdir -p profiles/my-project
cp profiles/default/AGENTS.project.md profiles/my-project/AGENTS.project.md
cp profiles/default/CYCLE_BRIEF.md profiles/my-project/CYCLE_BRIEF.md
cp configs/project.example.json configs/project.json
```

Edit `configs/project.json`:

- set `project.name`
- set `codex` auth/environment fields
- set `workspaces` and `originals`
- set `job_detection.managed_hints`
- set `job_detection.patterns`
- set `results.watch_paths`
- set `results.file_patterns`
- set `project_docs` to your private profile docs

Then run:

```bash
python3 scripts/bootstrap_layout.py
python3 scripts/doctor.py
scripts/show_runtime_status.sh
```

## 5. Choose An Execution Mode

Manual mode is safest while configuring:

```bash
scripts/set_mode.sh execution manual
```

Low-API batch mode is the recommended server default once the profile is ready:

```bash
scripts/set_mode.sh execution batch_low_api
scripts/set_mode.sh batch_profile auto
rm -f runtime/PAUSE
scripts/launch_tmux_agent.sh
```

Training jobs launched by the agent run as ordinary processes. Codex/LLM calls
happen only at planning boundaries.

## 6. Read Next

- `docs/USER_GUIDE.md`: choose the right documentation path for your use case.
- `docs/FEATURES_AND_MODES.md`: understand capabilities and execution modes.
- `docs/CONFIG_REFERENCE.md`: edit `configs/project.json` correctly.
- `docs/PROFILE_AUTHORING.md`: write a strong project profile.
