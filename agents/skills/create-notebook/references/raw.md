# Raw Ingest — Code Patterns and Templates

See `references/examples/transform_raw_example.py` for a complete working example.

## Notebook file format

The file header occupies the lines between `# Databricks notebook source` and the first `# COMMAND ----------`. Nothing in the file header creates a visible cell in the Databricks UI. Write it exactly as shown — no blank lines between elements, no `# DBTITLE`, no `# COMMAND ----------` inside it:

```
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %run "../../_platform_app/platform_init"

# COMMAND ----------
```

Rules:
- No `environment_version` line in the PEP 723 block.
- `# MAGIC %run` goes directly after `# ///` with no blank line and no `# COMMAND ----------` between them. It is NOT a cell — it is part of the file header.
- The first `# COMMAND ----------` comes after `# MAGIC %run`.
- Raw notebooks have no wizard markdown preamble. The first cell after `# COMMAND ----------` is the Entity Definition.
- Cell titles use `# DBTITLE 1,<Title>` on the line before cell content. Cells are separated by `# COMMAND ----------`.

## Entity definition

### Variable naming

Use `<source_system>_<entity_name>_raw` (e.g., `meta_campaigns_raw`, `marketo_leads_raw`).

### Entity constructor

```python
# DBTITLE 1,Entity Definition
<var> = Entity(
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
    attributes=[
        Attribute(name="<column>", attr_type=AttrType.<TYPE>),
        # ...
    ],
)
```

### Attribute rules

- Use the **actual source API types** — do not widen to `AttrType.STRING` unless the API truly returns strings.
- Common types: `AttrType.STRING`, `AttrType.INT`, `AttrType.BIGINT`, `AttrType.DOUBLE`, `AttrType.BOOLEAN`, `AttrType.TIMESTAMP`, `AttrType.DATE`.
- Do not add `source`, `is_key`, `field_type`, `data_scope`, `variants`, `views`, `zorder_columns`, `relationships`, or `retention_duration`.
- Do not include `UploadDate` — that is added by the staging layer.
- Do not include framework technical columns.

### Entity locator format

```
raw/cq/<source_system>/int/<entity_name>
```

No `source=` field on the raw entity — raw is the origin layer.

## Deploy cell

```python
Deploy().deploy_entity(<entity_var>)
```

## PltDebugTransform

```python
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=<entity_var>, enforce_schema=False),
    target_persist=False,
    target_merge_type=TargetMergeType.FULL_REPLACE,
    increment_driver_source_entity_name=None
)
```

- Always `target_persist=False` — raw notebooks write to blob storage, not Delta.
- Always `enforce_schema=False` on target.
- Always `increment_driver_source_entity_name=None` (literal `None`, **not** the sentinel string).
- No `lifecycle_handler` parameter.
- If the ingestion requires reading another raw entity (e.g., an account list), add it as a keyword arg:
  ```python
  source_<entity_name>_raw=Drl.from_config(
      entity_name="<entity_name>", product="cq", module="int",
      layer=Layer.RAW, source_system="<source_system>"
  )
  ```

## IngestInfoContext — backfill and date window

`logger` is initialized by `platform_init` — do not declare it manually.

```python
# DBTITLE 1,Fetches Ingest date details
import json
from pltdata import IngestInfoContext
from datetime import datetime, timedelta

max_days = 5
ingest_info_context = IngestInfoContext()
ingested_data = ingest_info_context.read_all(
    entity_locator=<entity_var>.entity_locator, upload_days=max_days
)

# For backfilling or if no data yet ingested
if len(ingested_data) == 0:
    report_start_date = str((datetime.now() - timedelta(days=max_days)).date())
    logger.info(f"Extract first time from {report_start_date}")
else:  # For daily load
    report_start_date = str((datetime.now() - timedelta(days=1)).date())
    logger.info(f"Extract after ingest {ingested_data[0].id} from {report_start_date}")
```

When both `report_start_date` and `report_end_date` are needed:

```python
if len(ingested_data) == 0:
    report_start_date = str((datetime.now() - timedelta(days=max_days)).date())
    report_end_date = str((datetime.now() - timedelta(days=1)).date())
else:
    report_start_date = report_end_date = str((datetime.now() - timedelta(days=1)).date())
```

## Blob storage path construction

