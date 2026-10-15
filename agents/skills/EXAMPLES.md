# Claude Code Skills — Usage Examples

Concrete walk-throughs showing exactly how each skill behaves, what Claude asks, and why

---

## Pipeline Skills (batch)

### Example 1 — Full pipeline from scratch

**User prompt:**

> Create a full pipeline for amazon_ads sponsored_products — raw through curated.

**Claude would:**

1. Check paths — all four notebooks are missing → all classified as **new**
2. Ask **once** for all missing inputs:
   - API client class, fetch method, and attribute types (for raw)
   - Key columns and dedup sort column (for enriched)
   - Curated module name, merge type, delete behavior (for curated)
3. Generate in order: raw → staging → enriched → curated
4. Staging's `StagingIngestionLifecycleHandler` gets `"raw/cq/amazon_ads/int/sponsored_products"` — derived from naming convention since raw is new
5. Curated's `Drl.from_config` gets `entity_name="amazon_ads_sponsored_products"`, `source_system="amazon_ads"` — derived from enriched which was just created in step 3

**What Claude does NOT do:**
- Generate any layer before collecting all inputs
- Ask separately for each layer (one consolidated question)
- Invent API method names or attribute types

---

### Example 2 — Existing raw, create staging + enriched + curated

**User prompt:**

> Raw for crm contact already exists. Create staging, enriched, and curated for it.

**Claude would:**

1. Check `databricks/1-raw/crm/transform_crm_contact.py` — **exists**
2. Read it and extract from the `Entity(...)` constructor:
   ```
   entity_name="crm_contact"
   entity_locator="raw/cq/crm_source/int/crm_contact"   ← note: crm_source, not crm
   source_system="crm_source"
   ```
3. Check staging/enriched/curated paths — all missing → all classified as **new**
4. Ask only for staging/enriched/curated inputs (not raw — it exists)
5. Staging's `StagingIngestionLifecycleHandler` gets `"raw/cq/crm_source/int/crm_contact"` — the **extracted** locator, not a guessed path
6. Curated's `Drl.from_config` gets `entity_name="crm_contact"`, `source_system="crm_source"` — extracted from the enriched notebook after it is created in step 5

**Why the read-then-extract step is critical:**

If Claude had guessed from the folder name and request, it would have generated:
```
"raw/cq/crm/int/contact"   ← wrong source_system, wrong entity_name
```

The actual locator is:
```
"raw/cq/crm_source/int/crm_contact"   ← source_system="crm_source", entity_name="crm_contact"
```

The folder is named `crm/`. The file is named `transform_crm_contact.py`. Neither reveals `source_system="crm_source"`. Only reading the `Entity(...)` constructor gives the authoritative values. A wrong locator here means staging silently reads zero files and writes an empty table with no error.

---

### Example 3 — Only curated is missing

**User prompt:**

> Enriched for marketo leads is done. Just need the curated notebook.

**Claude would:**

1. Check `databricks/5-curated/` — curated not found → **new**
2. Check `databricks/4-enriched/marketo/transform_marketo_leads.py` (or user-specified path) — **exists**
3. Read it and extract:
   ```
   entity_name="marketo_leads"
   entity_locator="enriched/cq/int/marketo/leads"
   source_system="marketo"
   ```
4. Ask only for: module name, merge type, delete behavior, key column confirmation
5. Generate curated notebook with:
   ```python
   source_marketo_leads_enriched=Drl.from_config(
       entity_name="marketo_leads",
       product="cq",
       module="int",
       layer=Layer.ENRICHED,
       source_system="marketo"
   )
   ```

**Key insight:** Claude does not ask "what is your enriched entity name?" — it reads the existing notebook and extracts it. The only things Claude asks are the decisions a human must make (module, merge type, delete behavior).

---

### Example 4 — Mixed: some layers new, some modified

**User prompt:**

> We have raw and staging for ecommerce orders. Add enriched and curated.

**Claude would:**

