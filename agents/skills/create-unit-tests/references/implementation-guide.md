# CQ Unit-Test Patterns

Use these patterns as adaptable examples. Inspect the selected production code, compiled artifact, entities, and nearby tests before choosing exact imports, fixture rows, or assertions.

## Path Mapping

Mirror a transform notebook beneath `databricks/tests/unit/`:

```text
databricks/4-enriched/marketo/transform_marketo_leads.py
databricks/tests/unit/4-enriched/marketo/test_transform_marketo_leads.py
```

Mirror an integration library module beneath the unit-test `lib` tree:

```text
databricks/lib/integration-lib/integration/functions/example_api.py
databricks/tests/unit/lib/integration-lib/integration/functions/test_example_api.py
```

Fixture CSV paths describe the direct source entities, not the target notebook:

```text
databricks/tests/data/staging/marketo/marketo_leads.csv
databricks/tests/data/staging/marketo/marketo_deleted_leads.csv
databricks/tests/data/staging/amazon_retail/amazon_retail_traffic.csv
```

Name a new fixture `<source-system>_<source-entity>.csv` in lowercase snake case. If the entity name already starts with the source system, do not repeat that prefix. Keep the layer only in the directory path; do not add `_staging`, `_enriched`, or another layer suffix to a new filename. Preserve an established fixture filename when updating an existing test unless the request includes standardizing it.

## Compiled Module Resolution

Compiled transform modules live in `databricks/lib/integration-lib/integration/bin/`. Determine the exact generated name from the repository rather than inventing it. For example:

```text
Notebook: 4-enriched/marketo/transform_marketo_leads.py
Compiled: integration/bin/t_transform_marketo_leads_enriched_int.py
Function: t_transform_marketo_leads_enriched_int
```

The compiled decorator is the source of truth for source bindings and `export_type`. The compiled function signature is the source of truth for positional source order. Framework parameters such as `execution_context` and `lifecycle_handler` are supplied by the decorator when the standard transform is invoked with `run_unittest=True`.

Artifact discovery does not change generated imports. Even when Claude Code inspects a read-only Shared release artifact, the test must use the portable `integration.bin...` import expected by local development and the PR pipeline. When no current artifact exists, run the repository compiler; the resulting repository artifact becomes authoritative for implementation and verification. See `genie-code-workflow.md` for workspace discovery and freshness rules.

## Single-Source Notebook Pattern

```python
import pytest

from pltdata import PltDataFrame
from pltdata.drl.schema_translate import SchemaTranslate

from databricks.tests.test_utils.data_loader import load_csv
from databricks.tests.test_utils.schema_assertions import (
    assert_column_types_equal,
)
from integration.bin.t_transform_example_curated_int import (
    example_curated,
    t_transform_example_curated_int,
)
from integration.bin.t_transform_example_enriched_int import example_enriched


FIXTURE_PATH = "enriched/example/example_enriched.csv"


@pytest.fixture(scope="module")
def source_df(spark):
    source_schema = SchemaTranslate(example_enriched).get_spark_schema()
    return PltDataFrame(load_csv(spark, FIXTURE_PATH, source_schema))


@pytest.fixture(scope="module")
def transformed_df(source_df):
    return t_transform_example_curated_int(
        source_df,
        run_unittest=True,
    )


@pytest.fixture(scope="module")
def transformed_rows(transformed_df):
    return {row.entity_key: row for row in transformed_df.collect()}


def test_schema_matches_target_entity(transformed_df):
    expected_schema = SchemaTranslate(example_curated).get_spark_schema()
    assert_column_types_equal(transformed_df.schema, expected_schema)


def test_filters_out_ineligible_records(transformed_rows):
    assert "UNIT_FILTERED" not in transformed_rows


def test_maps_target_values(transformed_rows):
    row = transformed_rows["UNIT_001"]
    assert row.mapped_value == "expected"


def test_keeps_latest_business_key_record(transformed_rows):
    row = transformed_rows["UNIT_001"]
    assert row.source_version == 2
```

Use the real compiled entity variable names. A direct PySpark `DataFrame` may work for some transforms, but prefer `PltDataFrame` when the compiled signature and production code expect it.

## Multiple-Source Notebook Pattern

Create a schema-derived fixture and `PltDataFrame` for each direct input. Pass them in compiled function parameter order:

