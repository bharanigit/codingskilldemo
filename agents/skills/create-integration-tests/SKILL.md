---
name: create-integration-tests
description: Create or maintain full-initiative, config-driven integration tests. Authors setup and validation Python scripts and integration_tests.json entries for pipeline execution. Bootstraps the suite runner and config when they do not exist. Works without compiled artifacts or a live Databricks cluster.
---

# Create Integration Tests

Analyze the complete initiative, account for every discovered production path, and implement all safely testable end-to-end scenarios. Design tests to exercise the initiative's transformation chain from a controlled source anchor through to the curated output, using the mock pltdata framework locally.

## Author Files and Defer Execution

This skill creates or updates repository files and performs static checks. Integration-test execution belongs to a developer-started pipeline run after authoring. Do not execute setup or validation scripts inline.

## Bootstrap Infrastructure When Absent

Before authoring initiative tests, inspect:

```text
databricks/tests/integration/common/run_integration_suite.py
databricks/tests/integration/config/integration_tests.json
```

If either is missing, **create both** before registering any initiative. Follow the templates in `references/runner-and-config.md`. This is a one-time bootstrap step, not a redesign — the created runner and schema become the shared suite contract for all future initiatives.

## Read References Selectively

Always read:

- `references/coverage-planning.md` before deciding implementation scope.
- `references/test-design.md` before choosing the test anchor or test type.
- `references/runner-and-config.md` before editing the suite configuration or creating the runner.
- `references/notebook-patterns.md` before creating or changing setup and validation scripts.

## Inspect the Repository

Inspect at minimum:

- The integration test runner and config (create if absent — see bootstrap step above).
- Existing initiative tests under `databricks/tests/integration/`.
- The initiative's production transforms across all relevant layers.
- Entity definitions, attribute types, and transformation logic in each notebook.

Identify every source anchor, business key, transformation step, derived attribute, curated entity, and downstream path. Do not silently omit a discovered path.

## Apply the Scope Guard

Use this suite for initiatives whose full transformation chain — raw → staging → enriched → curated — can be exercised locally with synthetic data and the mock pltdata framework.

## Plan Full-Initiative Coverage

Default to full-initiative coverage unless the requesting developer explicitly limits scope. Full-initiative coverage requires inspection and classification of every production transform and entity associated with the initiative.

Create the coverage manifest defined in `references/coverage-planning.md`. Assign every path one disposition: `CONTROLLED`, `OBSERVATIONAL`, `EXCLUDED`, or `UNVERIFIED`, with a reason for every non-controlled path.

## Choose Test Mode and Anchor

Use `controlled_test_data` for initiatives whose transformation chain can be exercised end-to-end with synthetic DataFrames. The setup script creates in-memory fixtures; the validation script runs the full transformation chain and asserts on the output.

Use `observational` only when the transformation logic cannot be safely invoked (e.g., external API calls, file-system side effects that cannot be mocked).

Choose the earliest safe anchor. Prefer raw when the raw ingestion is pure Python/Spark with no external dependencies. Otherwise anchor at staging or enriched.

## Preserve the Shared Suite Architecture

Treat the runner and config schema as immutable once created. Every config entry must follow:

```text
one setup script -> one validation script
```

Use one setup and validation script pair per initiative. Do not modify the runner, the config schema, or the execution sequence when adding a new initiative.

If required coverage cannot fit the contract, report the unsupported requirement and the highest supportable boundary. Never redesign the shared suite as an incidental part of initiative work.

## Implement the Test

Create or update:

```text
databricks/tests/integration/<initiative>/
  setup_<initiative>.py
  validate_<initiative>.py
```

Register the test in `databricks/tests/integration/config/integration_tests.json`.

Ensure setup is deterministic and idempotent. Pass only required context through the `setup_result` dictionary. Ensure validation proves mappings, joins, filters, keys, and the declared boundary for every supported scenario.

Follow `references/notebook-patterns.md` for the exact script structure.

## Verify Before Completion

Perform static checks only:

- Parse `integration_tests.json` as JSON and confirm it is valid.
- Confirm canonical config values (test_type, allowed_envs, required_boundary).
- Confirm the coverage manifest accounts for every discovered initiative path.
- Confirm each non-controlled path has an explicit disposition and reason.
- Confirm every claimed boundary has fatal, meaningful assertions.
- Confirm the runner and config schema were not changed after bootstrap.

Report files created or updated, static checks completed, and coverage status for each path. Explicitly state that integration tests were not executed and require a developer-started pipeline run.
