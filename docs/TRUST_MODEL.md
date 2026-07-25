# Trust Model

Experiment Control Agent is a server-side research operator. It can read the
configured project context, make research decisions, and run commands in the
configured environment. Treat a real deployment as trusted automation, not as
an untrusted-code sandbox.

## What The Runtime Enforces

- `runtime/PAUSE` makes the supervisors skip new planning cycles;
  `runtime/STOP` makes them exit. A direct runner invocation is still an
  operator action and should be treated accordingly.
- A planning-cycle lock prevents two instances of the same runner from
  starting concurrently.
- `bootstrap_layout.py` creates only simple-name symlinks below `workspaces/`
  and `originals/`; it refuses to replace existing files or directories.
- Cycle outcomes and managed batch status have structural validators that
  report incomplete state so later cycles can recover it.
- `doctor.py` reports missing paths, malformed configuration, missing explicit
  `writable` declarations, and originals marked writable.

These are operational safeguards. They preserve state and prevent a few common
mistakes; they do not confine arbitrary processes after launch.

## What The Profile And Planner Must Respect

- `workspaces.*.writable` and `originals.*.writable` are declarations for the
  planner and reviewer. They are not filesystem permission enforcement.
- Project policy files determine which datasets, commands, schedulers, output
  roots, and external services are in scope.
- Research decisions, including hypotheses, experiment design, prioritization,
  interpretation, and mode changes, remain the planner's responsibility.

Keep original data and historical experiment roots read-only at the filesystem
level whenever possible. Use a separate writable rerun workspace for generated
code, outputs, checkpoints, and scratch data.

## Planning-Cycle Privilege

The bundled Codex runner invokes `codex exec` with
`--dangerously-bypass-approvals-and-sandbox`. This is intentional for an agent
that must operate a server, but it means the planner can execute commands with
the permissions of the account running the agent. It is not appropriate for
unreviewed profiles, untrusted prompts, or a shared account with sensitive
access.

Start every new project in `manual` mode. Review the rendered prompt, profile,
symlink targets, and first planning-cycle output before enabling an automatic
supervisor. Keep `runtime/PAUSE` present until that review is complete.

## Recommended Deployment Boundary

1. Use a dedicated Unix account or isolated machine for the experiment agent.
2. Grant that account access only to the needed repositories, datasets, compute
   queues, and credentials.
3. Mount or permission original/reference roots read-only; make only rerun
   workspaces writable.
4. Keep `configs/project.json`, provider auth, runtime state, logs, and private
   project material untracked.
5. Run `python3 scripts/doctor.py --strict` and review its warnings before
   enabling automatic cycles.

The framework is deliberately not a fixed scientific workflow. These boundaries
constrain where and how the researcher-like agent operates, not what scientific
idea it is allowed to pursue within the configured project.
