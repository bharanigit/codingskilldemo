# Data Platform Skills — Routing Reference

> **Claude Code users:** Skills are registered as slash commands in `.claude/agents/`. Type `/create-notebook`, `/code-review`, etc. directly — no need to paste this file. The `CLAUDE.md` at the repo root is auto-loaded.
>
> This file is an internal reference that skill definitions read to understand routing logic and the layer map.

Use this guide to select the correct skill for each request.

> **Before generating any entity or transform notebook, read [`understand-platform-framework/SKILL.md`](understand-platform-framework/SKILL.md)** — it contains the full platform framework reference (Layer, AttrType, Entity, Drl, LifecycleHandler, etc.) and the authoritative locator rules for each layer.

## Quick selection

| Request type | Skill |
|---|---|
| Create any transform notebook (raw, staging, enriched, curated) | `create-notebook` |
| Create a full pipeline or 2+ layers at once | `create-notebook` |
| Review code / notebook / PR | `code-review` |
| Create or update integration tests | `create-integration-tests` |
| Generate unit tests for a transform notebook | `create-unit-tests` |
| Look up platform framework API (Layer, AttrType, Entity, Drl, locator rules) | `understand-platform-framework` |

## Disambiguation rules

**"Create a notebook for X entity"** — ask which layer (raw / staging / enriched / curated) before generating, then use `create-notebook`.

**"Create a pipeline for X entity"** or any multi-layer request — use `create-notebook`. It handles full and partial pipelines and will check which layers already exist.

**"Add a column / modify / fix a notebook"** — use `create-notebook` and specify the target layer.

**"Review this code / notebook / PR"** — use `code-review`.

## Data platform layer overview

| Layer | Reads from | Produces | Key rule |
|---|---|---|---|
| Raw (`1-raw`) | External API / source system | JSON files in blob storage | No Delta write; `target_persist=False`; `end_transform(None)` |
| Staging (`3-staging`) | Raw blob JSON files | All-STRING Delta table | All attributes `AttrType.STRING`; `FULL_REPLACE`; per-file loop |
| Enriched (`4-enriched`) | Staging Delta table | Typed, deduplicated Delta table | Correct types; `is_key` on PKs; null normalization + ROW_NUMBER dedup |
| Curated (`5-curated`) | Enriched (or Staging) Delta | Typed, keyed Delta with explicit merge | Business logic; merge type and delete behavior must be deliberate |

The locator chain follows: `raw/cq/<sys>/int/<entity>` → `staging/cq/<sys>/int/<entity>` → `enriched/cq/int/<sys>/<entity>` → `curated/cq/int/<module>/<entity>`

Note: enriched locator places `<sys>` **after** `int`, unlike raw and staging.

## Layer map

```
databricks/1-raw/                            → create-notebook (layer: raw)
databricks/3-staging/                        → create-notebook (layer: staging)
databricks/4-enriched/                       → create-notebook (layer: enriched)
databricks/5-curated/                        → create-notebook (layer: curated)
```

## Skill directories

```
skills/
├── create-notebook/              SKILL.md  references/  ← all batch notebook generation
│   └── references/
│       ├── entity-definition.md  ← shared Entity/Attribute rules across all layers
│       ├── raw.md
│       ├── staging.md
│       ├── enriched.md
│       ├── curated.md
│       ├── cross-layer.md
│       └── examples/
│           └── transform_raw_example.py
├── understand-platform-framework/ SKILL.md  ← platform framework API reference (Layer, AttrType, Entity, Drl, etc.)
├── code-review/                  SKILL.md  docs.md
├── create-integration-tests/     SKILL.md  references/
└── create-unit-tests/            SKILL.md  references/
```

Each skill's `references/` subfolder contains the detailed code templates. See `README.md` for full human documentation of all skills.

When handling cross-layer pipelines, or when the source system may differ from the folder name, read `EXAMPLES.md` — it contains concrete walk-throughs that illustrate the read-then-extract workflow and common naming pitfalls.
