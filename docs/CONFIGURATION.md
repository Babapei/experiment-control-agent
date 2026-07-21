# Configuration

The core agent reads `configs/project.json`. If that file is missing, scripts
fall back to `configs/project.example.json`.

Use JSON intentionally: it keeps the first public version dependency-free on
older Python installations. A YAML loader can be added later as an optional
feature.

Important sections:

- `provider`: planning-provider adapter type and command. The bundled adapter
  is `codex`.
- `codex`: Codex adapter settings, including Codex home, authentication
  behavior, conda activation, optional model defaults, and fallback model
  settings.
- `modes`: allowed agent/execution modes and batch profile soft targets.
- `workspaces`: writable project workspaces linked under `workspaces/`.
- `originals`: read-only references linked under `originals/`.
- `job_detection`: process hints and regexes used by `list_active_jobs.py`.
- `results`: watched result paths and filename patterns used for event
  signatures.
- `batch.manifest_columns`: required columns for low-API batch manifests.
- `project_docs`: project-specific policy and reference files.

For a field-by-field reference, see `docs/CONFIG_REFERENCE.md`.
For mode behavior and feature explanations, see `docs/FEATURES_AND_MODES.md`.

## Configuration Order

For a new project, configure in this order:

1. `workspaces` and `originals`, so write boundaries are clear.
2. `project_docs`, so the rendered prompt contains project policy.
3. `job_detection`, so active jobs are not missed or overcounted.
4. `results`, so supervisors wake on meaningful artifacts.
5. `modes` and `batch`, so unattended behavior matches your budget.
6. `provider` and `codex`, so the planning-provider adapter can authenticate
   and run in the right environment.

For `modes`, define objective modes as contracts. Every value in
`modes.agent_modes` needs a matching `modes.agent_mode_contracts.<mode>` entry.

Prompt rendering uses these fields on every planning-provider call. Check the
rendered prompt with:

```bash
python3 scripts/render_prompt.py cycle
python3 scripts/render_prompt.py batch_low_api
```

## Inspection And Doctor

Print the resolved config:

```bash
python3 scripts/inspect_config.py
```

Run setup checks:

```bash
python3 scripts/doctor.py
```

Use strict mode in CI or before publishing:

```bash
python3 scripts/doctor.py --strict
```

Warnings are not always fatal. For example, `nvidia-smi` may be unavailable on a
CPU-only development laptop, but required on the actual GPU server.
