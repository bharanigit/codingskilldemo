# Enriched Transform — Code Patterns and Templates

## Notebook file format

The file header occupies the lines between `# Databricks notebook source` and the first `# COMMAND ----------`. Nothing in the file header creates a visible cell in the Databricks UI. Write it exactly as shown — no blank lines between elements, no `# DBTITLE`, no `# COMMAND ----------` inside it:

```
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC Enriched job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               ENRICHED
# MAGIC * Entity:              <enriched_entity_name>
# MAGIC ### Notebook information
# MAGIC
# MAGIC Uses Platform Development Framework

# COMMAND ----------

# MAGIC %run "../../_platform_app/platform_init"

# COMMAND ----------
```

Rules:
- No `environment_version` line in the PEP 723 block.
- The wizard markdown preamble goes directly after `# ///` with no blank line and no `# COMMAND ----------` between them. It is NOT a cell — it is part of the file header.
- The first `# COMMAND ----------` comes after the last `# MAGIC` line of the preamble.
- `# MAGIC %run "../../_platform_app/platform_init"` is the first cell (after the first `# COMMAND ----------`).
- Markdown cells use `# MAGIC %md` with `# MAGIC ` prefix per line. Magic commands use `# MAGIC %run ...` (not bare `%run`). Cell titles use `# DBTITLE 1,<Title>` on the line before cell content. Cells are separated by `# COMMAND ----------`.

## Wizard markdown preamble

```
# MAGIC %md
# MAGIC Enriched job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               ENRICHED
# MAGIC * Entity:              <enriched_entity_name>
# MAGIC ### Notebook information
# MAGIC
# MAGIC Load staged data into enriched object
```

Where `<enriched_entity_name>` is the `entity_name` parameter value (e.g., `marketo_leads`).

## Entity definition

### Naming conventions

- **Variable name**: `<short_entity_name>_enriched` (e.g., `campaigns_enriched`, `marketo_leads_enriched`)
- **`entity_name` parameter**: `<source_system>_<entity_name>` (e.g., `"meta_campaigns"`, `"marketo_leads"`) — this is how the Unity Catalog table will be named
- **`entity_locator`**: `"enriched/cq/int/<source_system>/<entity_name>"` — source system comes **after** `int`, unlike staging/raw

### Entity constructor

```python
<var>_enriched = Entity(
    entity_name="<source_system>_<entity_name>",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="enriched/cq/int/<source_system>/<entity_name>",
    source=["staging/cq/<source_system>/int/<staging_entity_name>"],
    layer=Layer.ENRICHED,
    product="cq",
    version="<version>",
    source_system="<source_system>",
    is_public=False,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[
        Attribute(
            name="<enriched_col_name>",
            attr_type=AttrType.<TYPE>,
            source=["staging/cq/<source_system>/int/<staging_entity_name>/<staging_col_name>"],
            is_key=True  # only on primary key columns
        ),
        Attribute(
            name="<enriched_col_name>",
            attr_type=AttrType.<TYPE>,
            source=["staging/cq/<source_system>/int/<staging_entity_name>/<staging_col_name>"],
        ),
        # ...
    ],
    retention_duration=RetentionDuration(dev=None, qua=None, prd=None),
)
```

### Attribute rules

- Use **correctly typed** attributes — not all STRING. Use `AttrType.INT`, `AttrType.BIGINT`, `AttrType.DOUBLE`, `AttrType.BOOLEAN`, `AttrType.TIMESTAMP`, `AttrType.DATE`, `AttrType.STRING`.
- Mark primary key columns with `is_key=True`.
- Every attribute must have `source=[...]` pointing to its staging DRL path.
- Use **snake_case** enriched attribute names (e.g., `lead_id`, `campaign_name`, `created_at`).
- Staging source names may be camelCase (e.g., `staging/.../createdAt`) — keep them exactly as they appear in the staging entity.
- `retention_duration=RetentionDuration(dev=None, qua=None, prd=None)` is always required.
- Do not add `data_scope`, `variants`, `views`, `zorder_columns`, `relationships`, or `field_type` unless the local pattern requires them.

## Deploy cell

```python
Deploy().deploy_entity(<var>_enriched)
```

## PltDebugTransform

```python
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=<var>_enriched, enforce_schema=True),
    target_persist=True,
    target_merge_type=TargetMergeType.MERGE_ON_PRIMARY_KEY,
    lifecycle_handler=EnrichedIngestionLifecycleHandler(
        ["staging/cq/<source_system>/int/<staging_entity_name>"],
        <var>_enriched.entity_locator,
        True
    ),
    increment_driver_source_entity_name="NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME",
    source_<staging_entity_name>_staging=Drl.from_config(
        entity_name="<staging_entity_name>",
        product="cq",
        module="int",
        layer=Layer.STAGING,
        source_system="<source_system>"
    )
)
```

