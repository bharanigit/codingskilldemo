# Staging Transform — Code Patterns and Templates

## Notebook file format

The file header occupies the lines between `# Databricks notebook source` and the first `# COMMAND ----------`. Nothing in the file header creates a visible cell in the Databricks UI. Write it exactly as shown — no blank lines between elements, no `# DBTITLE`, no `# COMMAND ----------` inside it:

```
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC Staging job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               STAGING
# MAGIC * Entity:              <entity_name>
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
# MAGIC Staging job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               STAGING
# MAGIC * Entity:              <entity_name>
# MAGIC ### Notebook information
# MAGIC
# MAGIC Uses Platform Development Framework
```

Where `<entity_name>` is the `entity_name` parameter value (e.g., `campaigns`, `leads`).

## Entity definition

### Variable naming

Use `<source_system>_<entity_name>_staging` (e.g., `meta_campaigns_staging`, `marketo_leads_staging`).

### Entity constructor

```python
<var> = Entity(
    entity_name="<entity_name>",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="staging/cq/<source_system>/int/<entity_name>",
    source=["raw/cq/<source_system>/int/<entity_name>"],
    layer=Layer.STAGING,
    product="cq",
    version="1.0.0",
    source_system="<source_system>",
    is_public=False,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[
        Attribute(
            name="<column_name>",
            attr_type=AttrType.STRING,
            source=["raw/cq/<source_system>/int/<entity_name>/<column_name>"],
        ),
        # ... all source columns ...
        Attribute(name="UploadDate", attr_type=AttrType.TIMESTAMP),
    ],
)
```

### Attribute rules

- Every attribute except `UploadDate` must use `AttrType.STRING` — staging schema-widens all types.
- Every attribute except `UploadDate` must have `source=["raw/cq/<source_system>/int/<entity_name>/<raw_column_name>"]`.
- `UploadDate` is always the **last** attribute; use `AttrType.TIMESTAMP` with no `source` or `source=[]`.
- Do not add `is_key`, `field_type`, `data_scope`, `variants`, `views`, `zorder_columns`, `relationships`, or `retention_duration`.
- Do not include framework technical columns (`HashDiff`, `LoadDate`, etc.) as attributes.

## Deploy cell

```python
Deploy().deploy_entity(<entity_var>)
```

## PltDebugTransform

```python
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    target=Drl.from_object(entity=<entity_var>, enforce_schema=True),
    target_persist=True,
    target_merge_type=TargetMergeType.FULL_REPLACE,
    lifecycle_handler=StagingIngestionLifecycleHandler(
        "raw/cq/<source_system>/int/<entity_name>",
        <entity_var>.entity_locator
    ),
    increment_driver_source_entity_name="NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME",
    source_<entity_name>_raw=Drl.from_config(
        entity_name="<entity_name>",
        product="cq",
        module="int",
        layer=Layer.RAW,
        source_system="<source_system>"
    )
)
```

- Always `target_persist=True` and `target_merge_type=TargetMergeType.FULL_REPLACE`.
- Always `enforce_schema=True` on target.
- Always `increment_driver_source_entity_name="NOT_DEFINED_DRIVER_SOURCE_ENTITY_NAME"` (sentinel string, not `None`).
- The `lifecycle_handler` first arg is the raw entity locator path; second is the staging entity locator property.
- Declare the raw source entity as `source_<entity_name>_raw`.
- Do not add a `version=` argument to `PltDebugTransform`.

## Logger and lifecycle handler resolution

```python
logger = PltLogger("<entity_name>")

try:
    # Running in compiled transformations
    staging_lifecycle_handler = lifecycle_handler
except NameError:
    # Development mode in notebook
    staging_lifecycle_handler = plt_transform._lifecycle_handler

all_uploads = staging_lifecycle_handler.files_to_process
logger.info("All folders to process: %s", "\n".join([str(f) for f in all_uploads]))
```

The `try/except NameError` block is mandatory — it handles both compiled and interactive modes.

## Per-file processing loop

```python
# DBTITLE 1,Data transformation
target = None
for uploaded_file in all_uploads:
    <entity_name>_staging_source = Entity(
        entity_name="<entity_name>",
        entity_type=EntityType.DELTA,
        module_name="int",
        entity_locator="raw/cq/<source_system>/int/<entity_name>",
        layer=Layer.RAW,
        product="cq",
        version="1.0.0",
        source_system="<source_system>",
        is_public=False,
        entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
        attributes=[],
    )

    if read_dataframe(uploaded_file) is None:
        continue

    source_hdf = PltDataFrame(
        read_dataframe(uploaded_file),
        Drl.from_object(<entity_name>_staging_source, enforce_schema=False),
    )

    transform_hdf = source_hdf
    transform_hdf = transform_hdf.withColumn(
        "UploadDate",
        to_timestamp(lit(uploaded_file.UploadDate), "yyyy-MM-dd HH:mm:ss.SSSSSSS"),
    )
    for attr in <entity_var>.attributes:
        source_locator = (
            attr.name
            if attr.source is None or len(attr.source) == 0
            else attr.source[0]
        )
        source_split = source_locator.split("/")
        source_name = source_split[len(source_split) - 1]
        if source_name == attr.name and source_name in transform_hdf.columns:
            continue
        else:
            if source_name in transform_hdf.columns:
                transform_hdf = transform_hdf.withColumnRenamed(source_name, attr.name)
            elif source_name not in transform_hdf.columns:
                field = SchemaTranslate.get_spark_type(attr)
                transform_hdf = transform_hdf.withColumn(
                    attr.name, f.lit(None).cast(field.dataType)
                )

    for col in transform_hdf.columns:
        if len([a for a in <entity_var>.attributes if a.name == col]) == 0:
            transform_hdf = transform_hdf.drop(col)

    if target:
        target = target.unionByName(transform_hdf, allowMissingColumns=True)
    else:
        target = transform_hdf
```

### Loop rules

- The inner `Entity` is a throwaway raw source descriptor: `layer=Layer.RAW`, `attributes=[]`, same `entity_locator` as the raw path.
- `read_dataframe(uploaded_file) is None` guards against empty raw files — this check is mandatory.
- `enforce_schema=False` on the inner raw `Drl.from_object` — raw files are schema-flexible.
- The column-rename loop is driven mechanically by `attr.source[0]` path splitting — do not add business logic here.
- The column-drop loop removes any raw column not declared in the staging entity — do not omit it.
- Use `unionByName(..., allowMissingColumns=True)` — raw files across batches may have missing fields.
- Do not add type casting, filtering, or business transformations inside the staging loop; those belong in the enriched layer.

## End transform

```python
plt_transform.end_transform(target)
```

Pass the accumulated `target` DataFrame (may be `None` if all uploads were empty — the framework handles this).