1. Check four paths:
   - `databricks/1-raw/ecommerce/` — found → **existing**
   - `databricks/3-staging/ecommerce/` — found → **existing**
   - `databricks/4-enriched/ecommerce/` — not found → **new**
   - `databricks/5-curated/` for ecommerce orders — not found → **new**
2. Read raw notebook → extract `entity_name`, `entity_locator`, `source_system`
3. Read staging notebook → extract staging locator and attribute names (used as enriched `source` DRL paths)
4. Ask for: enriched types and primary keys, curated module/merge-type/delete behavior
5. Generate enriched and curated only — does not touch raw or staging

---

## Individual Layer Skills

### Example 5 — Single raw notebook

**User prompt:**

> Create a raw ingest notebook for meta campaigns.

**Claude would:**

1. Ask:
   - What attributes does the campaigns API return, and what are their types?
   - What is the API client class and fetch method?
2. Generate `databricks/1-raw/meta/transform_meta_campaigns.py` with:
   - `target_persist=False`
   - `increment_driver_source_entity_name=None`
   - IngestInfoContext for date-windowed backfill
   - Blob path using `LakeConnectFactory` (no hard-coded environment names)
   - `end_transform(None)`

**What Claude does NOT do:**
- Add `UploadDate` to the raw entity (staging adds it)
- Use `AttrType.STRING` for all attributes (native API types required)
- Invent the API method name

---

### Example 6 — Enriched with complex source name mismatch

**User prompt:**

> Create enriched for crm contact. Staging is at staging/cq/crm_source/int/crm_contact.

**Claude would:**

1. Read the staging notebook to get the attribute list (camelCase staging names, all STRING)
2. Generate enriched entity with:
   ```python
   entity_name="crm_contact"            # = "crm_source_crm_contact"? No:
   # enriched entity_name = "<source_system>_<entity_name>"
   # but source_system here is "crm_source"
   # so entity_name="crm_source_crm_contact"? Or is entity_name just "crm_contact"?
   # → Claude reads SKILL.md rule: entity_name = source_system + "_" + entity_name
   # → asks for confirmation before generating
   entity_locator="enriched/cq/int/crm_source/crm_contact"   ← sys AFTER int
   source_system="crm_source"
   ```
3. Maps staging camelCase names to enriched snake_case:
   ```python
   Attribute(
       name="contact_id",              # enriched snake_case
       attr_type=AttrType.BIGINT,
       source=["staging/cq/crm_source/int/crm_contact/ContactId"],  # staging camelCase
       is_key=True
   )
   ```
4. Adds null normalization loop (always)
5. Adds ROW_NUMBER dedup on `contact_id` (always when `is_key=True` attributes exist)

**Key insight:** The enriched locator is `enriched/cq/int/crm_source/crm_contact` — `crm_source` (the `source_system`) comes **after** `int`. Every other layer puts `source_system` before `int`. This inversion is encoded in the enriched SKILL.md and docs.md; Claude applies it automatically.

---

## Code Review

### Example 7 — Reviewing a new notebook before merging

**User prompt:**

> Review this staging notebook before I raise a PR.

**Claude would:**

1. Identify technologies present: Python, PySpark, Databricks notebook, Delta Lake
2. Apply 43 checklist sections in priority order: Correctness → Security → Reliability → Performance → Cost → Maintainability
3. Check framework-specific correctness:
   - All staging attributes `AttrType.STRING`?
   - `UploadDate` last attribute with `AttrType.TIMESTAMP` and no `source`?
   - `read_dataframe(uploaded_file) is None` guard present?
   - `attr.source is None` (not `== None`) in the loop?
   - No hard-coded environment names?
4. Report findings in the standard table:

| Issue | Severity | Recommendation | Example Fix |
|---|---|---|---|
| `attr.source == None` on line 74 | High | PySpark may override `==`; use identity check | `if attr.source is None` |
| `logger.info(f"Processing {secret_token}")` | Critical | Never log tokens | Remove token from log line |

5. Provide Review Summary with overall assessment, finding counts, and top 3 priorities

