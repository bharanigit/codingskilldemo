# Entity Pipeline — Cross-Layer Wiring Reference

## Per-layer templates

For the code templates of each individual layer, read the corresponding reference file directly:

| Layer | Reference file |
|---|---|
| Raw | `agents/skills/create-notebook/references/raw.md` |
| Staging | `agents/skills/create-notebook/references/staging.md` |
| Enriched | `agents/skills/create-notebook/references/enriched.md` |
| Curated | `agents/skills/create-notebook/references/curated.md` |

This file contains only what is unique to multi-layer pipelines: how to resolve the source references that wire one layer to the next, using values extracted from existing notebooks.

---

## Cross-layer source references

### Staging → Raw

Staging needs the raw entity's locator and framework-registered `entity_name` / `source_system`.

| Value | Existing raw notebook | New raw notebook |
|---|---|---|
| `raw_entity_locator` | Read `entity_locator=` from raw `Entity(...)` | `raw/cq/<source_system>/int/<entity_name>` |
| `raw_entity_name` | Read `entity_name=` from raw `Entity(...)` | confirmed input |
| `raw_source_system` | Read `source_system=` from raw `Entity(...)` | confirmed input |

```python
lifecycle_handler=StagingIngestionLifecycleHandler(
    "<raw_entity_locator>",
    <staging_entity_var>.entity_locator
)

source_<raw_entity_name>_raw=Drl.from_config(
    entity_name="<raw_entity_name>",
    product="cq",
    module="int",
    layer=Layer.RAW,
    source_system="<raw_source_system>"
)
```

### Enriched → Staging

Enriched needs the staging entity's locator and attribute names.

| Value | Existing staging notebook | New staging notebook |
|---|---|---|
| `staging_entity_locator` | Read `entity_locator=` from staging `Entity(...)` | `staging/cq/<source_system>/int/<entity_name>` |
| `staging_entity_name` | Read `entity_name=` from staging `Entity(...)` | confirmed input |
| `staging_source_system` | Read `source_system=` from staging `Entity(...)` | confirmed input |
| staging attribute names | Read `attributes=[...]` from staging `Entity(...)` | from raw field names |

```python
lifecycle_handler=EnrichedIngestionLifecycleHandler(
    ["<staging_entity_locator>"],
    <enriched_entity_var>.entity_locator,
    True
)

source_<staging_entity_name>_staging=Drl.from_config(
    entity_name="<staging_entity_name>",
    product="cq",
    module="int",
    layer=Layer.STAGING,
    source_system="<staging_source_system>"
)

# Each enriched attribute source DRL:
Attribute(
    name="<enriched_col>",
    attr_type=AttrType.<TYPE>,
    source=["staging/cq/<staging_source_system>/int/<staging_entity_name>/<staging_col>"],
)
```

### Curated → Enriched

Curated needs the enriched entity's framework-registered `entity_name` and `source_system` — **not** the folder name or file name.

| Value | Existing enriched notebook | New enriched notebook |
|---|---|---|
| `enriched_entity_name` | Read `entity_name=` from enriched `Entity(...)` (e.g., `"ace_contact"`) | `<source_system>_<entity_name>` |
| `enriched_source_system` | Read `source_system=` from enriched `Entity(...)` (may differ from folder) | confirmed input |

```python
source_<enriched_entity_name>_enriched=Drl.from_config(
    entity_name="<enriched_entity_name>",
    product="cq",
    module="int",
    layer=Layer.ENRICHED,
    source_system="<enriched_source_system>"
)
```

> **Critical:** `Drl.from_config` uses the framework-registered `entity_name` and `source_system` from the enriched `Entity(...)` constructor — not the folder name or file name. Always read the existing enriched notebook before generating curated.
