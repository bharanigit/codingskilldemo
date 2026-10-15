---
name: create-unit-tests
description: Create or update a pytest unit test for one Databricks transform notebook or integration-lib module. Use compiled integration.bin code for transform execution, support local and Claude Code artifact discovery.
---

# Create Unit Tests

Create one isolated pytest module for one explicitly selected production notebook or library module. Keep it deterministic, compatible with the PR unit-test pipeline, and independent of Databricks storage, deployed workflows, secrets, and external systems.

Read `references/implementation-guide.md` before implementing or updating a test.

When operating in Databricks Claude Code, also read `references/genie-code-workflow.md`. That reference changes how compiled artifacts are found and what can be verified; it does not change the generated pytest format.

## Enforce One Target

Handle exactly one production notebook or one library module per request.

Accept an exact path, a layer-qualified notebook name, or a name that resolves to exactly one file. If a name matches multiple files, show the candidates and ask the user to select one. If the request names an initiative, source system, or multiple layers instead of one target, do not expand it into initiative-wide coverage; ask for one notebook or library module.

Do not discover or test downstream consumers. For a selected serving notebook, inspect only that notebook, its compiled artifact, and its direct declared sources. Treat the upstream transformations that produced those sources as separate unit-test targets.

## Select the Test Mode

Use compiled-notebook mode for production transforms under Databricks layers such as `1-raw`, `3-staging`, `4-enriched`, and `5-curated`.

Use library-function mode for modules under `databricks/lib/integration-lib/integration/`. Import these modules directly; do not compile notebooks and do not add `run_unittest=True` to library function calls.

Keep the test path parallel to the production path and prefix the production filename with `test_` as shown in the reference.

## Inspect Shared Test Infrastructure

Before implementation, inspect:

- `databricks/tests/conftest.py`
- Relevant helpers under `databricks/tests/test_utils/`
- Existing tests nearest to the selected target
- `pytest.ini`
- `.azuredevops/run-unit-test-pr.yml` when environment or execution behavior is uncertain

Reuse the shared Spark fixture, runtime stubs, CSV loader, and schema assertions. Do not modify shared test infrastructure, the compiler, or CI configuration unless the user explicitly requests a framework change.

## Resolve a Compiled Notebook Transform

Read the selected source notebook to understand its entity definitions, decorator configuration, transformation branches, direct calls, and expected behavior. Never import or execute the source notebook in the unit test.

First look for the corresponding generated module under the current repository root:

```text
databricks/lib/integration-lib/integration/bin/
```

If the repository artifact exists and represents the current selected notebook, use it and do not run the compiler. Discover the actual generated filename and function; do not rely only on a derived naming pattern.

When operating in Claude Code and the repository artifact is unavailable or stale, inspect the read-only Shared release fallback according to `references/genie-code-workflow.md`. Use a Shared artifact without compilation only when it represents an unchanged deployed notebook.

If neither location provides a current artifact, tell the user which module requires compilation and run this command from the repository root in either a local environment or Claude Code:

```text
python databricks/.azuredevops/scripts/run_compile_transform.py
```

The compiler processes all transforms and writes generated modules only to the repository `databricks/lib/integration-lib/integration/bin/` directory. Never compile into or modify Shared. After compilation, verify that the expected repository module and transform function exist and import successfully. If either is still missing, stop and report the compiler result instead of guessing an import or testing the source notebook directly. Do not revert unrelated compiler-generated changes automatically.

Regardless of where an artifact was inspected, generated tests must use portable `integration.bin` imports. Never embed `/Workspace/Shared/release`, another absolute artifact path, or an environment-specific `sys.path` change in a test. At execution time, import the transform function, source entity definitions, and target entity definition from compiled `integration.bin` modules only.

## Discover Direct Inputs and Output

From the compiled decorator and function, identify:

- Every direct source parameter in its declared order
- Each source entity, layer, source system, and Spark schema
- The target entity and expected Spark schema
- Runtime collaborators used inside the function body
- Joins, mappings, filters, null handling, deduplication, defaults, and other branches that require evidence

Do not infer source order from filenames. Use the compiled function parameters and decorator source bindings.

Remember that `run_unittest=True` bypasses framework loading and persistence for standard transforms, but does not suppress storage, `dbutils`, secret, network, or API calls written directly in the function body. Mock narrow deterministic collaborators when that makes the body locally safe. If direct side effects cannot be isolated reliably, stop and report the unsafe dependency rather than executing it.

Distinguish connection isolation from runtime metadata. A shared `LakeConnectFactory` or runtime stub may successfully prevent external connections while returning `None` for undeclared properties such as `product_environment`. When runtime metadata selects a transformation branch, patch that property narrowly at the compiled module path with a realistic deterministic value and restore the patch afterward. Do not change the shared stub to establish a framework-wide default unless the user explicitly requests a test-infrastructure change.

## Handle Direct Table Reads

Inspect the function body in every layer for direct reads such as `spark.table(...)` or `spark.read.table(...)`. These are additional direct inputs even when they are absent from the transform decorator, and `run_unittest=True` does not intercept them.

For each statically identifiable table:

1. Resolve its entity definition from repository compiled artifacts or source notebooks. In Claude Code, a matching Shared compiled entity may be inspected read-only.
2. Prefer the entity definition over live catalog metadata. Derive the fixture schema through `SchemaTranslate` and create synthetic CSV rows for the columns and branches used by the transform.
3. If no entity can be resolved, use Unity Catalog schema metadata only when it is available and permitted. Do not read or copy table rows. If the schema is still unavailable or ambiguous, stop and ask the user for the schema or a synthetic fixture.
4. Patch the compiled module's table reader to return the local fixture only for the exact expected table name. An unexpected table name must raise an error; never fall through to Unity Catalog.

Place direct-read fixtures under the same source-layer and source-system convention used for decorator sources. Follow the concrete router pattern in `references/implementation-guide.md`.

Inspect direct writes separately, including `save`, `saveAsTable`, Delta merge operations, and helpers such as `SatHelper.insert_new_hub_entries`. Patch only the external persistence boundary when the transformation remains meaningful, and restore it after the test. If a direct write cannot be isolated without replacing the behavior under test, stop without executing the transform.

## Build Notebook Fixtures

Create one synthetic CSV fixture for every direct source entity. Place it under:

```text
databricks/tests/data/<source-layer>/<source-system>/<source-system>_<source-entity>.csv
```

Use lowercase snake case. Include the source system and source entity in the filename, but do not repeat the source-system prefix when the entity name already begins with it. Do not append a layer suffix such as `_staging` or `_enriched`; the parent directory already identifies the direct source layer. Use the repository's actual entity naming where an established fixture path differs. Derive columns and types from the compiled source entity through `SchemaTranslate`. Include all columns required by the shared strict CSV loader, while keeping the number of rows small.

Design rows from the selected notebook's behavior, not merely its schema. Include matching and nonmatching keys for joins, meaningful mapped values, nulls, defaults, duplicates, or boundary values only when the transform handles them. Use synthetic values and never copy secrets, credentials, or unmasked production PII.

Load each CSV with the shared loader, cast it using the source entity schema, and wrap it in `PltDataFrame` when expected by the compiled transform.

## Implement Meaningful Assertions

Invoke a standard compiled transform once through a reusable fixture when test isolation permits:

```python
result = compiled_transform(
    source_a_df,
    source_b_df,
    run_unittest=True,
)
```

Pass every source positionally in compiled parameter order and always include `run_unittest=True`.

At minimum, assert the output column names and types against the compiled target entity schema. Add focused behavioral tests for the selected notebook's important transformations. Prefer assertions by stable synthetic keys over full-table row counts or unordered row positions.

Create one focused test per distinct behavior rather than combining unrelated filters, joins, mappings, deduplication, and aggregations into one broad test. Closely related assertions may remain together; do not create one test per output column. There is no fixed number of test functions: a simple transform may need only a schema test and one behavioral test, while a complex transform should have several.

Do not use `cache()` or `persist()` in generated unit tests. When scenarios share the same inputs and runtime conditions, invoke the transform once, collect its result once in a module-scoped fixture, and reuse those collected rows. Use separate transformed fixtures only when scenarios need incompatible inputs, mocks, or runtime conditions.

Mock only external or runtime behavior that is outside the unit under test. Ensure patches are restored after the test module and do not make a failing production branch pass by replacing the transformation logic itself.

For library-function mode, test the selected functions directly. Use the shared Spark fixture for Spark expressions and DataFrame functions; use ordinary pytest fixtures and mocks for Python clients and APIs. CSV fixtures are optional unless they materially improve the library test.

Do not disable a failing test by commenting it out. Do not add a skip merely to complete the request. Fix the test when the intended behavior is clear, or report the concrete production/framework blocker.

## Verify the Result

In Claude Code, do not run pytest, including collection-only commands. Do not create or modify `conftest.py`, `pytest.ini`, runtime stubs, test utilities, or Spark-session configuration to make tests run on a Databricks cluster. Compilation is allowed in Claude Code; pytest execution is deferred to local development or the PR unit-test pipeline. Follow `references/genie-code-workflow.md` and report that execution was deferred.

In a local environment, run the narrow target and require it to pass:

```text
python -m pytest <test-file> -v
```

Ensure `databricks/lib/integration-lib` is available on `PYTHONPATH` when the environment does not already provide it. If local Spark rejects `SparkSession.builder.master("local[1]")` because Databricks Connect is installed, report the environment mismatch; do not change the user's environment unless requested.

Do not run the complete unit suite by default when only the selected test or its private CSV fixtures changed. The PR pipeline provides the complete regression check.

In a local environment, run related tests when broadly reused production code changes. Run the complete unit suite locally only when shared test infrastructure, runtime stubs, test utilities, compiler behavior, pytest configuration, or widely reused library code changed, or when the user explicitly requests it:

```text
python -m pytest databricks/tests/unit -v
```

When pytest ran locally, report the target result separately from unrelated existing suite failures. In every environment, state the created test path, fixture paths, compiled module used, behaviors covered, mocks applied, and any remaining limitations.

State whether the repository or Shared artifact was inspected, whether repository compilation ran, and whether pytest actually executed locally. Do not describe source inspection, Shared reference inspection, compilation, or file generation as successful test execution.
