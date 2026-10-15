# Data Platform Framework Reference

This file is the authoritative reference for the platform framework API, layer architecture, and notebook file format. Skills read this before generating any entity or transform notebook.

---

## Data Platform Layer Architecture

Data flows through four layers. Each layer has its own notebook pattern.

```
External API / Source
        │
        ▼
  ┌──────────────────────────────────────────────┐
  │  Raw  (1-raw)                                │
  │  JSON files written to blob storage          │
  │  entity_locator: raw/cq/<sys>/int/<entity>   │
  └──────────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────────┐
  │  Staging  (3-staging)                        │
  │  All-STRING Delta table                      │
  │  entity_locator: staging/cq/<sys>/int/<ent>  │
  └──────────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────────┐
  │  Enriched  (4-enriched)                      │
  │  Typed, deduplicated Delta table             │
  │  entity_locator: enriched/cq/int/<sys>/<ent> │  ← sys moves AFTER int
  └──────────────────────────────────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────────┐
  │  Curated  (5-curated)                        │
  │  Typed+keyed Delta, business logic applied   │
  │  entity_locator: curated/cq/<module>/<ent>   │
  └──────────────────────────────────────────────┘
```

**Key locator rule:** enriched is the only layer that places `<sys>` after `int` in the locator path. All other layers place `<sys>` before `int`.

**`cq` is a placeholder product code.** All examples in this file use `cq` as the `<product>` segment. Replace it with your team's own product identifier (e.g. `myproduct`) throughout all entity locators and `Entity(product=...)` calls.

---

## Notebook File Format

All notebooks are `.py` source files for Git. Every notebook must start with:

```python
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# COMMAND ----------
# MAGIC %run "../../_platform_app/platform_init"
```

The `%run` depth depends on the layer:

| Layer | Notebook path | `%run` depth |
|---|---|---|
| Raw | `1-raw/<sys>/transform_...py` | `../../` |
| Staging | `3-staging/<sys>/transform_...py` | `../../` |
| Enriched | `4-enriched/<sys>/transform_...py` | `../../` |
| Curated | `5-curated/<module>/transform_...py` | `../../` |

---

## Platform Framework Python Package Reference

Skills generate notebooks that import from the `pltdata` package. This section documents the exact classes, enums, and constructor signatures a skill must use when building entity definitions and transforms.

---

### Imports

```python
# Schema / entity model
from pltdata.schema import (
    Layer, EntityType, AttrType, FieldType,
    Entity, EntityProperty, EntityVariant,
    Attribute, Parameter, RetentionDuration,
)
from pltdata.schema.module_name import ModuleName

# DRL — addressing entities on the lake
from pltdata.drl.drl import Drl
from pltdata.drl.lake_connect_factory import LakeConnectFactory
from pltdata.drl.lake_connect_base import PrimaryKeyCheck, PrimaryKeyCheckInSources, RunMode

# Transform hooks and context
from pltdata.transform.execution_context import ExecutionContext, PartitionValue
from pltdata.transform.lifecycle_handler import LifecycleHandler

# Staging-specific lifecycle handlers
from pltdata.staging.staging_lifecycle_handler import (
    StagingIngestionLifecycleHandler,
    EnrichedIngestionLifecycleHandler,
)

# Deployment
from pltdata.deployment.deploy_action import DeployMode, ForceMode
```

---

### Layer

Classifies which zone of the data lake an entity lives in. The physical container prefix follows from this enum.

| Member | Value | Physical prefix | Notes |
|---|---|---|---|
| `Layer.EXTERNAL` | `"external"` | `15-external` | |
| `Layer.RAW` | `"raw"` | `10-raw` | Blob JSON; no Delta |
| `Layer.STAGING` | `"staging"` | `20-staging` | All-STRING Delta |
| `Layer.ENRICHED` | `"enriched"` | `30-enriched` | Typed, deduped Delta |
| `Layer.CURATED` | `"curated"` | `40-curated` | Business-logic Delta |
| `Layer.WORKSPACE` | `"workspace"` | `60-workspace` | |