**What Claude does NOT do:**
- Invent performance numbers ("this will be 40% faster")
- Invent line numbers it hasn't seen
- Flag every `display()` as a defect
- Report a finding without evidence it is actually present

---

## Integration Tests

### Example 9 — Controlled integration test for a new initiative

**User prompt:**

> Create integration tests for the marketo leads initiative — controlled test through curated.

**Claude would:**

1. Read `databricks/tests/integration/config/integration_tests.json` and existing test folders to understand the pattern
2. Read `.config/module.json` to find the workflow name:
   ```
   entity "marketo_leads" → workflow "marketo" → job "platform Workflow - marketo_int"
   ```
3. Trace the vertical slice: staging anchor → enriched → curated
4. Check compiled functions exist under `databricks/lib/integration-lib/integration/bin/`
5. Generate `databricks/tests/integration/marketo/setup_marketo.py`:
   - Inserts one deterministic synthetic row into staging with a unique key
   - Returns `{"key": selected_key, "target_table": "..."}` via `dbutils.notebook.exit`
6. Generate `databricks/tests/integration/marketo/validate_marketo.py`:
   - Reads widgets from the runner
   - Asserts the synthetic key exists in the curated table with correct mappings
7. Add config entry to `integration_tests.json`:
   ```json
   {
     "initiative": "marketo",
     "test_type": "controlled_test_data",
     "allowed_envs": ["dev"],
     "enabled": true,
     "required_boundary": "curated",
     "target_job_name": "platform Workflow - marketo_int",
     ...
   }
   ```

**What Claude does NOT do:**
- Use `dbutils.notebook.run` to execute a platform transformation notebook directly
- Add a `target_notebooks` field — that bypasses the compiled execution path
- Create controlled tests for QUA — DEV only by default

---

---

### Example 10 — Full pipeline with all inputs provided upfront (mockapi customer)

**User prompt:**

```
Using the skill at /Workspace/Repos/<user>/<repo>/agents/skills/create-notebook/SKILL.md,
create a multi-layer pipeline (raw, staging, enriched, curated) for the following entity:

Source system: mockapi
Entity name: customer
Product: cq, Module: int

Attributes:

| Name       | Raw Type | Enriched Type | Is Key |
|------------|----------|---------------|--------|
| id         | BIGINT   | BIGINT        | Yes    |
| first_name | STRING   | STRING        | No     |
| last_name  | STRING   | STRING        | No     |
| email      | STRING   | STRING        | No     |
| phone      | STRING   | STRING        | No     |
| address    | STRING   | STRING        | No     |
| city       | STRING   | STRING        | No     |
| country    | STRING   | STRING        | No     |
| created_at | STRING   | TIMESTAMP     | No     |

Raw layer: Source is mockapi (synthetic data generation, not a real API).
  Data is written as JSON to blob storage.
Staging layer: Flattens raw JSON, all columns as STRING + UploadDate TIMESTAMP.
Enriched layer: Typed attributes, dedup by id sorted by created_at DESC,
  null normalization.
Curated layer: MERGE_ON_PRIMARY_KEY, passthrough from enriched,
  data_scope=DataScope.UNKNOWN.

Create all notebooks as Databricks notebooks in the repo, inject PEP 723
into the file header, and do not create a visible cell for the environment block.
```

**Claude would:**

1. All inputs already provided → no clarifying questions needed; generate immediately in order: raw → staging → enriched → curated
2. Create directories if they don’t exist: `createAsset({ assetType: "directory", name: "<repo_root>/databricks/1-raw/mockapi" })`, etc.
3. Create **Databricks notebooks** (not plain files) in the repo:
   - `<repo_root>/databricks/1-raw/mockapi/transform_mockapi_customer` (notebook)
   - `<repo_root>/databricks/3-staging/mockapi/transform_customer` (notebook)
   - `<repo_root>/databricks/4-enriched/mockapi/transform_customer` (notebook)
   - `<repo_root>/databricks/5-curated/int/transform_mockapi_customer` (notebook)
4. Add cells to each notebook via `editAsset(add)` — no `# COMMAND ----------` or `# DBTITLE` artifacts in cell content
5. Inject PEP 723 block into each notebook’s `.py` file header via the workspace export/import API (last step)

