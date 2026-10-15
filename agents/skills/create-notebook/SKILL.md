---
name: create-notebook
description: Create or modify any Databricks platform notebook — raw ingestion, staging transform, enriched transform, curated transform, or a full multi-layer pipeline. Use when asked to create, scaffold, or modify notebooks in databricks/1-raw/, databricks/3-staging/, databricks/4-enriched/, or databricks/5-curated/.
---

# Create Platform Notebook

Use this skill for any request to create, scaffold, modify, or review a Databricks platform notebook — single layer or multi-layer pipeline.

## Scope Guard

In scope:

- Raw ingestion notebooks (`databricks/1-raw/`)
- Staging transform notebooks (`databricks/3-staging/`)
- Enriched transform notebooks (`databricks/4-enriched/`)
- Curated transform notebooks (`databricks/5-curated/`)
- Multi-layer pipelines (any combination of the above)

Out of scope:

- Framework library changes, deployment config, or CI/CD edits unless explicitly requested

## References

Always read before generating:

- `agents/skills/understand-platform-framework/SKILL.md` — authoritative platform framework API reference
- `references/<layer>.md` — code templates for the target layer (see routing table below)

Also read when applicable:

- `references/entity-definition.md` — when creating or changing an Entity constructor, its attributes, locator, keys, retention, or deploy cell; covers rules shared across all layers
- `references/cross-layer.md` — when creating two or more layers
- `agents/skills/EXAMPLES.md` — when handling cross-layer pipelines or when source system may differ from folder name

## Layer Routing

Determine the target layer(s) from the user request, then read the corresponding reference file(s):

| Layer | Folder | Reference file |
|---|---|---|
| Raw | `databricks/1-raw/` | `references/raw.md` |
| Staging | `databricks/3-staging/` | `references/staging.md` |
| Enriched | `databricks/4-enriched/` | `references/enriched.md` |
| Curated | `databricks/5-curated/` | `references/curated.md` |
| Two or more layers | any combination | all relevant layer files + `references/cross-layer.md` |

If the user mentions a folder path, use that to determine the layer. If the layer is ambiguous, ask before proceeding.

Inspect similar notebooks in the same source system folder before creating. Prefer examples from the same source system.

Do not modify framework libraries, deployment config, or CI/CD files unless explicitly requested.

## Serverless Environment Block (PEP 723)

Every generated notebook must include a PEP 723 serverless environment block. This block lives in the **file header** of the `.py` source file — it is **invisible** in the Databricks notebook UI (it appears only in the Environment panel). It must **never** be created as a visible notebook cell.

The block must be written exactly as shown below:

```
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
```

In the `.py` source file, the header looks like this:

```
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %run "../../_platform_app/platform_init"

# COMMAND ----------
```

The PEP 723 block sits between `# Databricks notebook source` and `# MAGIC %run` in the header. The `%run` is the first **visible** cell in the notebook UI. The PEP 723 block is metadata only.

Rules that must never be violated:
- **Do NOT create a notebook cell for the PEP 723 block** — it must only exist in the file header.
- The path is always `/Workspace/Shared/environment/int-default-env.yml` — do not invent or shorten this path.
- Do NOT use `workspace-base-environments/...` paths — those are internal Databricks cluster environment IDs, not the correct value here.
- Do not add `environment_version`, `base_environment_version`, or any other key inside `[tool.databricks.environment]`.
- Do not add a `[dependencies]` section or `requires-python`.

### How to inject the PEP 723 block

Since the PEP 723 block is file-header metadata (not a cell), it cannot be added via `editAsset(add)`. After creating the notebook and adding all cells, inject it by modifying the `.py` source file directly via the Databricks workspace API:

```python
import requests, base64

host = spark.conf.get("spark.databricks.workspaceUrl")
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
headers = {"Authorization": f"Bearer {token}"}

PEP723_BLOCK = """# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///"""

def inject_pep723(notebook_path):
    """Inject the PEP 723 block into a notebook's file header."""
    # Export
    resp = requests.get(
        f"https://{host}/api/2.0/workspace/export",
        headers=headers,
        params={"path": notebook_path, "format": "SOURCE"}
    )
    content = base64.b64decode(resp.json()["content"]).decode("utf-8")
    lines = content.split("\n")

    # Remove any existing PEP 723 block(s) from header
    cleaned = []
    in_pep723 = False
    for line in lines:
        if line.strip() == "# /// script":
            in_pep723 = True
            continue
        if in_pep723:
            if line.strip() == "# ///":
                in_pep723 = False
                continue
            continue
        cleaned.append(line)

    # Insert PEP 723 block after '# Databricks notebook source'
    result = []
    for line in cleaned:
        result.append(line)
        if line == "# Databricks notebook source":
            result.append(PEP723_BLOCK)

    new_content = "\n".join(result)
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    # Import back
    resp = requests.post(
        f"https://{host}/api/2.0/workspace/import",
        headers=headers,
        json={"path": notebook_path, "format": "SOURCE", "language": "PYTHON",
              "content": encoded, "overwrite": True}
    )
    return resp.status_code == 200
```

