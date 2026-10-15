# Data Platform — Claude Code Project Context

This repository contains a Databricks data platform with batch notebooks (raw → staging → enriched → curated).

## Skills

Use the skills below by typing the slash command. Each skill reads its full instructions and reference templates from `agents/skills/`.

| Slash command | What it does |
|---|---|
| `/create-notebook` | Generate a raw, staging, enriched, or curated notebook — single layer or full pipeline |
| `/create-unit-tests` | Generate an isolated pytest module for one transform notebook |
| `/create-integration-tests` | Generate end-to-end integration tests for a full initiative |
| `/code-review` | Review any notebook, PR, or code change across 43 checklist sections |

## Routing

- Any request to **create or modify a notebook** → `/create-notebook`
- Any request to **review code** → `/code-review`
- Any request to **write tests** → `/create-unit-tests` (one notebook) or `/create-integration-tests` (full initiative)

Before generating any entity or transform, always read `agents/skills/understand-platform-framework/SKILL.md` — it is the authoritative layer architecture and framework API reference.

## Data platform layer overview

| Layer | Folder | Locator pattern |
|---|---|---|
| Raw | `databricks/1-raw/<sys>/` | `raw/<product>/<sys>/int/<entity>` |
| Staging | `databricks/3-staging/<sys>/` | `staging/<product>/<sys>/int/<entity>` |
| Enriched | `databricks/4-enriched/<sys>/` | `enriched/<product>/int/<sys>_<entity>` |
| Curated | `databricks/5-curated/<module>/` | `curated/<product>/<module>/<entity>` |

Note: enriched locator places `<sys>` **after** `int`, unlike raw and staging.

## Key rules (all layers)

- Every notebook starts with `%run "../../_platform_app/platform_init"` (depth varies by layer)
- PEP 723 block is injected into the file header — never as a visible cell
- Never hard-code environment names — always use `lake_connection.product_environment`
- Always read the existing `Entity(...)` constructor to get `entity_name`, `entity_locator`, `source_system` — never infer from folder or file names

## Demo project

A self-contained demo is in `demo/` — includes a mock `pltdata` framework package and skeleton notebooks for all four layers. Use it to run skills locally without a Databricks cluster.

## Naming notes for adopters

- **`cq` product code**: all entity locator examples use `cq` as the product segment (e.g. `raw/cq/<sys>/int/<entity>`). Replace `cq` with your own product identifier throughout.
- **`PltDebugTransform` / `pltdata`**: the `Plt` prefix and `pltdata` package name are the platform framework's API names used throughout this repo. The demo mock package mirrors these names exactly so demo notebooks run with the same imports as production.
