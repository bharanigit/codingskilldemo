# Unit-Test Implementation Guide

Use these patterns as adaptable examples. Inspect the selected source notebook, entity definitions, and any nearby tests before choosing exact imports, fixture rows, or assertions.

## Path Mapping

Mirror a transform notebook beneath `databricks/tests/unit/`:

```text
databricks/3-staging/mockapi/transform_employees.py
databricks/tests/unit/3-staging/mockapi/test_transform_employees.py
```

Mirror an integration library module beneath the unit-test `lib` tree:

```text
databricks/lib/integration-lib/integration/functions/example_api.py
databricks/tests/unit/lib/integration-lib/integration/functions/test_example_api.py
```

Fixture CSV paths describe the **direct source** entities, not the target notebook:

```text
databricks/tests/data/raw/mockapi/mockapi_employees.csv
databricks/tests/data/staging/marketo/marketo_leads.csv
databricks/tests/data/staging/marketo/marketo_deleted_leads.csv
```

Name a new fixture `<source-system>_<source-entity>.csv` in lowercase snake case. If the entity name already starts with the source system, do not repeat that prefix. Keep the layer only in the directory path; do not add `_staging`, `_enriched`, or another layer suffix to the filename.

## Minimal conftest.py

When no shared test infrastructure exists, create a `conftest.py` alongside the test (or at the `databricks/tests/` root) that provides a local Spark session:

```python
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    return (
        SparkSession.builder
        .master("local[1]")
        .appName("unit-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
```

## Source-Notebook Pattern

Read the source notebook. Copy the `Entity(...)` constructors verbatim and replicate the PySpark transformation expressions as a standalone function. Do not import or execute the notebook itself.

```python
import pytest
from pyspark.sql import functions as F
from pltdata import (
    Attribute, AttrType, Entity, EntityProperty, EntityType,
    Layer, Parameter, RetentionDuration, SchemaTranslate,
)
from databricks.tests.test_utils.data_loader import load_csv
from databricks.tests.test_utils.schema_assertions import assert_column_types_equal


# --- Entity definitions (verbatim from source notebook) ---

mockapi_employees_raw = Entity(
    entity_name="employees",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="raw/cq/mockapi/int/employees",
    layer=Layer.RAW,
    product="cq",
    version="1.0.0",
    source_system="mockapi",
    is_public=False,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[
        Attribute(name="employee_id", attr_type=AttrType.STRING),
        Attribute(name="first_name",  attr_type=AttrType.STRING),
        # ... all attributes from notebook
    ],
)

mockapi_employees_staging = Entity(
    entity_name="employees",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="staging/cq/mockapi/int/employees",
    layer=Layer.STAGING,
    product="cq",
    version="1.0.0",
    source_system="mockapi",
    is_public=False,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[
        Attribute(name="employee_id", attr_type=AttrType.STRING),
        Attribute(name="first_name",  attr_type=AttrType.STRING),
        # ... all attributes from notebook
        Attribute(name="UploadDate",  attr_type=AttrType.TIMESTAMP),
    ],
)


# --- Standalone transformation (extracted from notebook loop) ---

def apply_staging_transform(source_df, upload_date_str="2024-01-01 00:00:00.0000000"):
    """Replicates the notebook's per-file staging transformation expressions."""
    staging_attrs = mockapi_employees_staging.attributes

    result = source_df.withColumn(
        "UploadDate",
        F.to_timestamp(F.lit(upload_date_str), "yyyy-MM-dd HH:mm:ss.SSSSSSS"),
    )
    for attr in staging_attrs:
        source_locator = (
            attr.name
            if attr.source is None or len(attr.source) == 0
            else attr.source[0]
        )
        source_name = source_locator.split("/")[-1]
        if source_name != attr.name and source_name in result.columns:
            result = result.withColumnRenamed(source_name, attr.name)

    keep = {a.name for a in staging_attrs}
    for col in result.columns:
        if col not in keep:
            result = result.drop(col)

    return result


# --- Fixtures ---

RAW_FIXTURE = "databricks/tests/data/raw/mockapi/mockapi_employees.csv"


@pytest.fixture(scope="module")
def source_df(spark):
    schema = SchemaTranslate(mockapi_employees_raw).get_spark_schema()
    return load_csv(spark, RAW_FIXTURE, schema)


@pytest.fixture(scope="module")
def transformed_df(source_df):
    return apply_staging_transform(source_df)


@pytest.fixture(scope="module")
def transformed_rows(transformed_df):
    return {row.employee_id: row for row in transformed_df.collect()}


# --- Tests ---

def test_schema_matches_target_entity(transformed_df):
    expected = SchemaTranslate(mockapi_employees_staging).get_spark_schema()
    assert_column_types_equal(transformed_df.schema, expected)


def test_all_source_columns_present(transformed_rows):
    row = transformed_rows["UNIT_001"]
    assert row.employee_id == "UNIT_001"
    assert row.first_name is not None


def test_upload_date_is_populated(transformed_rows):
    row = transformed_rows["UNIT_001"]
    assert row.UploadDate is not None


def test_columns_outside_staging_entity_are_dropped(transformed_df):
    staging_cols = {a.name for a in mockapi_employees_staging.attributes}
    for col in transformed_df.columns:
        assert col in staging_cols, f"Unexpected column in output: {col}"
```

