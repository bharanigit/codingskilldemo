# How to Use Data Platform Skills in Claude Code

This guide covers the skills used to create and test data platform notebooks in the repository:

| Skill | Purpose |
|---|---|
| `create-notebook` | Generate a raw / staging / enriched / curated notebook |
| `create-unit-tests` | Generate a Databricks notebook unit test for one transform |
| `create-integration-tests` | Generate end-to-end integration tests for a full initiative |

---

## Prerequisites

- Access to the project repo synced in Databricks Repos
- A cluster attached to the notebook (for unit/integration tests)
- `compile_transforms` must have been run at least once before creating unit tests

---

## How to Invoke a Skill in Claude Code

Invoke skills using `/skill-name` syntax in Claude Code CLI. When working inside Databricks:

**Steps for any skill:**

1. Open the skill's `SKILL.md` file in the Databricks workspace:
   ```
   /Workspace/<repo>/agents/skills/<skill-name>/SKILL.md
   ```
2. Copy everything below the `---` frontmatter block (from the `# Create ...` heading to the end)
3. Open a Claude Code session
4. Paste the copied content followed by your request:

   ```
   Follow these instructions exactly:

   [paste SKILL.md content here]

   ---
   <your request, e.g. "Create a unit test for databricks/4-enriched/mockapi/transform_employees.py">
   ```

5. If Claude gets stuck on a step, paste just that section of SKILL.md and say:
   > "Follow only this step now."

---

## create-notebook

**What it does:** Generates one or more platform transform notebooks (raw → staging → enriched → curated) with correct entity definitions, lifecycle handlers, and source wiring.

### Steps

1. **Paste the skill** from `agents/skills/create-notebook/SKILL.md`

2. **State your request:**
   ```
   Create an enriched transform for the mockapi employees entity.
   Source system: mockapi
   Source: staging/mockapi/employees
   Primary key: id
   ```

3. **Claude will ask for:**
   - Entity name and source system
   - Attribute list with types
   - Primary key columns
   - Merge strategy (for curated)

4. **Review the generated notebook** — check entity name, locator, attributes, and lifecycle handler

5. **Register the entity** by running the Deploy cell in the notebook

### Tips

- Specify the layer explicitly (`enriched`, `curated`, etc.) to avoid Claude asking
- For multi-layer (e.g., staging + enriched together), say "Create staging and enriched notebooks for..."
- Do **not** use `workspace-base-environments/...` paths in the `base_environment` field — the correct path is `/Workspace/Shared/environment/int-default-env.yml`

---

## create-unit-tests

**What it does:** Generates a Databricks notebook unit test for one production transform. The test loads fixtures from CSV, runs the compiled transform function with `run_unittest=True`, and asserts schema and behavior.

### Steps

1. **Compile the transforms** — open and run `databricks/_platform_app/deploy/compile_transforms` notebook (Run all). This writes compiled modules to `databricks/lib/integration-lib/integration/bin/`

2. **Paste the skill** from `agents/skills/create-unit-tests/SKILL.md`

3. **State your request:**
   ```
   Create a unit test for:
   databricks/4-enriched/mockapi/transform_employees.py
   ```

4. **Claude will:**
   - Verify the compiled module exists (e.g., `t_transform_employees_enriched_int`)
   - Read the source notebook to understand entity attributes and transform logic
   - Create a CSV fixture under `databricks/tests/data/<layer>/<source_system>/`
   - Create the test notebook under `databricks/tests/unit/<layer>/<source_system>/test_<name>.py`

5. **Run the test notebook** — open it in Databricks and click **Run all**, or ask Claude to run it in a cell:
   ```python
   dbutils.notebook.run("/Workspace/.../databricks/tests/unit/4-enriched/mockapi/test_transform_employees", 300)
   ```

### Generated notebook structure

```
cmd 1  — %run "../../../../_platform_app/platform_init"
cmd 2  — Imports (namespace fix + compiled module imports)
cmd 3  — Load CSV fixture and run transform (with file: prefix)
cmd 4+ — One test cell per behavior (schema, cast, null, dedup, etc.)
```

