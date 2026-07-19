# Roadmap

This roadmap records the current public shape of the extracted scaffold and the
remaining hardening ideas for a reusable LLM experiment-control agent. Keep core
behavior generic. Put project-specific research knowledge into profiles.

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

## Completed Extraction Phases

### Phase 1: Planning And Scope Lock

- Roadmap and architecture boundary added.
- Existing project-specific agent kept untouched.
- Planning/scope files committed.

### Phase 2: Configuration Hardening

- First-class config inspection command added.
- Validation added for configured paths, mode defaults, batch profiles,
  manifest columns, job regexes, and project doc references.
- `doctor` command added for publish-safe preflight checks.
- Bootstrap output and setup ergonomics improved.

### Phase 3: Low-API Supervisor Completeness

- Configurable retry/backoff added for temporary planning-provider failures.
- Model/reasoning fallback profiles added through config.
- Optional supplemental cycles added for idle resources while long jobs
  are still active.
- All thresholds kept project-configurable.

### Phase 4: Prompt/Profile System

- Prompts explicitly render configured project docs.
- Generic default profile added.
- E+A/SBM profile kept sanitized and clearly marked as an example.
- Templates added for status, lane ledger, batch plan, and target dashboard.

### Phase 5: Tests And Compatibility

- Unit tests added for config loading, job detection, signature calculation, and
  validation.
- Shell syntax checks added.
- Tested on macOS and Linux server shells.
- Hard dependencies on `tmux`, `nvidia-smi`, or conda avoided when not
  configured.

### Phase 6: Release Preparation

- MIT license added.
- GitHub-oriented README sections added.
- Security/publishing checklist added.
- Toy example and sanitized profile examples added.
- Server sync and validation completed.

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

## Optional Hardening Before A Public v1 Tag

- Add CI configuration after the GitHub repository exists.
- Decide whether MIT is the final license.
- Add richer real-world sanitized example profiles if desired.
- Add scheduler adapters such as Slurm/PBS if users need them.
- Add a small CLI wrapper command if the shell/Python script surface feels too
  fragmented.