---

### AttrType

Physical data type for `Attribute.attr_type`. Every attribute must declare one.

| Member | Spark type |
|---|---|
| `AttrType.STRING` | StringType |
| `AttrType.LONG` | LongType |
| `AttrType.INT` | IntegerType |
| `AttrType.SHORT` | ShortType |
| `AttrType.FLOAT` | FloatType |
| `AttrType.DOUBLE` | DoubleType |
| `AttrType.TIMESTAMP` | TimestampType |
| `AttrType.DATE` | DateType |
| `AttrType.BIGINT` | LongType |
| `AttrType.DECIMAL` | DecimalType |
| `AttrType.BOOLEAN` | BooleanType |
| `AttrType.BINARY` | BinaryType |

**Staging rule:** every attribute in a staging entity must be `AttrType.STRING` except `UploadDate`, which is `AttrType.TIMESTAMP`.

---

### FieldType

Semantic role of an attribute. Two members drive framework behavior:

| Member | Effect |
|---|---|
| `FieldType.P_KEY` | Marks the attribute as a **partition key**. `Drl.get_partition_key()` and `ExecutionContext.is_target_partitioned()` use this. |
| `FieldType.PB_KEY` | Marks the **primary business key** portion. Used by `Drl.get_primary_part_of_business_key()`. |

Other common values: `ID`, `NAME`, `DSC`, `DATE`, `TMS`, `FLAG`, `AMT`, `QTY`, `CODE`, `KEY`, `HK`, `B_KEY`, `AUTO_ID`.

---

### EntityType

Storage format. Default is `EntityType.DELTA` (external Delta table).

| Member | Use when |
|---|---|
| `EntityType.DELTA` | Standard external Delta table (most entities) |
| `EntityType.DELTA_MANAGED` | Unity Catalog managed Delta table |
| `EntityType.PARQUET` | Parquet source |
| `EntityType.JSON` | JSON blob source |
| `EntityType.CSV` / `XLSX` / `XML` | File-format sources |
| `EntityType.SQL` | SQL Server entity |
| `EntityType.VOLUME` | Unity Catalog volume (external) |
| `EntityType.VOLUME_MANAGED` | Unity Catalog volume (managed) |

---

### EntityProperty

Per-entity configuration flags. Always present on `Entity`; commonly constructed with defaults.

```python
EntityProperty(
    auto_compute_hash=True,         # auto-generate HK column (default True)
    auto_compute_loadinfo=True,     # auto-generate LoadDate / UpdateDate (default True)
    physical_path=None,             # override derived ABFSS path (rarely used)
    disable_liquid_clustering=None, # set True to opt out of liquid clustering
    type_widening_enabled=None,
)
```

---

### Attribute

One column in an entity schema.

```python
Attribute(
    name="ColumnName",              # required — unique within the entity
    attr_type=AttrType.STRING,      # physical data type
    is_key=False,                   # True → business / primary key column
    field_type=FieldType.ID,        # semantic role (optional but recommended)
    source=["staging/cq/sys/int/entity.ColumnName"],  # DRL source path(s) for enriched/curated
    description=None,               # human-readable description
    display_name=None,              # UI label
    is_cluster_key=None,            # liquid clustering hint
    is_array=False,
    attr_len=None,                  # for DECIMAL: precision
    attr_precision=None,
    attr_scale=None,
)
```

**Source path format for enriched entities:**
```
"staging/cq/<sys>/int/<entity>.<ColumnName>"
```

**`is_key=True`** is required on every primary-key column for `MERGE_ON_PRIMARY_KEY` and dedup ROW_NUMBER logic to work correctly.

**`UploadDate` (staging only):** always the last attribute; never has a `source` path; always `AttrType.TIMESTAMP`.

---

### Entity

The core schema object. Every transform notebook constructs one.

