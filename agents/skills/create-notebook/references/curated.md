# Curated Transform — Code Patterns and Reference Rules

## Notebook file format

First line must be exactly:

```
# Databricks notebook source
```

Immediately followed by the PEP 723 environment block:

```
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
```

The file header occupies the lines between `# Databricks notebook source` and the first `# COMMAND ----------`. Nothing in the file header creates a visible cell in the Databricks UI. Write it exactly as shown — no blank lines between elements, no `# DBTITLE`, no `# COMMAND ----------` inside it:

```
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC # Platform Development Framework

# COMMAND ----------

# MAGIC %run "../../_platform_app/platform_init"

# COMMAND ----------
```

Rules:
- No `environment_version` line in the PEP 723 block.
- The markdown preamble goes directly after `# ///` with no blank line and no `# COMMAND ----------` between them. It is NOT a cell — it is part of the file header.
- The first `# COMMAND ----------` comes after the last `# MAGIC` line of the preamble.
- `# MAGIC %run "../../_platform_app/platform_init"` is the first cell (after the first `# COMMAND ----------`).
- Markdown cells use `# MAGIC %md` with `# MAGIC ` prefix per line. Magic commands use `# MAGIC %run ...` (not bare `%run`). Cell titles use `# DBTITLE 1,<Title>` on the line before cell content. Cells are separated by `# COMMAND ----------`.

## Entity rules

The target entity must use:

```python
layer=Layer.CURATED
entity_type=EntityType.DELTA
entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True)
```

unless the user explicitly specifies another behavior.

Do NOT add a `source=` field to the curated `Entity(...)` constructor. Source bindings for curated entities belong in the `PltDebugTransform` declaration as `source_<name>_enriched=Drl.from_config(...)` keyword arguments, not on the entity itself.

Use `DataScope.A`, `DataScope.G`, `DataScope.E`, or `DataScope.UNKNOWN` deliberately.

Use `RetentionDuration(dev=None, qua=None, prd=None)` when the existing local pattern does so.

## Technical column rules

Platform Framework manages technical columns for persisted tables/files.

Common technical columns include:

- `<entity_name>HK` or framework-generated hash key
- target HK: `<table_name>_hk`
- relationship HK: `<related_table>_hk_<role>`
- `HashDiff`
- `LoadDate`
- `UpdateDate`
- `BatchTimestamp`

Do not manually create, select, or populate framework audit/change columns unless an existing local pattern explicitly requires it. HK columns may be part of the entity contract and are handled by the HK rules below.

In generated notebooks:

- entity `attributes` should describe business/data-contract columns
- final target alignment should use `[a.name for a in <target_entity>.attributes]`
- framework-generated technical columns should be left to `PltDataFrame`, `SatHelper`, and `end_transform`
- do not compare all business attributes manually for generic merge logic; the framework uses `HashDiff` for this

If a use case requires deletion semantics, model a deliberate business column such as `IsDeleted` and choose the merge type accordingly.

## Hash key column rules

Platform Framework automatically creates hash key columns.

### Target HK

Every table/entity has a target HK column named:

```text
<table_name>_hk
```

This HK is computed as an MD5 hash of the columns marked with:

```python
is_key=True
```

When generating a notebook:

- mark all business key attributes with `is_key=True`
- do not manually compute the target HK unless required by the existing pattern
- if the target HK is manually computed or selected, document why
- do not confuse the target HK with audit/change columns such as `HashDiff`, `LoadDate`, `UpdateDate`, or `BatchTimestamp`

### Relationship HK

Relationships automatically create columns named:

```text
<related_table>_hk_<role>
```

The relationship HK is computed from the related columns when `foreign_fields_mapping` is specified.

When generating relationships:

- define `Relationship(...)` with `foreign_fields_mapping=[FieldMapping(...)]` when a relationship HK is required
- use `role` when there are multiple relationships to the same related entity
- do not invent roles
- do not assume a relationship HK can be computed if `foreign_fields_mapping` is empty
- manually create relationship HK columns only when the mapping cannot express the required behavior or an existing local pattern does so

### Final column implications

HK columns may be part of the entity attributes and final target dataframe in hub/satellite patterns.

Audit/change columns are normally not part of the entity business attributes.

Before finishing, verify:

- business key columns are correctly marked with `is_key=True`
- target HK naming follows `<table_name>_hk`
- relationship HK naming follows `<related_table>_hk_<role>`
- relationship mappings contain the columns needed to compute the related HK

## Merge type rules

Choose `target_merge_type` deliberately.

### Preferred default: `TargetMergeType.MERGE_ON_PRIMARY_KEY`

Use for normal curated entities unless another behavior is clearly required.

This merge type:

