---
name: create-integration-tests
description: Create or maintain full-initiative, config-driven Databricks integration tests from local development or Claude Code. Author setup and validation notebooks and integration_tests.json entries for pipeline execution after deployment, preserving the single-workflow suite contract. Use for new initiatives, added or modified production notebooks, and coverage gaps.
---

# Create Integration Tests

Analyze the complete initiative, account for every discovered production path, and implement all safely testable scenarios that fit the fixed shared suite contract. Design tests to exercise deployed production code through the single configured production workflow.

## Author Files and Defer Execution

This skill creates or updates repository files and performs static checks. Integration-test execution belongs to a developer-started pipeline run after deployment. Do not execute or import setup notebooks, validation notebooks, or the suite runner. Do not trigger production workflows or the integration pipeline, or deploy files as part of authoring tests.

Repository compilation is allowed when current compiled references are missing or stale. Compilation is separate from deployment and test execution. Runtime actions described in this skill and its references, including fixture writes and validation queries, describe behavior to implement in the generated notebooks for pipeline execution.

## Read References Selectively

Always read:

- `references/coverage-planning.md` before deciding implementation scope.
- `references/test-design.md` before choosing the test anchor or test type.
- `references/runner-and-config.md` before editing the suite configuration.

Read when applicable:

- `references/genie-code-workflow.md` whenever operating in Claude Code or resolving missing or stale compiled artifacts.
- `references/workflow-verification.md` whenever selecting or verifying a production workflow.
- `references/notebook-patterns.md` before creating or changing setup and validation notebooks.

Do not rely on remembered architecture. Rebuild the initiative lineage from the repository.

## Inspect the Repository

Inspect at minimum:

- `databricks/tests/integration/common/run_integration_suite.py`
- `databricks/tests/integration/config/integration_tests.json`
- Existing initiative tests under `databricks/tests/integration/`
- The initiative's production transforms across all relevant layers
- `.config/module.json`
- Current compiled functions under `databricks/lib/integration-lib/integration/bin/`, using the Claude Code reference for Shared discovery and compilation fallback
- Generated or deployed workflow tasks when available
- Entity, schema, DRL, lookup, and SQL-view definitions used by every initiative path

Inspect the CI/CD pipeline YAML under `databricks/.azuredevops/` when deployment artifact coverage matters.

Identify every source anchor, business key, dependency, intermediate checkpoint, curated entity, downstream serving entity, export boundary, workflow name, and environment safety constraint. Do not silently omit a discovered path.

## Apply the Scope Guard

Use this suite for batch platform workflows whose boundary can be validated in lakehouse tables.

## Plan Full-Initiative Coverage

Default to full-initiative coverage unless the requesting developer explicitly limits the scope to a named entity or path. Full-initiative coverage requires inspection and classification of every production transform, entity, SQL view, export, and external adapter associated with the initiative; it does not require unsafe controlled data for every notebook.

For an existing initiative, reuse its setup and validation pair and configuration, preserve valid existing scenarios, and fill supported coverage gaps against the current production paths. For a new initiative or one without integration tests, create the pair and configuration for all currently implemented, supported paths. Follow the maintenance rules in `references/coverage-planning.md`.

Create the coverage manifest defined in `references/coverage-planning.md`. Assign every path one disposition: `CONTROLLED`, `OBSERVATIONAL`, `EXCLUDED`, or `UNVERIFIED`, with a reason for every non-controlled path.

For paths that fit the configured workflow and test mode, prefer multiple independent scenarios inside the initiative's single setup and validation notebooks. Use a combined scenario as well when joins, unions, coalescing, deduplication, or cross-input behavior must be proved.

Choose the earliest deterministic and safe anchor for each supported path. Prefer raw only when CQ owns it and setup is repeatable. Otherwise use staging, enriched, curated, or observational context as described in `references/test-design.md`.

## Preserve the Shared Suite Architecture

Treat the shared suite architecture as immutable while creating or updating an initiative test. Every config entry must follow:

```text
one setup notebook -> optional single production workflow -> one validation notebook
```

The workflow slot runs or is skipped according to the existing controlled or observational contract. Use one setup and validation notebook pair per initiative; DEV and QUA config entries may reuse that same pair.

Implement multiple scenarios inside those notebooks and pass one consolidated `setup_result`. Do not modify the shared runner, pipeline definition, config schema, or execution sequence. Do not add multiple setup notebooks, multiple workflow names, multiple validation notebooks, `target_notebooks`, or direct transformation-notebook execution.

If required coverage cannot fit the contract, do not redesign the suite. Implement a lower boundary only when it still honestly satisfies the requested scope; otherwise stop and report the unsupported requirement, highest supportable boundary, excluded path, and separately approved platform change that would be required.

## Choose Test Mode and Boundary

Use `controlled_test_data` when CQ owns a safe writable anchor. Use `observational` when mutation is unsafe or the source is externally owned.

Configure the generated tests for these pipeline behaviors:

- Run controlled tests only in DEV.
- Allow observational tests in DEV and QUA.

Make the declared boundary match fatal assertions.

## Configure Production Execution

Treat platform transformation notebooks as source definitions rather than runtime entry points. Verify this path for every in-scope stage:

```text
source transform -> compiled function -> deployed workflow task -> platform execution
```

Set `target_job_name` for the suite runner to invoke during pipeline execution when the test mode requires it. Do not trigger the job while authoring. Never run a transformation source notebook directly with `dbutils.notebook.run`, and never add a `target_notebooks` workaround.

The runner supports one production workflow invocation. Do not claim a multi-workflow boundary or change the runner to create one. For scenario 3, stop at the boundary executed by the configured job and disclose the downstream exclusion and its reason.

## Implement the Test

Create or update:

```text
databricks/tests/integration/<initiative>/
  setup_<initiative>.py
  validate_<initiative>.py
```

Register the test in `databricks/tests/integration/config/integration_tests.json`.

Ensure setup is safe, deterministic, and idempotent. Pass only required context through notebook exit JSON. Ensure validation proves mappings, joins, filters, keys, identities, and the declared boundary for every supported scenario in the coverage manifest.

When the initiative has multiple supported paths, implement one structured context containing all scenarios. Implement validation to evaluate each scenario independently, print a consolidated scenario summary, and fail once at the end if any scenario failed.

## Verify Before Completion

Perform static checks only. Parse Python syntax without importing or executing the test notebooks. Read workflow and schema metadata when available; do not run a job to obtain verification evidence.

- Parse `integration_tests.json` as JSON.
- Confirm canonical config values and environment restrictions.
- Confirm the production workflow name and required task dependency path using evidence for the current code, or report the exact pending verification.
- Confirm the compiled functions exist for every claimed layer.
- Confirm setup does not write directly to export folders.
- Confirm incremental rules cannot omit controlled data.
- Confirm the coverage manifest accounts for every discovered initiative path.
- Confirm each non-controlled path has an explicit disposition and reason.
- Confirm every claimed boundary has fatal, meaningful assertions.
- Confirm the shared runner, pipeline, and config schema were not changed.
- State skipped adapters, separate workflows, ownership limits, and unverified assumptions.

Report the files and coverage created or updated, repository or Shared artifacts inspected, whether compilation ran, static checks completed, and deployment evidence still pending. Explicitly state that integration tests were not executed and require deployment followed by a developer-started pipeline run. Do not describe compilation, generated assertions, or static checks as passing integration tests.