Call `inject_pep723(notebook_path)` for each generated notebook after all cells have been added.

## How to Create Notebooks (Cell-by-Cell)

Notebooks are created as **Databricks notebook assets** (not plain `.py` files). The agent must add content cell-by-cell using `editAsset` with `operation: "add"`. Do NOT write `# COMMAND ----------` separators, `# DBTITLE 1,...` markers, or `# Databricks notebook source` in cell content — those are `.py` source-file serialization artifacts. Instead:

1. **Create the notebook** via `createAsset` with `assetType: "notebook"`.
2. **Read the notebook** via `readAssetById` with `assetType: "notebook"` and the returned asset ID — this gives you cell nuids needed for the `target` field.
3. **Add cells** via `editAsset` with `operation: "add"`. Each cell is a separate `content` item:
   - `target`: the nuid of the cell to insert after (use `"BEGIN"` to insert at the start; subsequent items in the same call chain automatically).
   - `title`: the cell title (what `# DBTITLE 1,<Title>` would show in the UI).
   - `language`: `"python"`, `"sql"`, `"md"`, or `"run"` (for `%run` cells).
   - `patches`: one entry with `old_text: ""` and `new_text: <cell content>` (the code/text only — no `# MAGIC`, no `# COMMAND ----------`, no `# DBTITLE`).
4. **Inject the PEP 723 block** into the file header via the workspace API (see above). This is the **last step** after all cells are added.

### Language mapping

| Content type | `language` value | `new_text` format |
|---|---|---|
| Python code | `"python"` | Raw Python code (no `# MAGIC` prefix) |
| `%run "..."` | `"python"` | `%run "../../_platform_app/platform_init"` |
| Markdown | `"md"` | Raw markdown (no `# MAGIC %md` prefix) |
| SQL | `"sql"` | Raw SQL (no `# MAGIC %sql` prefix) |

### Cell content rules

- **No serialization artifacts**: Never include `# Databricks notebook source`, `# COMMAND ----------`, `# DBTITLE 1,...`, or `# MAGIC` prefixes in cell `new_text`.
- **Titles via metadata**: Set the cell title using the `title` field in the `editAsset` content item, not via `# DBTITLE`.
- **No PEP 723 cell**: Never create a visible cell for the PEP 723 environment block — it is injected into the file header as the last step (see above).
- **First cell**: The first cell in every notebook should be the `%run` init cell.

### Example: creating a notebook end-to-end

```python
# Step 1: Create notebook
nb = createAsset({ asset: { assetType: "notebook", name: "<full_repo_path>" } })

# Step 2: Read to get cell nuids
nb_info = readAssetById({ assetType: "notebook", assetId: nb.assetId })
first_cell_nuid = nb_info.cells[0].nuid

# Step 3: Add cells (first cell is %run, NOT PEP 723)
editAsset({
  asset: { type: "notebook", id: nb.assetId, name: "<name>" },
  operation: "update",
  content: [{
    target: first_cell_nuid,
    title: "",
    language: "python",
    patches: [{ old_text: "", new_text: "%run \"../../_platform_app/platform_init\"", replace_all: false }]
  }]
})

editAsset({
  asset: { type: "notebook", id: nb.assetId, name: "<name>" },
  operation: "add",
  content: [
    { target: first_cell_nuid, title: "Entity Definition", language: "python",
      patches: [{ old_text: "", new_text: "my_entity = Entity(...)\n...", replace_all: false }] },
    { title: "Deploy Entity", language: "python",
      patches: [{ old_text: "", new_text: "Deploy().deploy_entity(my_entity)", replace_all: false }] }
  ]
})

# Step 4: Inject PEP 723 into file header (LAST step)
inject_pep723("<notebook_workspace_path>")
```

## Output File Paths

Create each notebook as a **Databricks notebook** (not a plain `.py` file) **inside the repository** where this skill lives.

### Asset type: always `notebook`

When calling `createAsset`, always use `assetType: "notebook"` — never `assetType: "file"`. A plain file does not have cells, `# COMMAND ----------` separators, or `# DBTITLE` titles; only a notebook does. The notebook name should **not** include the `.py` extension — Databricks adds it automatically for Python notebooks stored in Git repos.

```
createAsset({ asset: { assetType: "notebook", name: "<full_absolute_path_without_.py>" } })
```

After creation, use `editAsset` with `asset.type = "notebook"` and the returned asset ID to add cells.

### Repository root

