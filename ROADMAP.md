# Roadmap

This roadmap is the implementation contract for turning the extracted scaffold
into a public, reusable LLM experiment-control agent. Keep core behavior generic. Put
project-specific research knowledge into profiles.

## Final Shape

The repository should be usable by another researcher who can:

1. Clone the repository.
2. Copy `configs/project.example.json` to `configs/project.json`.
3. Define workspaces, environment activation, managed job patterns, watched
   result files, metrics, and project docs.
4. Authenticate the configured LLM provider.
5. Run manual, interval, event, or low-API batch supervision without editing
   core scripts.

The public repository must not contain private credentials, historical runtime
logs, private manuscript material, raw datasets, generated artifacts, or
machine-specific project state.

## Architecture Boundary

### Core

- process supervisors
- LLM invocation through the configured provider
- pause/stop state
- mode switching
- low-API batch state
- retry/backoff/fallback
- optional supplemental idle-resource batches
- active job detection
- result signature calculation
- runtime validation
- usage logging
- publish-safe docs and examples

### Project Profile

- research objective
- project-specific safety policy
- workspaces and read-only originals
- environment activation commands
- managed job regexes
- result watch paths and file patterns
- metric definitions
- target row/state vocabulary
- preferred runners and command maps
- lane/dashboard templates
- private reference docs

## Implementation Phases

### Phase 1: Planning And Scope Lock

- Add this roadmap.
- Add a concise architecture document.
- Keep the existing project-specific agent untouched.
- Commit the planning/scope files.

### Phase 2: Configuration Hardening

- Add a first-class config inspection command.
- Validate configured paths, mode defaults, batch profiles, manifest columns,
  job regexes, and project doc references.
- Add a `doctor` command for publish-safe preflight checks.
- Improve bootstrap output and setup ergonomics.
- Commit config/tooling changes.

### Phase 3: Low-API Supervisor Completeness

- Reintroduce configurable retry/backoff for temporary Codex failures.
- Reintroduce model/reasoning fallback profiles through config.
- Reintroduce optional supplemental cycles for idle resources while long jobs
  are still active.
- Keep all thresholds project-configurable.
- Commit supervisor changes.

### Phase 4: Prompt/Profile System

- Make prompts explicitly render or reference configured project docs.
- Add a complete generic default profile.
- Keep the E+A/SBM profile sanitized and clearly marked as an example.
- Add templates for status, lane ledger, batch plan, and target dashboard.
- Commit prompt/profile changes.

### Phase 5: Tests And Compatibility

- Add unit tests for config loading, job detection, signature calculation, and
  validation.
- Add shell syntax checks.
- Test on macOS and Linux server shells.
- Avoid hard dependencies on `tmux`, `nvidia-smi`, or conda when not configured.
- Commit tests.

### Phase 6: Release Preparation

- Add license placeholder or selected license.
- Add GitHub-oriented README sections.
- Add security/publishing checklist.
- Add example `project.json` variants for common setups.
- Sync to the server new directory and run validation.
- Commit release docs.

## Non-Goals For The Public Core

- Domain-specific experiment design.
- Hardcoded paper metrics.
- Hardcoded conda environments.
- Hardcoded GPU counts.
- Hardcoded runner scripts.
- Automatic destructive cleanup.
- Storing API credentials or runtime state in git.

## Commit Discipline

Make small commits at phase boundaries or after a cohesive feature is verified.
Each commit should keep the repository runnable.

## Current Progress

Baseline extraction completed:

- Phase 1 complete: roadmap and architecture boundary committed.
- Phase 2 complete: default profile, config inspection, and doctor committed.
- Phase 3 complete: configurable retry, fallback, and supplemental low-API
  cycles committed.
- Phase 4 complete: rendered prompts and generic templates committed.
- Phase 5 complete: local check suite and unit tests committed.
- Phase 6 complete: release/profile/security docs and MIT license committed.

Remaining optional hardening before a public v1 tag:

- Add CI configuration after the GitHub repository exists.
- Decide whether MIT is the final license.
- Add richer real-world sanitized example profiles if desired.
- Add scheduler adapters such as Slurm/PBS if users need them.
- Add a small CLI wrapper command if the shell/Python script surface feels too
  fragmented.
