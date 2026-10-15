# Data Platform Skills

This directory contains **Claude Code skills** — packaged instruction sets that guide Claude to generate, review, or test data platform notebooks and pipelines.

> **Framework reference:** See [`understand-platform-framework/SKILL.md`](understand-platform-framework/SKILL.md) for the full data platform layer architecture, notebook file format, and platform framework reference. Skills read that file when generating entities.

---

## What is a Skill?

A skill is a directory loaded by Claude Code that tells Claude exactly what to do for a specific task type. When you invoke a skill, Claude reads its `SKILL.md` (behavior rules) and `docs.md` (code templates and reference patterns) and generates correct, framework-compliant output.

Skills encode the patterns, rules, and constraints of the data platform framework so you don't have to explain them every time.

---

## Invoking a Skill

In Claude Code, invoke a skill by typing:

```
/create-notebook
/code-review
/create-integration-tests
```

Or describe what you want — the routing guide in `ROUTING.md` helps Claude pick the right skill.

---

## Skill File Structure

Each skill follows this layout:

```
<skill-name>/
├── SKILL.md      — behavior: scope, required inputs, workflow, done criteria
├── docs.md       — code templates and framework reference patterns
└── examples/     — real working notebook samples (optional)
```

**SKILL.md** answers: *What should Claude do?* It defines the scope guard, the 4-step required-input workflow (Extract → Ask → Discover → Generate), and the done criteria Claude checks before reporting completion.

**docs.md** answers: *How does the code look?* It contains entity constructor templates, PltDebugTransform patterns, cross-layer wiring snippets, and framework rules.

---

## Choosing the Right Skill

| What you want to create | Skill |
|---|---|
| Any transform notebook — raw, staging, enriched, or curated | `create-notebook` |
| Two or more layers at once | `create-notebook` |
| Review code / notebook / PR | `code-review` |
| Integration tests | `create-integration-tests` |
| Unit tests for a transform notebook | `create-unit-tests` |

**Disambiguation:**
- "Create a notebook for X" → use `create-notebook`; it will ask which layer if not stated
- "Create a pipeline for X" → use `create-notebook`; it handles full and partial multi-layer pipelines
- "Add a column / fix a bug" → use `create-notebook` and specify the target layer

---

## Skills Reference

### `create-notebook`

Generates one or more transform notebooks — raw ingestion, staging transform, enriched transform, or curated transform. Handles single layers and full multi-layer pipelines.

**When to use:** any request to create, scaffold, or modify notebooks in `databricks/1-raw/`, `databricks/3-staging/`, `databricks/4-enriched/`, or `databricks/5-curated/`.

| Layer | Output path |
|---|---|
| Raw | `databricks/1-raw/<source_system>/transform_<source_system>_<entity_name>.py` |
| Staging | `databricks/3-staging/<source_system>/transform_<entity_name>.py` |
| Enriched | `databricks/4-enriched/<source_system>/transform_<entity_name>.py` |
| Curated | `databricks/5-curated/<module>/transform_<entity_name>.py` |

**Key rules (all layers):**
- Every notebook includes the PEP 723 serverless block with `base_environment = "/Workspace/Shared/environment/int-default-env.yml"`
- Never hard-code environment names — use `lake_connection.product_environment`
- Always extract `entity_name`, `entity_locator`, `source_system` from existing `Entity(...)` constructors; never infer from folder/file names

**Reference files:** `SKILL.md`, `references/<layer>.md`, `references/entity-definition.md`, `references/cross-layer.md` (multi-layer)

---

### `code-review`

Reviews Databricks Python and PySpark code across 43 checklist sections covering correctness, security, reliability, performance, cost, and maintainability.

**When to use:** reviewing any notebook, PR, or code change in the repository.

**Review priorities (in order):**
1. Correctness
2. Security
3. Reliability
4. Performance
5. Cost
6. Maintainability

**Severity levels:** Critical → High → Medium → Low

**Finding format:**

| Issue | Severity | Recommendation | Example Fix |
|---|---|---|---|
| Description of problem | High | What to do instead | Corrected code snippet |

**Key principles:**
- Understand before optimizing
- Prefer evidence over assumptions
- Never invent performance numbers, execution plans, or line numbers
- Do not expose detected secrets in output

**Reference files:** `SKILL.md` (9 lines), `docs.md` (full 43-section checklist)