```python
Entity(
    # --- Required ---
    entity_name="my_entity",                         # snake_case; enriched uses "<sys>_<entity>"
    layer=Layer.STAGING,
    product="cq",                                    # product code for your repository
    entity_property=EntityProperty(),

    # --- Locator (required unless purely config-driven) ---
    entity_locator="staging/cq/my_sys/int/my_entity",
    source_system="my_sys",                          # required for RAW / EXTERNAL / STAGING

    # --- Attributes ---
    attributes=[
        Attribute(name="Id",   attr_type=AttrType.STRING, is_key=True),
        Attribute(name="Name", attr_type=AttrType.STRING),
    ],

    # --- Optional metadata ---
    module_name=None,          # ModuleName enum or plain string
    display_name=None,
    description=None,
    version="1.0.0",           # always use "1.0.0" as the default; never a placeholder

    # --- Optional storage settings ---
    entity_type=EntityType.DELTA,
    retention_duration=RetentionDuration(dev=None, qua=None, prd=None),
    cdf_enabled=True,          # Change Data Feed — default True

    # --- Cross-entity ---
    is_public=False,
)
```

**Critical locator rules by layer:**

| Layer | `entity_locator` pattern | `source_system` position |
|---|---|---|
| Raw | `raw/cq/<sys>/int/<entity>` | before `int` |
| Staging | `staging/cq/<sys>/int/<entity>` | before `int` |
| Enriched | `enriched/cq/int/<sys>/<entity>` | **after `int`** |
| Curated | `curated/cq/<module>/<entity>` | not in locator |

---

### RetentionDuration

Per-environment data retention in days. Provide `None` to use platform default.

```python
RetentionDuration(dev=None, qua=None, prd=None)
```

Curated entities must always declare this field even when all values are `None`.

---

### Drl — Data Resource Locator

The primary object for addressing entities on the lake. Use the factory methods, never construct directly.

#### `Drl.from_config(...)` — look up entity from metadata DB

```python
src = Drl.from_config(
    entity_name="contact",
    layer=Layer.ENRICHED,
    product="cq",
    source_system="ace",           # required for RAW / EXTERNAL / STAGING
    module=None,                   # ModuleName enum or string; required if product alone is ambiguous
)
```

Use this when the entity is already deployed and registered. The framework loads the schema from the metadata database.

#### `Drl.from_object(entity)` — use an inline Entity

```python
tgt = Drl.from_object(entity)
```

Use this when the entity is defined in the current notebook (the common case for target entities).

#### Key `Drl` methods used in notebooks

| Method | Returns | Notes |
|---|---|---|
| `drl.get_entity()` | `Entity` | Loads / returns the resolved entity definition |
| `drl.get_external_location()` | `str` | ABFSS path on the lake |
| `drl.get_table_full_name(con)` | `str` | `` `catalog`.`schema`.`table` `` — fully qualified Spark table name |
| `drl.get_primary_key()` | `List[str]` | Column names where `is_key=True` |
| `drl.get_partition_key()` | `List[str]` | Column names where `field_type=FieldType.P_KEY` |
| `drl.get_business_columns()` | `List[str]` | Non-key, non-technical column names |
| `drl.get_df_from_table()` | `DataFrame` | Reads entity as a Spark DataFrame |

#### EntityExt — derived schema properties (via `drl.entity_ext`)

| Constant / property | Notes |
|---|---|
| `EntityExt.LOAD_DATE_COLUMN_NAME` | `"LoadDate"` — framework auto-generated column |
| `EntityExt.UPDATE_DATE_COLUMN_NAME` | `"UpdateDate"` — framework auto-generated column |
| `EntityExt.HASH_KEY_FOR_PK_COLUMN_NAME_SUFFIX` | `"HK"` — suffix on hash-key columns |
| `EntityExt.IS_DELETED_COLUMN_NAME` | `"IsDeleted"` |
| `drl.entity_ext.technical_column_names` | All framework-generated column names |
| `drl.entity_ext.business_column_names` | Non-technical, non-key columns |
| `drl.entity_ext.hash_key_for_pk_column_name` | HK column name for this entity |