- Always `target_persist=True` and `target_merge_type=TargetMergeType.MERGE_ON_PRIMARY_KEY`.
- Always `enforce_schema=True`.
- Always `increment_driver_source_entity_name="NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME"` (sentinel string, not `None`).
- `EnrichedIngestionLifecycleHandler` first arg is a **list** of staging locator strings (one per source staging entity).
- Third arg to `EnrichedIngestionLifecycleHandler` is always `True`.
- Declare each staging source as `source_<staging_entity_name>_staging=Drl.from_config(...)`.
- If multiple staging sources are used (e.g., main + deleted), declare all of them.

## Data transformation

Precede with a markdown cell:

```
# MAGIC %md
# MAGIC # Data transformation
```

### Standard transformation pattern

```python
from pyspark.sql.functions import col
from pyspark.sql.types import LongType, StringType, IntegerType, DoubleType, BooleanType

transformed_plt = source_<entity>_staging.select(
    col("<staging_col>").cast(<Type>()).alias("<enriched_col>"),
    col("<staging_col>").cast(<Type>()).alias("<enriched_col>"),
    # ... one entry per enriched attribute ...
)
```

### Transformation rules

- Cast every column to its enriched type: `.cast(LongType())`, `.cast(StringType())`, `.cast("boolean")`, etc.
- Alias every column to the enriched attribute name using `.alias("<enriched_col>")`.
- Enriched names are snake_case; staging names may be camelCase.
- Use `LakeConnectFactory().lake_connection.product_environment` for environment-aware table lookups — never hard-code environment-specific catalog names.
- Complex derivations allowed: `when/otherwise`, `regexp_extract`, `split`, `initcap`, `lower`, `trim`, `expr(...)`, window functions.
- If joining multiple sources (e.g., main staging + deleted staging):
  ```python
  combined_df = src_<main>_stg.alias("m").join(
      src_<deleted>_stg.alias("d"),
      col("m.<key>") == col("d.<key>"),
      "left"
  )._df
  ```
- Do not add `UploadDate` to the enriched target — the enriched entity should not carry staging lineage timestamps.

### Null normalization

Always add after transformation:

```python
from pyspark.sql.functions import col, when

for column in transformed_plt.columns:
    transformed_plt = transformed_plt.withColumn(
        column,
        when((col(column) == "nan") | (col(column) == "null"), None).otherwise(col(column))
    )
```

### ROW_NUMBER deduplication by business key

Always add after null normalization:

```python
from pyspark.sql.functions import expr

bkList = [a for a in <var>_enriched.attributes if a.is_key]
if len(bkList) > 0:
    target = transformed_plt.withColumn(
        "rn",
        expr(f"ROW_NUMBER() OVER (PARTITION BY ({','.join([bk.name for bk in bkList])}) ORDER BY <sort_col> DESC)")
    )
    target = target.where("rn=1").drop("rn")
```

- `<sort_col>` is typically a date/timestamp column such as `updated_at` or `UploadDate`.
- The join separator is `','` — a plain comma string with no backslashes. Never write `'\',\''` or any variant with backslash characters inside the f-string `{}` expression: Python raises `SyntaxError: unexpected character after line continuation character` at runtime.
- The partition expression must use the actual enriched PK column names.
- After deduplication, assign result to `target`.
- `UploadDate` should not appear in the final `target` if not declared as an enriched attribute.

## End transform

```python
plt_transform.end_transform(target)
```

Pass the `target` DataFrame after deduplication and null normalization.

## HistoricalJobRunLog (advanced pattern)

Only use this pattern if the local examples for the same source system use it. Do not add it by default.

```python
from integration.functions.historical_job_run_log import HistoricalJobRunLog

environment = LakeConnectFactory().lake_connection.product_environment
entity_table_name = <var>_enriched.entity_name  # e.g., "marketo_leads"

if HistoricalJobRunLog.has_already_run(environment, <var>_enriched.entity_name):
    # daily incremental path
    combined_df = src_<main>_stg.alias("m").join(...)._df
    has_already_run = True
else:
    # historical backfill path from landing table
    historical_df = spark.table(f"platform_{environment}.self_hdf_landing.{entity_table_name}")
    # ... dedup and combine historical + daily ...
    has_already_run = False
```