The repository root is determined by navigating up from this skill file's location (`<repo_root>/agents/skills/create-notebook/SKILL.md`) — the repo root is the great-great-grandparent directory.

Concretely, if this skill file is at:
```
/Workspace/Repos/<user>/<repo_name>/agents/skills/create-notebook/SKILL.md
```
then the repo root is:
```
/Workspace/Repos/<user>/<repo_name>
```
and all notebooks must be created under `<repo_root>/databricks/`.

### Critical rules

- Always use `assetType: "notebook"` in `createAsset` — **never** `assetType: "file"`. Plain files are not notebooks and will not have cells.
- Always use the **full absolute workspace path** starting with `/Workspace/Repos/...` when creating notebooks.
- Do NOT create notebooks under `/Workspace/Users/` — that is the user's home directory, not the repository.
- Do NOT use relative paths (e.g. `databricks/1-raw/...`) without the repo root prefix — the Databricks workspace resolves relative paths against the user's home, which is wrong.
- Do NOT include the `.py` extension in the notebook name — Databricks adds it automatically in Git repos.
- Do NOT run any Databricks CLI upload command.

### Notebook path table

Write each notebook to the path shown below (without `.py`), creating the `<source_system>` subfolder via `createAsset({ asset: { assetType: "directory", name: "..." } })` if it does not already exist. Never group multiple layers into a shared folder. Never prefix the filename with the layer number or layer name.

| Layer | Path under `<repo_root>/databricks/` |
|---|---|
| Raw | `1-raw/<source_system>/transform_<source_system>_<entity_name>` |
| Staging | `3-staging/<source_system>/transform_<entity_name>` |
| Enriched | `4-enriched/<source_system>/transform_<entity_name>` |
| Curated | `5-curated/<module>/transform_<entity_name>` |

Example for a raw notebook with `source_system=mockapi`, `entity_name=employees`, and repo at `/Workspace/Repos/user@example.com/<repo-name>`:
- Correct: `createAsset({ asset: { assetType: "notebook", name: "/Workspace/Repos/user@example.com/<repo-name>/databricks/1-raw/mockapi/transform_mockapi_employees" } })`
- Wrong: `assetType: "file"` — creates a plain `.py` file without notebook cells
- Wrong: `/Workspace/Users/...` — creates in the user's home, not the repo
- Wrong: `databricks/1-raw/mockapi/transform_mockapi_employees` — relative path resolves to `/Workspace/Users/`

## Required Inputs

Before generating, all required inputs must be confirmed. Follow this workflow:

### Step 1: Extract from user prompt and repo

Check whether inputs are already provided in the message or in referenced files or notebooks.

### Step 2: Ask for missing required inputs

Ask all missing inputs in a single consolidated question. Do NOT generate with TODOs — ask first.

### Step 3: Discover from existing upstream layers

If upstream layers exist, read them and extract `entity_name`, `entity_locator`, `source_system` from the `Entity(...)` constructor — these are authoritative; never infer from folder or file names. Offer derived values for confirmation.

### Step 4: Generate only when inputs are complete

Generate the full notebook with no TODOs. Do not invent business logic, API methods, keys, or type mappings.

---

### Raw — required inputs

| Input | Example | How to infer |
|---|---|---|
| `source_system` | `meta`, `marketo`, `amazon_ads` | Ask if not stated |
| `entity_name` | `campaigns`, `leads` | Ask if not stated |
| API client class | `MetaApiClient` | Look up in `integration/functions/`; ask if not found |
| API fetch method | `get_campaigns` | Look up in client class; ask if not found |
| attributes with native API types | `id` BIGINT, `name` STRING | Ask or derive from similar notebooks |

Optional defaults: `product=cq`, `module=int`, `version="1.0.0"`, `is_public=False`, `max_days=5`, `upload_type="nested_json"`

---

### Staging — required inputs

| Input | Example | How to infer |
|---|---|---|
| `source_system` | `meta`, `marketo` | Ask if not stated |
| `entity_name` | `campaigns`, `leads` | Ask if not stated |
| attribute column names | `id`, `name`, `createdAt` | Look up from raw entity; ask if not found |

Optional defaults: `product=cq`, `module=int`, `version="1.0.0"`, `is_public=False`

---

### Enriched — required inputs

| Input | Example | How to infer |
|---|---|---|
| `source_system` | `meta`, `marketo` | Ask if not stated |
| `entity_name` | `campaigns`, `leads` | Ask if not stated |
| `staging_entity_name` | same as entity_name | Confirm |
| attributes (name, type, is_key) | `id` BIGINT PK, `name` STRING | Ask or look up from staging entity |
| `dedup_sort_column` | `updated_at`, `UploadDate` | Ask which timestamp to sort by |

Optional defaults: `product=cq`, `module=int`, `version="1.0.0"`, `is_public=False`