```python
@pytest.fixture(scope="module")
def primary_df(spark):
    schema = SchemaTranslate(primary_staging).get_spark_schema()
    return PltDataFrame(load_csv(spark, PRIMARY_PATH, schema))


@pytest.fixture(scope="module")
def deleted_df(spark):
    schema = SchemaTranslate(deleted_staging).get_spark_schema()
    return PltDataFrame(load_csv(spark, DELETED_PATH, schema))


@pytest.fixture(scope="module")
def transformed_df(primary_df, deleted_df):
    return t_transform_example_enriched_int(
        primary_df,
        deleted_df,
        run_unittest=True,
    )
```

Design related fixture rows together. For a left join, include at least one matching key and one primary-only key so both branches are observable. For precedence or coalescing logic, include rows that isolate each input and a row where both inputs are populated.

## Synthetic CSV Design

The shared `load_csv` helper validates that every source schema column is present, reorders columns to match the entity, and casts each column to its Spark type. Therefore:

- Include every schema column in the header.
- Leave nullable, behaviorally irrelevant values empty.
- Provide valid neutral values for required columns.
- Use explicit stable identifiers such as `UNIT_001`.
- Keep fixtures small; usually two to five carefully selected rows are better than broad samples.
- Preserve meaningful nulls rather than replacing every missing value with an empty string when the cast behavior matters.
- Use valid ISO values for dates and timestamps.
- Avoid real names, email addresses, account identifiers, access tokens, or other production data.

Choose rows after tracing the transform. A schema-valid CSV that does not exercise joins, mappings, filters, or defaults is insufficient.

## Runtime Dependency Mocking

Patch narrow collaborators at the module path used by the compiled transform. For a module-scoped transformed fixture, use a module-scoped `pytest.MonkeyPatch` and restore it:

```python
@pytest.fixture(scope="module", autouse=True)
def mock_historical_state():
    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        historical_job_run_log.HistoricalJobRunLog,
        "has_already_run",
        staticmethod(lambda *args, **kwargs: True),
    )
    yield
    patcher.undo()
```

A connection stub does not necessarily provide meaningful runtime metadata. For example, a stubbed `LakeConnectFactory` can prevent Databricks access but return `None` for `product_environment`. If the transform uses that value to choose business logic, supply the intended branch value at the compiled module path rather than relying on the stub's fallback:

```python
from types import SimpleNamespace

import integration.bin.t_transform_example_serving_int as compiled_module


@pytest.fixture(scope="module", autouse=True)
def non_development_environment():
    patcher = pytest.MonkeyPatch()
    lake_connection = SimpleNamespace(product_environment="qua")
    patcher.setattr(
        compiled_module,
        "LakeConnectFactory",
        lambda: SimpleNamespace(lake_connection=lake_connection),
    )
    yield
    patcher.undo()
```

Choose a realistic value for the behavior under test, such as `dev`, `qua`, or `prd`. This patch supplies deterministic metadata; it must not replace the Spark expressions or transformation branch itself. Keep the override local to the selected test unless the user explicitly requests a shared test-infrastructure default.

Mock time, historical-run state, secrets, API clients, or filesystem adapters only when they are external to the transformation being tested. Do not mock the Spark expressions, joins, mappings, or filters that constitute the selected notebook's behavior.

If the function body performs direct writes or external calls that cannot be fully isolated, do not execute it. `run_unittest=True` only bypasses the standard framework decorator's read and persistence stages.

## Direct Unity Catalog Table Reads

A `spark.table(...)` or `spark.read.table(...)` call inside the compiled function is an undeclared direct input. `run_unittest=True` does not replace it. Resolve its entity and create a synthetic CSV exactly as for a decorator source.

Use this resolution order:

1. A compiled entity in the current repository.
2. The entity definition in an upstream repository notebook.
3. In Claude Code, a compiled entity in the read-only Shared release.
4. Unity Catalog schema metadata only, without selecting table rows.

If none provides an unambiguous schema, ask for the schema or a synthetic fixture instead of reading production data or inventing columns.

Patch the `spark` object used by the compiled module with an exact-name router. Return ordinary PySpark DataFrames because production code commonly wraps the result in `PltDataFrame` itself:

```python
from types import SimpleNamespace

import pytest

import integration.bin.t_transform_example_curated_int as compiled_module


DIRECT_TABLE = "platform_qua.self_int_enriched.example_source"
DIRECT_FIXTURE = "enriched/example/example_source.csv"


class _TableRouter:
    def __init__(self, delegate, tables):
        self._delegate = delegate
        self._tables = tables

    def table(self, name):
        if name not in self._tables:
            raise AssertionError(f"Unexpected table read: {name}")
        return self._tables[name]

    def __getattr__(self, name):
        return getattr(self._delegate, name)


class _SparkRouter(_TableRouter):
    def __init__(self, spark, tables):
        super().__init__(spark, tables)
        self.read = _TableRouter(spark.read, tables)


@pytest.fixture(scope="module")
def direct_source_df(spark):
    schema = SchemaTranslate(example_source_enriched).get_spark_schema()
    return PltDataFrame(load_csv(spark, DIRECT_FIXTURE, schema))


@pytest.fixture(scope="module", autouse=True)
def isolate_direct_table_reads(spark, direct_source_df):
    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        compiled_module,
        "spark",
        _SparkRouter(
            spark,
            {DIRECT_TABLE: direct_source_df.toPyspark()},
        ),
    )
    lake_connection = SimpleNamespace(product_environment="qua")
    patcher.setattr(
        compiled_module,
        "LakeConnectFactory",
        lambda: SimpleNamespace(lake_connection=lake_connection),
    )
    yield
    patcher.undo()
```

Adapt the deterministic environment value and exact table name together so the production f-string resolves to the registered key. Do not implement a fallback to `spark.table`; a new table dependency should fail the test until a fixture is added.

Direct writes require a separate narrow patch. For example, a satellite transform may legitimately test its DataFrame and hash-key logic while preventing the external Hub persistence boundary:

```python
import integration.functions.sat_helper as sat_helper_module


@pytest.fixture(scope="module", autouse=True)
def prevent_hub_persistence():
    patcher = pytest.MonkeyPatch()
    calls = []

    def record_insert(self, target, lake_connection):
        calls.append(target)

    patcher.setattr(
        sat_helper_module.SatHelper,
        "insert_new_hub_entries",
        record_insert,
    )
    yield calls
    patcher.undo()
```

Mock only the persistence operation. Keep mappings, joins, deduplication, hash computation, and other transformation behavior real. If earlier helper methods also require live entity metadata, resolve and patch that metadata narrowly; stop when doing so would replace the behavior being tested.

## Library-Function Pattern

Library functions are imported directly and do not use `run_unittest=True`:

```python
from pyspark.sql import Row
from pyspark.sql import functions as F

from integration.functions.example import normalize_value


def test_normalize_value_maps_known_value(spark):
    source = spark.createDataFrame([Row(raw_value="known")])
    actual = source.select(
        normalize_value(F.col("raw_value")).alias("normalized")
    ).first()

    assert actual.normalized == "expected"
```

For API clients and ordinary Python helpers, use small direct values and mock sessions, credentials, clocks, and responses. Assert returned values and meaningful collaborator calls without making network requests.

## Assertion Selection

Every compiled notebook test should validate the target schema and at least one behavior specific to the selected transform. Add assertions as applicable for:

- Field aliases and derived values
- Join matches and unmatched rows
- Filters and retained rows
- Null and default handling
- Deduplication or precedence
- Primary-key presence and uniqueness when the transform guarantees them
- Nested structures, arrays, and identity maps

Create separate test functions for distinct behaviors so a failure identifies the broken rule. Keep closely related assertions together, such as all fields produced by one mapping or all measures from one aggregation. Do not force a fixed test count and do not create a separate test for every column.

Do not use `cache()` or `persist()` in generated unit tests. When multiple behavioral tests use the same output, invoke the transform once, collect its result once in a module-scoped fixture, and reuse those collected rows. Use separate transform executions only when a scenario requires different input rows, mocks, or runtime state.

Avoid assertions based only on row counts, exact current timestamps, DataFrame collection order without sorting, or implementation details unrelated to observable behavior.

## Verification

The pytest commands in this section are for local development and CI only. Do not run them from Claude Code. In Claude Code, do not create or modify `conftest.py`, `pytest.ini`, runtime stubs, test utilities, or Spark-session settings to make pytest run against the active Databricks cluster; defer execution to local development or the PR unit-test pipeline.

Locally, run from the repository root with the integration library on `PYTHONPATH` when needed.

PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\databricks\lib\integration-lib;$env:PYTHONPATH"
python -m pytest <test-file> -v
```

Do not run the complete unit suite by default when only the selected test or its private CSV fixtures changed. The PR pipeline provides the complete regression check.

Run related tests when broadly reused production code changes. Run the complete unit suite only when shared test infrastructure, runtime stubs, test utilities, compiler behavior, pytest configuration, or widely reused library code changed, or when the user explicitly requests it:

```powershell
python -m pytest databricks/tests/unit -v
```

Distinguish failures in the new target from unrelated failures in existing tests.