---

### LakeConnectFactory

Singleton. Returns the active `LakeConnect` instance for the current Databricks environment.

```python
con = LakeConnectFactory().lake_connection
```

**Key properties on `con`:**

| Property | Type | Notes |
|---|---|---|
| `con.product_environment` | `str` | `"dev"`, `"qua"`, or `"prd"` — **never hard-code environment names; read this instead** |
| `con.spark` | `SparkSession` | The active Spark session |
| `con.db_utils` | `DBUtils` | Databricks `dbutils` |
| `con.catalog_name` | `str` | `"platform_<product>_<env>"` — Unity Catalog name |
| `con.batch_timestamp` | `datetime` | Workflow task value `job_start_timestamp`, or `utcnow()` |
| `con.version` | `str` | Current version string |
| `con.sql(query)` | `DataFrame` | Execute SQL; auto-substitutes catalog across environments |

---

### ExecutionContext

Injected into every transform function by the `PltDebugTransform` decorator. Provides incremental load metadata, partition info, and execution log management.

```python
def my_transform(execution_context: ExecutionContext, ...):
    ...
```

**Key methods:**

| Method | Notes |
|---|---|
| `execution_context.get_transformation_execution_last_started()` | `datetime` of last successful run — use for incremental load filters |
| `execution_context.is_target_partitioned()` | `True` if target has `FieldType.P_KEY` attributes |
| `execution_context.is_source_partitioned(drl)` | `True` if source has `FieldType.P_KEY` attributes |
| `execution_context.get_transformation_execution_modified_partitions_predicate(drl, since)` | SQL predicate for changed partitions since `since` |
| `execution_context.get_transformation_execution_modified_partitions(drl, since)` | `List[PartitionValue]` |
| `execution_context.print_summary_execution_context()` | Print load-type / version / source summary to stdout |
| `execution_context.lake_connection` | The active `LakeConnect` |
| `execution_context.target_drl` | The target entity's DRL |

---

### LifecycleHandler

Interface with hook points in the platform transform flow. Override only the hooks you need; all default to `pass`.

```python
class LifecycleHandler:
    def on_transform_start(self, execution_context: ExecutionContext) -> None: ...
    def on_transform_end_started(self, execution_context: ExecutionContext) -> None: ...
    def on_transform_execution_started(self, execution_context: ExecutionContext) -> None: ...
    def on_transform_entity_variant_started(self, execution_context: ExecutionContext, variant: str) -> None: ...
    def on_transform_entity_variant_finished(self, execution_context: ExecutionContext, variant: str) -> None: ...
    def on_target_persisted(self, execution_context: ExecutionContext) -> None: ...
    def on_transform_finished(self, execution_context: ExecutionContext) -> None: ...
    def on_exception(self, exception: Exception) -> None: ...
```

---

### StagingIngestionLifecycleHandler

Required in every staging transform. Manages the ingestion event log between raw blobs and the staging Delta table.

```python
StagingIngestionLifecycleHandler(
    source_dlr=raw_drl,       # Drl of the raw entity (source)
    target_dlr=staging_drl,   # Drl of the staging entity (target)
)
```

**Key members:**

| Member | Notes |
|---|---|
| `handler.files_to_process` | `List` of staged file entries (populated after `initialize_source_uploads`) |
| `handler.has_anything_to_process()` | `True` if there are files to ingest — guard the per-file loop with this |
| `handler.initialized` | `True` after `initialize_source_uploads` has been called |

The handler automatically calls `initialize_source_uploads` inside `on_transform_start`. Use `has_anything_to_process()` to guard the per-upload loop:

```python
if lifecycle_handler.has_anything_to_process():
    for uploaded_file in lifecycle_handler.files_to_process:
        df = read_dataframe(uploaded_file)
        if df is None:
            continue
        ...
```

---

### EnrichedIngestionLifecycleHandler