- updates rows when PKs match and business data changed
- inserts rows when PKs are new
- does not hard-delete target rows that are missing from the source increment
- is consistent with incremental reads
- generally creates less Delta storage growth than full replacement

Use soft-delete columns for logical deletes.

### `TargetMergeType.FULL_REPLACE`

Use only when each run produces the complete target result.

Avoid when the transformation only processes increments.

This can cause high Delta storage growth because each run rewrites the full target.

### `TargetMergeType.PARTITIONS_REPLACE`

Use only when:

- the target is partitioned
- the target dataframe contains complete data for affected partitions
- source and target partitioning are the same or compatible
- replacing affected partitions is intended

Do not use unless the partition strategy is known.

### `TargetMergeType.MERGE_ON_PRIMARY_KEY_FLAG`

Use only when hard deletes are explicitly required.

Requires:

- target PK attributes
- source column `IsDeleted`
- agreement that `IsDeleted = 1` physically deletes matching target rows

Do not use for ordinary soft-delete behavior.

### `TargetMergeType.SNAPSHOT`

Avoid unless explicitly reviewed.

Use only when multiple processed versions must be retained and the storage impact is accepted.

## Merge decision checklist

Before generating a transform, decide:

1. Is the input a full result or an increment?
2. Should missing rows be retained, soft-deleted, or hard-deleted?
3. Are target primary keys defined?
4. Is the target partitioned?
5. Is partition replacement intended?
6. Does the source include `IsDeleted`?
7. Is storage growth acceptable for the selected merge type?

If unclear, use `MERGE_ON_PRIMARY_KEY` and leave TODOs for delete/partition behavior.

## Transform declaration

```python
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=<target_entity_variable>, enforce_schema=True),
    target_persist=True,
    target_merge_type=TargetMergeType.<MERGE_TYPE>,
    increment_driver_source_entity_name="NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME",
    source_<enriched_entity_name>_enriched=Drl.from_config(
        entity_name="<enriched_entity_name>",
        product="cq",
        module="int",
        layer=Layer.ENRICHED,
        source_system="<enriched_source_system>"
    )
)
```

- Do NOT add `type=`, `job_config=`, or any `JobType`, `JobConfig`, `DedicatedJob`, `ClusterType` parameters — these do not exist in `PltDebugTransform`. Do NOT write explicit imports of `PltDebugTransform` — it is already available from `platform_init`. Adding extra imports causes `ModuleNotFoundError` at runtime.
- Source keyword arg name is `source_<enriched_entity_name>_enriched` — uses the framework-registered `entity_name` from the enriched `Entity(...)` constructor (e.g. `source_ace_contact_enriched`), not the folder or file name.
- If the curated entity reads from multiple enriched sources, declare each with a separate `source_<name>_enriched=Drl.from_config(...)` kwarg.
- `Drl.from_config` uses `entity_name` and `source_system` exactly as they appear in the enriched notebook's `Entity(...)` constructor — always read the enriched notebook rather than inferring from the path.

Declare every source dataframe in `PltDebugTransform` using `Drl.from_config(...)` unless the local examples use `Drl.from_object(...)`.

## Transformation rules

- Use readable stepwise PySpark.
- SQL is allowed when it matches the existing notebook style or makes the business logic clearer.
- Use `environment = LakeConnectFactory().lake_connection.product_environment` for environment-specific table names.
- Do not hard-code environment-specific catalog names — always use `product_environment`.
- Avoid direct Delta writes.
- Avoid unbounded `display()` in production cells.
- Avoid `collect()` unless the result is intentionally small and the reason is clear.
- Explicitly alias aggregate output columns.
- Use `unionByName(..., allowMissingColumns=True)` when combining different-shaped inputs.
- Use `dropDuplicates(...)`, windowing, or grouping deliberately when key uniqueness requires it.
- Do not manually add framework technical columns to the final dataframe.
- Assume the target key defined by `is_key=True` attributes is unique by contract.
- Do not add defensive deduplication unless the business logic or source behavior requires it.

## Hub/satellite rules

If the entity extends a hub or has relationships that need hash keys, preserve the `SatHelper` pattern:

```python
from integration.functions.sat_helper import SatHelper

sat_helper = SatHelper(<target_entity_variable>, spark, logger)
sat_helper.create_relationship_cols()

target = PltDataFrame(target, Drl.from_object(entity=<target_entity_variable>, enforce_schema=True))
target_with_hk = sat_helper.compute_hash_keys(target)

sat_helper.insert_new_hub_entries(target_with_hk, lake_connection)
sat_helper.remove_relationship_cols()

target_with_hk = target_with_hk.select([a.name for a in <target_entity_variable>.attributes])

plt_transform.end_transform(target_with_hk)
```

Do not use `SatHelper` for a simple non-satellite transform unless the local pattern requires it.