---

### Curated — required inputs

| Input | Example | How to infer |
|---|---|---|
| `entity_name` | `ace_contact`, `ecommerce_orders` | Ask if not stated |
| `source_system` | `ace`, `ecommerce` | Ask or infer from entity name |
| source entity locators | `enriched/cq/int/ace/contact` | Ask or look up from enriched layer |
| key attributes (`is_key=True`) | `contact_id` | Ask which columns uniquely identify a row |
| merge type | `MERGE_ON_PRIMARY_KEY`, `FULL_REPLACE` | Ask — never assume |
| delete behavior | no delete / soft delete / hard delete | Ask explicitly |

Optional defaults: `product=cq`, `module=int`, `version="1.0.0"`, `is_public=False`, `data_scope=DataScope.UNKNOWN`

---

## Multi-layer Pipeline

When two or more layers need to be created, also read `references/cross-layer.md`.

1. Check which target notebooks already exist — classify each layer as **existing** or **new**
2. For **existing** layers: read the file and extract `entity_name`, `entity_locator`, `source_system` from the `Entity(...)` constructor — never infer from folder or file names
3. Collect inputs only for **new** layers
4. Resolve cross-layer source references using extracted values (see `references/cross-layer.md`)
5. Generate new layers in dependency order: raw → staging → enriched → curated
6. Do not modify existing layers unless explicitly asked

Collect all missing inputs in a single consolidated question before generating any notebook.

## Done Criteria

### Raw
- notebook under `databricks/1-raw/<source_system>/transform_<source_system>_<entity_name>.py`
- PEP 723 block present in file header (not as a visible cell — injected via workspace API after all cells are added); first visible cell is `%run "../../_platform_app/platform_init"` — no wizard preamble
- entity: `layer=Layer.RAW`, locator `raw/cq/<source_system>/int/<entity_name>`, no `source=`
- attributes use native API types (not all STRING); no `is_key`, `retention_duration`, `field_type`, `data_scope`
- `PltDebugTransform`: `target_persist=False`, `enforce_schema=False`, `increment_driver_source_entity_name=None`, no `lifecycle_handler`
- `IngestInfoContext` backfill logic present; blob path uses `lake_connection.get_root(Layer.RAW)` with correct segments
- `dbutils.fs.put(...schema.json...)` and `ingest_info_context.create_new(...)` called
- `plt_transform.end_transform(None)` called once

### Staging
- notebook under `databricks/3-staging/<source_system>/transform_<entity_name>.py`
- PEP 723 block and wizard markdown preamble present with `STAGING` layer
- entity: `layer=Layer.STAGING`, locator `staging/cq/<source_system>/int/<entity_name>`
- all attributes except `UploadDate` use `AttrType.STRING` with `source` DRL path; `UploadDate` is last with `AttrType.TIMESTAMP`
- `PltDebugTransform`: `FULL_REPLACE`, `StagingIngestionLifecycleHandler`, `enforce_schema=True`, sentinel string
- `try/except NameError` block present; inner loop entity uses `layer=Layer.RAW` and `attributes=[]`
- `read_dataframe(...) is None` guard; column-rename and column-drop loops present
- `unionByName(..., allowMissingColumns=True)` used; `plt_transform.end_transform(target)` called once

### Enriched
- notebook under `databricks/4-enriched/<source_system>/transform_<entity_name>.py`
- PEP 723 block and wizard preamble with `ENRICHED` layer
- entity variable `<name>_enriched`; `entity_name` param `<source_system>_<entity_name>`
- `entity_locator` = `enriched/cq/int/<source_system>/<entity_name>` — source system **after** int
- entity: `layer=Layer.ENRICHED`, `retention_duration` present, PKs have `is_key=True`
- all attributes typed (not all STRING) with staging `source` DRL paths
- `PltDebugTransform`: `MERGE_ON_PRIMARY_KEY`, `EnrichedIngestionLifecycleHandler` (list as first arg), `enforce_schema=True`, sentinel string
- null normalization loop present; ROW_NUMBER dedup present when `is_key` attributes exist
- `plt_transform.end_transform(target)` called once

### Curated
- notebook under `databricks/5-curated/<module>/transform_<entity_name>.py`
- PEP 723 block present; entity: `layer=Layer.CURATED`, locator `curated/cq/<module>/<entity_name>`, `retention_duration` present
- merge type explicit; delete behavior deliberate; PKs have `is_key=True`
- `PltDebugTransform`: sentinel string; `source_<enriched_entity_name>_enriched=Drl.from_config(...)` uses framework-registered values (not folder name)
- final dataframe columns match target entity attributes; `end_transform` called once

### All notebooks
- no hard-coded environment-specific catalog names — always use `product_environment`
- no secrets or credentials added
- no unrelated files modified