Required in every enriched transform. Manages enrichment event log entries from staged files to the enriched Delta table.

```python
EnrichedIngestionLifecycleHandler(
    source_dlrs=[staging_drl],   # List[Drl] of staging source entities
    target_dlr=enriched_drl,     # Drl of the enriched entity
    finish_enriched=True,        # emit finalized events on completion (usually True)
)
```

---

### PltDebugTransform pattern (in-notebook usage)

The `PltDebugTransform` wrapper wires entity construction, transform decoration, and deployment together in every notebook. The exact API comes from the `_platform_app/platform_init` run cell (the platform transform primitives entry point):

```python
# 1 — Define entity
entity = Entity(
    entity_name="ace_contact",
    layer=Layer.ENRICHED,
    product="cq",
    entity_locator="enriched/cq/int/ace/contact",
    entity_property=EntityProperty(),
    attributes=[
        Attribute(name="ContactId", attr_type=AttrType.STRING, is_key=True,
                  source=["staging/cq/ace/int/contact.ContactId"]),
        Attribute(name="FirstName", attr_type=AttrType.STRING,
                  source=["staging/cq/ace/int/contact.FirstName"]),
    ],
    version="1.0.0",
)

# 2 — Resolve DRLs for sources
source_staging = Drl.from_config("contact", Layer.STAGING, product="cq", source_system="ace")

# 3 — Lifecycle handler (enriched example)
lifecycle_handler = EnrichedIngestionLifecycleHandler(
    source_dlrs=[source_staging],
    target_dlr=Drl.from_object(entity),
    finish_enriched=True,
)

# 4 — PltDebugTransform wires entity + lifecycle + increment driver together
def my_transform(execution_context: ExecutionContext, source_ace_contact_staging: DataFrame) -> DataFrame:
    ...
    return df

PltDebugTransform(
    entity=entity,
    transform_func=my_transform,
    lifecycle_handler=lifecycle_handler,
    increment_driver_source_entity_name="NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME",
    target_persist=True,
).run()

# 5 — Deploy cell (separate notebook cell)
Deploy().deploy_entity(entity)
```

**`increment_driver_source_entity_name` rules:**

| Layer | Value |
|---|---|
| Raw | `None` (literal Python `None`) |
| Staging | `"NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME"` (sentinel string) |
| Enriched | `"NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME"` |
| Curated | `"NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME"` |

---

### DeployMode / ForceMode

Used in deploy cells and workflow automation.

**DeployMode:**

| Member | Int | Use |
|---|---|---|
| `DeployMode.NO_DEPLOYMENT` | 0 | Skip |
| `DeployMode.ONLY_CREATE` | 1 | Create if not exists |
| `DeployMode.MAJOR_CHANGE` | 2 | Breaking schema change |
| `DeployMode.MINOR_CHANGE` | 3 | Non-breaking change |
| `DeployMode.UPDATE_CONFIGS` | 6 | Table properties only |

**ForceMode:**

| Member | Value |
|---|---|
| `ForceMode.OFF` | `"no_enforcement"` |
| `ForceMode.FORCE_SCHEMA_UPDATE` | `"force_schema_update"` |
| `ForceMode.FORCE_OVERWRITE` | `"force_overwrite"` |

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| `attr.source == None` in PySpark context | Use `attr.source is None` |
| `version="<version>"` placeholder in template | Use `version="1.0.0"` (the actual default) |
| `increment_driver_source_entity_name=None` for staging/enriched/curated | Use the sentinel string `"NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME"` |
| `increment_driver_source_entity_name="NOT_DEFINED..."` for raw | Use literal `None` |
| Inferring entity_name from folder/file name | Always read the `Entity(...)` constructor |
| Hard-coding environment names (e.g. `"dev"`, `"prod"` as literals) | Use `LakeConnectFactory().lake_connection.product_environment` |
| enriched locator: `enriched/cq/<sys>/int/<entity>` | Correct: `enriched/cq/int/<sys>/<entity>` (sys after int) |