### Common issues

| Error | Fix |
|---|---|
| `ModuleNotFoundError: databricks.tests` | The namespace fix in cmd 2 must include `_databricks_pkg.__path__.insert(0, _databricks_repo_dir)` — see implementation-guide.md |
| `PATH_NOT_FOUND` for CSV | Use `f"file:{_csv_path}"` prefix in `spark.read.csv()` |
| `.count()` with parentheses fails | Use `.count` without parentheses (it's a cached property on PltDataFrame) |
| `workspace-base-environments/...` in base_environment | Replace with `/Workspace/Shared/environment/int-default-env.yml` |

---

## create-integration-tests

**What it does:** Generates a `setup_<initiative>.py` and `validate_<initiative>.py` notebook pair that tests a full initiative end-to-end, then registers it in `integration_tests.json`.

### Steps

1. **Paste the skill** from `agents/skills/create-integration-tests/SKILL.md`

2. **Resolve the repo root** — run this in a Claude Code cell first so Claude can read workspace files:
   ```python
   _nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
   _parts = _nb_path.split('/')
   if 'Repos' in _parts:
       _repos_idx = _parts.index('Repos')
       _repo_root = '/Workspace/' + '/'.join(_parts[1:_repos_idx + 3])
   else:
       _databricks_idx = next(i for i, p in enumerate(_parts) if p == 'databricks')
       _repo_root = '/Workspace/' + '/'.join(_parts[1:_databricks_idx])
   print(_repo_root)
   ```

3. **State your request:**
   ```
   Create integration tests for the mockapi initiative.
   Target notebook: databricks/4-enriched/mockapi/transform_employees.py
   Test type: observational
   ```

4. **Claude will:**
   - Read `.config/module.json` to find the workflow name
   - Inspect existing integration tests as reference
   - Create `databricks/tests/integration/<initiative>/setup_<initiative>.py`
   - Create `databricks/tests/integration/<initiative>/validate_<initiative>.py`
   - Add an entry to `integration_tests.json`
   - Validate the JSON in a cell

5. **Validate the JSON** — Claude runs this automatically, or run manually:
   ```python
   import json
   with open(f"{_repo_root}/databricks/tests/integration/config/integration_tests.json") as f:
       cfg = json.load(f)
   print(f"Valid JSON — {len(cfg['tests'])} entries")
   ```

### Test types

| Type | When to use | Environments |
|---|---|---|
| `observational` | Source is externally owned or mutation is unsafe | DEV + QUA |
| `controlled_test_data` | CQ owns the anchor and can insert synthetic rows | DEV only |

### Manual testing (before CI)

To test a single initiative manually without the full runner:

1. Open `setup_<initiative>.py` → Run all → copy the `Notebook exited: {...}` JSON
2. Open `validate_<initiative>.py` → paste the JSON into the `setup_result` widget → press Enter → Run all

To run via the runner with an initiative filter:

1. Open `databricks/tests/integration/common/run_integration_suite`
2. Set the `initiative` widget to your initiative name (e.g., `mockapi`)
3. Click Run all

### In production

The runner is triggered automatically by Azure DevOps CI after each deployment. No manual intervention is needed.

---

## File Locations Reference

| Resource | Path |
|---|---|
| Skill definitions | `agents/skills/<skill-name>/SKILL.md` |
| Integration API clients | `databricks/lib/integration-lib/integration/functions/<sys>_api.py` |
| Unit test notebooks | `databricks/tests/unit/<layer>/<source_system>/test_<name>.py` |
| Unit test CSV fixtures | `databricks/tests/data/<layer>/<source_system>/<sys>_<entity>.csv` |
| Integration test notebooks | `databricks/tests/integration/<initiative>/` |
| Integration test config | `databricks/tests/integration/config/integration_tests.json` |
| Compiled transform modules | `databricks/lib/integration-lib/integration/bin/` |
| Suite runner | `databricks/tests/integration/common/run_integration_suite.py` |
| Module workflow config | `.config/module.json` |