---

### `create-integration-tests`

Creates config-driven integration tests in `databricks/tests/integration/`. Modular structure — references a `references/` subdirectory with separate docs for test design, runner config, workflow verification, and notebook patterns.

**When to use:** a new initiative needs end-to-end proof that its production workflow runs correctly.

**What it creates:**

```
databricks/tests/integration/<initiative>/
  setup_<initiative>.py
  validate_<initiative>.py
```

Plus a new entry in `databricks/tests/integration/config/integration_tests.json`.

**Key concepts:**

| Concept | Rule |
|---|---|
| Test type | `controlled_test_data` (Claude inserts synthetic rows) or `observational` (reads existing data) |
| Test boundary | `raw`, `staging`, `enriched`, `curated` |
| Environment | Controlled = DEV only; Observational = DEV + QUA |
| Workflow | Triggered via `target_job_name`; never call notebooks directly |
| Platform invariant | Always exercise the compiled function → deployed workflow task path |

**Reference files:** `SKILL.md`, `references/` (for `create-integration-tests`)

---

### `create-unit-tests`

Creates an isolated pytest module for one transform notebook or integration-lib module. Uses compiled `integration.bin` artifacts, not the source notebook directly. Compatible with the PR unit-test pipeline; does not run tests in Claude Code.

**When to use:** generating unit tests for a single transform notebook or library module in `databricks/lib/integration-lib/integration/`.

**Key concepts:**

| Concept | Rule |
|---|---|
| One target per request | Never expands to initiative-wide coverage |
| Compiled-notebook mode | For transforms under `1-raw`, `3-staging`, `4-enriched`, `5-curated` |
| Library-function mode | For modules under `databricks/lib/integration-lib/integration/` |
| Claude Code | Defers pytest execution to local dev or PR pipeline — never runs `pytest` in Claude Code |

**Reference files:** `SKILL.md`, `references/implementation-guide.md`, `references/genie-code-workflow.md`

---

## Skill Maintenance

### Updating a skill

1. For behavior changes (scope, workflow steps, done criteria) → edit the skill's `SKILL.md`
2. For code pattern changes (entity constructor, PltDebugTransform, template fixes) → edit the skill's `references/<file>.md`
3. Keep `SKILL.md` as behavior-only; keep reference files as template-only
4. If the platform framework API changes, update `understand-platform-framework/SKILL.md` first — then check every skill's `references/*.md` for inline copies of the same pattern

5. After editing, update `ROUTING.md` quick-selection and layer map if skill scope changed

### Adding a new skill

1. Create a folder under `agents/skills/<skill-name>/`
2. Write `SKILL.md` with: frontmatter (`name`, `description`), Scope Guard, Goal, Required Inputs (4-step workflow), Creation Workflow, Done Criteria
3. Write `docs.md` with code templates referenced by SKILL.md; link to `understand-platform-framework/SKILL.md` for API details rather than duplicating them
4. Add the skill to `ROUTING.md` quick-selection table and layer map

---

## File Map

```
agents/skills/
├── README.md                          ← this file (skill index and usage guide)
├── EXAMPLES.md                        ← concrete walk-throughs for all skills
├── ROUTING.md                          ← routing guide for Claude
│
├── create-notebook/                   ← all batch notebook generation (raw → staging → enriched → curated)
│   ├── SKILL.md                       ← routing, input collection, done criteria for all layers
│   └── references/
│       ├── entity-definition.md       ← shared Entity/Attribute constructor rules (all layers)
│       ├── raw.md                     ← raw ingestion code templates
│       ├── staging.md                 ← staging transform code templates
│       ├── enriched.md                ← enriched transform code templates
│       ├── curated.md                 ← curated transform code templates
│       ├── cross-layer.md             ← cross-layer wiring (lifecycle handlers, source locators)
│       └── examples/
│           └── transform_raw_example.py  ← complete working raw notebook example
│
├── code-review/
│   ├── SKILL.md          ← 9-line entry point
│   └── docs.md           ← 43-section full checklist (~1100 lines)
│
├── create-integration-tests/
│   ├── SKILL.md
│   └── references/
│
├── create-unit-tests/
│   ├── SKILL.md
│   └── references/
│
└── understand-platform-framework/
    └── SKILL.md                       ← platform framework API reference (Layer, AttrType, Entity, Drl, etc.)
```
