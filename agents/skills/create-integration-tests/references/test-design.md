# Integration Test Design

## Choose the Anchor

Choose the earliest input that is deterministic, writable, and safe:

- Use raw only when CQ controls the raw table or can exercise ingestion safely and repeatedly.
- Use staging, enriched, or curated when raw ingestion is external, asynchronous, source-owned, or impractical to reproduce.
- State which upstream adapter is excluded when beginning downstream of raw.
- Use observational mode when no safe controlled anchor exists.

For multi-input transforms, classify each dependency separately. Reuse stable existing lookup rows when ownership prevents synthetic fixtures. Create controlled trigger data only in CQ-owned inputs.

## Choose the Test Type

Use `controlled_test_data` when a deterministic fixture can be inserted or merged safely. Give it a unique key or marker and make reruns idempotent.

Use `observational` when mutation is unsafe. Select stable existing data with deterministic ordering and enough populated fields to prove meaningful mappings.

Before choosing fully observational testing, consider whether a safe CQ-owned downstream anchor can reuse eligible read-only lookups. Do not silently downgrade requested full-path coverage.

## Select Anchors for the Coverage Manifest

For every discovered initiative path, record:

- source anchor and ownership
- business key or unique marker
- required lookup and join dependencies
- intermediate checkpoints
- curated entity
- external-system boundary

Include every safely testable path that belongs to the configured workflow and compatible test mode. Use multiple independent identities rather than one synthetic record when one record could allow branches to mask each other. Add a combined identity when cross-input behavior must be proved.

Classify unsafe, external, separate-workflow, and unverified paths explicitly instead of silently omitting them. Prefer assertions on transformations, joins, deduplication, filters, and critical fields over whole-table row counts.

## Handle Environments

- Controlled tests normally use `allowed_envs: ["dev"]`.
- Observational tests may use `allowed_envs: ["dev", "qua"]`.
- Never permit controlled test data in QUA without explicit approval; the runner rejects it.
