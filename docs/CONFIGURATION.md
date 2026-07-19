# Configuration

The core agent reads `configs/project.json`. If that file is missing, scripts
fall back to `configs/project.example.json`.

Use JSON intentionally: it keeps the first public version dependency-free on
older Python installations. A YAML loader can be added later as an optional
feature.

Important sections:

- `codex`: Codex home, authentication behavior, conda activation, optional
  model defaults.
- `modes`: allowed agent/execution modes and batch profile soft targets.
- `workspaces`: writable project workspaces linked under `workspaces/`.
- `originals`: read-only references linked under `originals/`.
- `job_detection`: process hints and regexes used by `list_active_jobs.py`.
- `results`: watched result paths and filename patterns used for event
  signatures.
- `batch.manifest_columns`: required columns for low-API batch manifests.
- `project_docs`: project-specific policy and reference files.

For a field-by-field reference, see `docs/CONFIG_REFERENCE.md`.

Prompt rendering uses these fields on every Codex call. Check the rendered
prompt with:

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