When the notebook's transformation is entirely inline with no loop (e.g., a single `select(...)` or `withColumn(...)` chain), extract that chain directly as the function body. When a loop iterates over uploaded files, extract the per-iteration logic and pass a single synthetic DataFrame to the function.

## Multiple-Source Notebook Pattern

Create a schema-derived fixture and DataFrame for each direct input. Pass them positionally in the same order as the notebook reads them:

```python
@pytest.fixture(scope="module")
def primary_df(spark):
    schema = SchemaTranslate(primary_entity).get_spark_schema()
    return load_csv(spark, PRIMARY_FIXTURE, schema)


@pytest.fixture(scope="module")
def deleted_df(spark):
    schema = SchemaTranslate(deleted_entity).get_spark_schema()
    return load_csv(spark, DELETED_FIXTURE, schema)


@pytest.fixture(scope="module")
def transformed_df(primary_df, deleted_df):
    return apply_transform(primary_df, deleted_df)
```

Design related fixture rows together. For a left join, include at least one matching key and one primary-only key so both branches are observable. For precedence or coalescing logic, include rows that isolate each input and a row where both inputs are populated.

## Synthetic CSV Design

- Include every schema column in the header.
- Leave nullable, behaviorally irrelevant values empty.
- Provide valid neutral values for required columns.
- Use explicit stable identifiers such as `UNIT_001`.
- Keep fixtures small — two to five carefully selected rows are better than broad samples.
- Use valid ISO values for dates and timestamps.
- Avoid real names, email addresses, account identifiers, or other production data.

Choose rows after tracing the transform. A schema-valid CSV that does not exercise column renames, filters, or derived logic is insufficient.

## Runtime Dependency Mocking

Patch narrow collaborators at the module path. For a module-scoped transformed fixture, use a module-scoped `pytest.MonkeyPatch` and restore it:

```python
@pytest.fixture(scope="module", autouse=True)
def mock_environment():
    from types import SimpleNamespace
    import my_transform_module as m

    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        m,
        "LakeConnectFactory",
        lambda: SimpleNamespace(lake_connection=SimpleNamespace(product_environment="qua")),
    )
    yield
    patcher.undo()
```

Choose a realistic value for the behavior under test. This patch supplies deterministic metadata; it must not replace the Spark expressions or transformation branch itself.

Mock time, API clients, or filesystem adapters only when they are external to the transformation being tested. Do not mock the Spark expressions, joins, mappings, or filters that constitute the notebook's behavior.

## Direct Table Reads

A `spark.table(...)` inside the transformation is an undeclared input. Resolve its entity, create a synthetic CSV, and patch `spark` with an exact-name router:

```python
class _SparkRouter:
    def __init__(self, spark, tables):
        self._spark = spark
        self._tables = tables
        self.read = _ReadRouter(spark.read, tables)

    def table(self, name):
        if name not in self._tables:
            raise AssertionError(f"Unexpected table read: {name}")
        return self._tables[name]

    def __getattr__(self, name):
        return getattr(self._spark, name)


@pytest.fixture(scope="module", autouse=True)
def isolate_table_reads(spark, lookup_df):
    import my_transform_module as m
    patcher = pytest.MonkeyPatch()
    patcher.setattr(m, "spark", _SparkRouter(spark, {"catalog.schema.table": lookup_df}))
    yield
    patcher.undo()
```

Do not fall through to Unity Catalog. A new table dependency must cause the test to fail until a fixture is added.

## Library-Function Pattern

Library functions are imported directly — no `apply_transform` wrapper needed:

```python
from integration.functions.example import normalize_value
from pyspark.sql import Row, functions as F


def test_normalize_value_maps_known_value(spark):
    source = spark.createDataFrame([Row(raw_value="known")])
    actual = source.select(
        normalize_value(F.col("raw_value")).alias("normalized")
    ).first()
    assert actual.normalized == "expected"
```

## Assertion Selection

Every test should validate at minimum the target schema and at least one behavior specific to the selected notebook. Add assertions as applicable for:

- Output column names and types matching the target entity
- Column renames and aliases
- Derived values and expressions
- Join matches and unmatched rows
- Filters and retained rows
- Null and default handling
- Deduplication or precedence
- Columns outside the target entity being dropped

Create separate test functions for distinct behaviors. Keep closely related assertions together. Do not create one test per output column.

Avoid assertions based only on row counts, exact current timestamps, DataFrame collection order without sorting, or implementation details unrelated to observable behavior.
