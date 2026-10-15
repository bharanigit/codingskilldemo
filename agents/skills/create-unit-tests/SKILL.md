---
name: create-unit-tests
description: Create or update a pytest unit test for one Databricks transform notebook or integration-lib module. Reads source notebooks directly — no compiled artifacts or compiler step required.
---

# Create Unit Tests

Create one isolated pytest module for one explicitly selected production notebook or library module. Keep it deterministic, compatible with the PR unit-test pipeline, and independent of Databricks storage, deployed workflows, secrets, and external systems.

Read `references/implementation-guide.md` before implementing or updating a test.

When operating in Databricks Claude Code, also read `references/genie-code-workflow.md` for workspace-specific guidance.

## Enforce One Target

Handle exactly one production notebook or one library module per request.

Accept an exact path, a layer-qualified notebook name, or a name that resolves to exactly one file. If a name matches multiple files, show the candidates and ask the user to select one. If the request names an initiative, source system, or multiple layers instead of one target, do not expand it into initiative-wide coverage; ask for one notebook or library module.

Do not discover or test downstream consumers. For a selected notebook, inspect only that notebook and its direct declared sources.

## Select the Test Mode

Use **source-notebook mode** for production transforms under Databricks layers (`1-raw`, `3-staging`, `4-enriched`, `5-curated`). Read the source notebook directly to understand its entity definitions and transformation logic.

Use **library-function mode** for modules under `databricks/lib/integration-lib/integration/functions/` or equivalent. Import these modules directly; do not add `run_unittest=True` to library function calls.

Keep the test path parallel to the production path and prefix the production filename with `test_`:

```text
databricks/3-staging/mockapi/transform_employees.py
databricks/tests/unit/3-staging/mockapi/test_transform_employees.py
```

## Inspect Shared Test Infrastructure

Before implementation, inspect:

- `databricks/tests/conftest.py` — shared Spark fixture and runtime stubs
- Relevant helpers under `databricks/tests/test_utils/`
- Existing tests nearest to the selected target
- `pytest.ini`

If no shared test infrastructure exists, create a minimal `conftest.py` alongside the test that provides a local `SparkSession` fixture. Do not modify existing shared infrastructure unless explicitly requested.

## Read the Source Notebook

Read the selected source notebook to understand:

- Source and target `Entity(...)` definitions, including all attributes, types, keys, and locators
- Transformation logic: column renames, type casts, derived columns, filters, deduplication
- External dependencies: lifecycle handlers, framework calls, file reads, API calls
- Runtime branches that depend on environment metadata or external state

Do not import or execute the source notebook directly in the test module.

Instead, extract what the test needs:

1. **Entity definitions** — copy the `Entity(...)` constructors verbatim from the notebook into the test module, preserving all attributes and types. These are the authoritative schema source for `SchemaTranslate`.
2. **Transformation logic** — replicate the notebook's PySpark expressions as a **standalone Python function** in the test module. This function receives one or more source DataFrames and returns the transformed DataFrame. Omit framework orchestration (`PltDebugTransform`, lifecycle handlers, `end_transform`) — test only the transformation expressions.

When the notebook's transformation is embedded in a loop (e.g., processing multiple uploaded files per iteration), extract the per-iteration transformation into a standalone function and test it with a single synthetic batch.

## Discover Direct Inputs and Output

From the source notebook, identify:

- Every source entity and its direct Spark schema (via `SchemaTranslate`)
- The target entity and its expected Spark schema
- Runtime collaborators used inside the transformation (environment metadata, clocks, API calls)
- Joins, mappings, filters, null handling, deduplication, and other branches that require test coverage

## Handle Direct Table Reads

Inspect the notebook body for direct reads such as `spark.table(...)` or `spark.read.table(...)`. These are additional direct inputs even when absent from the entity declarations.

For each statically identifiable table:

1. Resolve its entity definition from repository source notebooks.
2. Derive the fixture schema via `SchemaTranslate` and create synthetic CSV rows.
3. Patch the `spark` reference used by the transformation with an exact-name router that fails loudly on any unexpected table name.

If the schema cannot be resolved, ask the user for the schema or a synthetic fixture rather than inventing columns.

## Build Notebook Fixtures

Create one synthetic CSV fixture for every direct source entity. Place it under:

```text
databricks/tests/data/<source-layer>/<source-system>/<source-system>_<source-entity>.csv
```

Use lowercase snake case. Do not repeat the source-system prefix when the entity name already begins with it. Do not append a layer suffix (`_staging`, `_enriched`) to the filename — the parent directory already identifies the layer.

Derive columns from the source entity's `attributes` list using `SchemaTranslate`. Include every schema column. Design rows from the notebook's actual behavior — include matching and non-matching keys for joins, meaningful mapped values, nulls, duplicates, and boundary values only when the transform handles them. Use synthetic values; never copy secrets, credentials, or production PII.

## Implement Meaningful Assertions

Define the transformation as a standalone function and invoke it via a module-scoped fixture:

```python
def apply_transform(source_df):
    """Replicates the notebook's PySpark transformation expressions."""
    ...

@pytest.fixture(scope="module")
def transformed_df(source_df):
    return apply_transform(source_df)
```

At minimum, assert that output column names and types match the target entity schema via `SchemaTranslate`. Add focused behavioral tests for each important transformation in the selected notebook.

Prefer assertions by stable synthetic keys over full-table row counts or unordered row positions.

Create one focused test per distinct behavior. Do not combine unrelated filters, joins, mappings, deduplication, and aggregations into one broad test.

Do not use `cache()` or `persist()` in generated tests. When multiple tests share the same inputs and runtime conditions, invoke the transform once and collect its result once in a module-scoped fixture, then reuse those collected rows. Use separate transform invocations only when a scenario requires different input rows, mocks, or runtime state.

Mock only external or runtime behavior that is outside the unit under test (environment metadata, API clients, clocks, filesystem adapters). Do not mock the Spark expressions, joins, mappings, or filters that constitute the notebook's behavior.

For library-function mode, test the selected functions directly. Use the shared Spark fixture for Spark expressions; use ordinary pytest fixtures and mocks for Python clients and APIs.

Do not disable a failing test by commenting it out. Do not add a skip merely to complete the request. Fix the test when the intended behavior is clear, or report the concrete blocker.

## Verify the Result

Do not run pytest from Claude Code. Defer execution to local development or the PR unit-test pipeline.

After generating a test in Claude Code, report:

```text
The unit test and synthetic fixtures were generated by reading the source
notebook directly. No compiled artifacts were required.

Pytest was not executed in Claude Code. Run the target test locally or use
the PR unit-test pipeline.
```

In a local environment, run from the repository root:

PowerShell:
```powershell
$env:PYTHONPATH = "path\to\pltdata;$env:PYTHONPATH"
python -m pytest <test-file> -v
```

Do not run the complete unit suite by default when only the selected test or its private CSV fixtures changed. The PR pipeline provides the complete regression check.

When pytest ran locally, report the target result separately from unrelated existing suite failures. In every environment, state the created test path, fixture paths, behaviors covered, mocks applied, and any remaining limitations.
