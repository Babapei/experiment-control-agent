# Default Cycle Brief

Read this file before each planning cycle when no custom project profile is
configured.

## Cycle Shape

1. Inspect active managed jobs.
2. Inspect concise status and recent journal entries.
3. Follow the active objective mode:
   - `method_exploration`: choose one hypothesis and one informative probe.
   - `audit_validation`: validate one uncertainty before promotion.
   - `target_recovery`: push one target or record a true blocker.
4. Choose one bounded action or batch.
5. Launch only documented non-conflicting work.
6. Update status, journal, lanes, and cycle outcome.
7. Exit.

## Low-API Batch Shape

In `batch_low_api`, create one batch directory under
`runtime/batch_low_api/batches/<timestamp>/`, write `plan.md` and
`manifest.tsv`, update `current_batch.md`, launch jobs, perform a short startup
check, and exit.
