# Demo — Data Platform Skills

This directory contains a self-contained demo environment for showcasing the data platform coding skills.

## What's here

```
demo/
├── pltdata/                          ← Mock platform framework (importable as `pltdata`)
│   ├── __init__.py                   ← Main exports: Layer, AttrType, Entity, Drl, ...
│   ├── _types.py                     ← Layer, AttrType, EntityType, FieldType enums
│   ├── _models.py                    ← Parameter, Attribute, Entity, EntityProperty, ...
│   ├── _drl.py                       ← Drl (data registry locator)
│   ├── _transform.py                 ← PltDebugTransform, PltDataFrame, LifecycleHandler
│   ├── _deploy.py                    ← Deploy (entity registry stub)
│   ├── _lake_connect.py              ← LakeConnectFactory (environment-aware connection)
│   └── _schema.py                    ← SchemaTranslate (Spark schema builder)
│
└── databricks/
    ├── _platform_app/
    │   └── plt_init.py               ← Framework bootstrap (equivalent to %run plt_init)
    ├── 1-raw/customers/              ← Raw ingest notebook (CRM → raw layer)
    ├── 3-staging/customers/          ← Staging transform notebook
    ├── 4-enriched/customers/         ← Enriched transform notebook
    └── 5-curated/customer360/        ← Curated profile notebook
```

## Demo pipeline: `customers` initiative

The demo shows a complete **CRM customers** data pipeline:

| Layer | Entity locator | What it does |
|---|---|---|
| Raw | `raw/crm/customers/int/customers` | Ingest raw CRM records |
| Staging | `staging/crm/customers/int/customers` | Normalise and validate |
| Enriched | `enriched/demo/int/crm_customers` | Derive new attributes |
| Curated | `curated/demo/customer_profile` | Build customer 360 profile |

## Mock framework (`pltdata`)

The mock framework mirrors the real platform framework API — same imports, same class names, same method signatures. Instead of executing Databricks/Delta operations it **logs intent**:

```python
from pltdata import Layer, AttrType, EntityType
from pltdata import Attribute, Entity, Drl
from pltdata import PltDebugTransform, Deploy, LakeConnectFactory

# All classes work locally — no Spark or Databricks connection needed
entity = Entity(entity_name="customers", layer=Layer.STAGING, ...)
Deploy().deploy_entity(entity)
# → [Deploy] Registering entity: 'customers' | layer=staging | ...
```

## Running locally

```bash
# From demo/ directory — add mock framework to Python path
cd demo
PYTHONPATH=. python databricks/3-staging/customers/transform_customers.py
```

## Using the skills in this demo

1. Load a skill from `agents/skills/<skill-name>/SKILL.md`
2. Point it at this demo project as the target repository
3. The generated notebooks use `from pltdata import ...` — resolved by the mock framework
4. No real Databricks cluster needed to read and understand the generated output

## Environment control

Set `PLATFORM_ENVIRONMENT` env var to switch environments:

```bash
PLATFORM_ENVIRONMENT=qua python databricks/4-enriched/customers/transform_customers.py
```