**Cross-layer wiring applied:**

| Transition | Locator used |
|---|---|
| Staging → Raw | `raw/cq/mockapi/int/customer` |
| Enriched → Staging | `staging/cq/mockapi/int/customer` |
| Curated → Enriched | `entity_name="mockapi_customer"`, `source_system="mockapi"` |

Note: enriched locator is `enriched/cq/int/mockapi/customer` — `int` comes **before** `source_system`, unlike raw and staging.

**Entity naming conventions applied:**

| Layer | Variable | `entity_name=` |
|---|---|---|
| Raw | `mockapi_customer_raw` | `"customer"` |
| Staging | `mockapi_customer_staging` | `"customer"` |
| Enriched | `customer_enriched` | `"mockapi_customer"` ← `<source_system>_<entity_name>` |
| Curated | `mockapi_customer_curated` | `"mockapi_customer"` |

**Raw synthetic data generation pattern (for mockapi / sample entities):**

```python
import random
import string

def _random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase, k=length))

def _generate_customer(count=50):
    """Generate synthetic customer records matching the entity attributes."""
    domains = ["example.com", "test.org", "mock.net", "sample.io"]
    cities = ["London", "Paris", "Toronto", "Sydney", "Singapore"]
    countries = ["GB", "FR", "CA", "AU", "SG", "US", "JP"]
    records = []
    for i in range(1, count + 1):
        first = _random_string(6).capitalize()
        last = _random_string(8).capitalize()
        records.append({
            "id": i,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}@{random.choice(domains)}",
            "phone": f"+1{random.randint(2000000000, 9999999999)}",
            "address": f"{random.randint(1, 200)} {_random_string(10).capitalize()} St.",
            "city": random.choice(cities),
            "country": random.choice(countries),
            "created_at": f"{report_start_date}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
        })
    return records
```

Claude uses only `random` + `string` from the standard library. No `requests`, no `faker`, no external HTTP calls.

**Common mistakes Claude must NOT make for this pipeline:**

| Mistake | Correct behaviour |
|---|---|
| PEP 723 block as a visible notebook cell | PEP 723 must be injected into the `.py` file header via workspace export/import API — never as a cell |
| Using `assetType: "file"` in `createAsset` | Always use `assetType: "notebook"` — plain files don’t have cells |
| Including `.py` in the notebook name | Databricks adds `.py` automatically for Python notebooks in Git repos |
| Relative paths like `databricks/1-raw/...` | Always use full absolute `/Workspace/Repos/...` paths |
| Creating notebooks under `/Workspace/Users/` | Always create under `/Workspace/Repos/<user>/<repo>/databricks/` |
| Calling `requests.get("https://mockapi.io/...")` for mockapi entities | Use synthetic data generation with `random` + `string` — no external HTTP calls |
| Curated `PltDebugTransform` with `type=JobType.PYTHON`, `job_config=JobConfig(DedicatedJob(...))` | These classes do not exist — importing them causes `ModuleNotFoundError` |
| `source=["enriched/..."]` on the curated `Entity(...)` constructor | Curated entities never have `source=` on the Entity. Source bindings go in `PltDebugTransform` as `source_<name>_enriched=Drl.from_config(...)` |

---

## Quick Reference — What Claude Always Asks vs. Always Derives

| Value | Claude asks | Claude derives (reads from repo) |
|---|---|---|
| `entity_name` | If not stated | From existing notebook's `Entity(...)` constructor |
| `source_system` | If not stated | From existing notebook's `Entity(...)` constructor |
| `entity_locator` | Never | From existing notebook's `Entity(...)` constructor |
| Staging attribute names | Never (when raw exists) | From raw entity's `attributes=[...]` |
| Enriched source DRL paths | Never (when staging exists) | From staging entity's `attributes[].source` |
| Merge type | Always — never assumes | — |
| Delete behavior | Always — never assumes | — |
| API method names (raw) | Always | — |
| Primary key columns | Always | — |