```python
# DBTITLE 1,Connecting to Delta Lake & creating Folders
lake_connection = LakeConnectFactory().lake_connection
entity_name = "<entity_name>"
module_name = "int"

target_path = "/".join([
    lake_connection.get_root(Layer.RAW),
    f"bu={lake_connection.business_unit}",
    f"pp={lake_connection.platform_product}",
    f"sys=<source_system>",
    f"mod={module_name}",
    f"entity={entity_name}",
])

dbutils.fs.mkdirs(target_path)

target_path_data = f"{target_path}/ingestion-date={datetime.now().strftime('%Y-%m-%d-%H:%M')}"
dbutils.fs.mkdirs(target_path_data)
print(target_path_data)
```

- Do not hard-code environment-specific catalog names — always use `product_environment`.
- Do not use `Layer.EXTERNAL` unless the source is an external zone (not blob).
- The `sys=` segment uses the source system name exactly (e.g., `sys=meta`, `sys=marketo`, `sys=amazon_ads`).

## Data ingestion

Choose the ingestion pattern based on the source system:

### Real API source (e.g., `meta`, `marketo`, `amazon_ads`)

```python
from integration.functions.cq_connect import CqConnect
from integration.functions.<source_api_module> import <ApiClass>
from integration.functions.common_functions import <helper_functions>

<api_client> = <ApiClass>()

# For each account / advertiser / entity:
for <item> in <api_client>.<accounts_list>:
    try:
        entity_val = <api_client>.<get_method>(entity_fields, <item>)
        if entity_val is not None and len(entity_val) > 0:
            data_json = json.dumps(entity_val, ensure_ascii=False, indent=4)
            dbutils.fs.put(
                f"{target_path_data}/{<item>}/{ingest_date}.json",
                data_json,
                overwrite=True,
            )
        else:
            print(f"No data for {<item>}")
    except Exception as e:
        raise e
```

If the API client and method are not known, add a TODO comment. Do not invent API method names.

The `entity_fields` list is typically derived from entity attributes:

```python
entity_fields = [att.name for att in <entity_var>.attributes]
```

or explicitly listed if the API requires a specific subset.

### Synthetic / mock source (e.g., `mockapi`, sample entities, demos)

When the source system is `mockapi` or the user asks for a sample/demo entity, do **not** call an external HTTP endpoint. Instead, generate synthetic data locally using only the Python standard library (`random`, `string`). Never use `requests`, `faker`, or any external URL.

The synthetic generator must:
- Produce records matching the entity's `attributes` (field names and plausible values for each type).
- Return a `list[dict]` that is JSON-serialized and written to blob storage identically to the real API pattern.
- Be self-contained in a single cell with no external dependencies.

Template:

```python
import random
import string

def _random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase, k=length))

def _generate_<entity_name>(count=50):
    """Generate synthetic <entity_name> records matching the entity attributes."""
    records = []
    for i in range(1, count + 1):
        records.append({
            # One key per entity attribute — generate plausible fake values:
            # "id": i,
            # "name": _random_string(10).capitalize(),
            # "email": f"{_random_string(6)}@example.com",
            # "created_at": f"{report_start_date}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
        })
    return records

<entity_name>_data = _generate_<entity_name>(50)

if <entity_name>_data is not None and len(<entity_name>_data) > 0:
    data_json = json.dumps(<entity_name>_data, ensure_ascii=False, indent=4)
    dbutils.fs.put(
        f"{target_path_data}/<entity_name>/{report_start_date}.json",
        data_json,
        overwrite=True,
    )
    size = len(<entity_name>_data)
else:
    print("No data generated")
    size = 0
```

Rules:
- Do NOT import `requests` or call any HTTP URL for mock/sample entities.
- Do NOT use `faker` or any third-party library — use only `random` and `string`.
- Tailor the generated values to each attribute type (integers for IDs, email-like strings for emails, city names for cities, etc.).
- Default to 50 records unless the user specifies a different count.

## Schema write and ingest log

```python
# Loading schema details to container
dbutils.fs.put(
    f"{target_path}/schema.json",
    json.dumps(<entity_var>.to_dict()),
    overwrite=True
)

# create metadata information about loaded data
ingest_info_context.create_new(
    upload_type="nested_json",
    system="<source_system>",
    entity_name="<entity_name>",
    folder_path=target_path_data,
    folder_size=<size_variable>
)
```

- `upload_type` is almost always `"nested_json"`.
- `folder_size` is a count of records or files written (e.g., `size`, `1`, `len(file_paths)`).

## End transform

```python
plt_transform.end_transform(None)
```

Always `None` — raw notebooks produce no DataFrame.
