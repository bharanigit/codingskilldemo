---
name: create-unit-tests
description: Create or update a pytest unit test for one Databricks transform notebook or integration-lib module. Uses compiled integration.bin artifacts. Excludes export transforms where export_type is not None. Does not run pytest — defers execution to local dev or the PR pipeline.
---

Read and follow `agents/skills/create-unit-tests/SKILL.md` exactly. That file is the complete skill definition.

Before generating, also read:
- `agents/skills/create-unit-tests/references/implementation-guide.md` — compiled-artifact patterns, fixture creation, assertion rules
- `agents/skills/create-unit-tests/references/genie-code-workflow.md` — artifact discovery and compilation fallback when running in Claude Code inside Databricks
