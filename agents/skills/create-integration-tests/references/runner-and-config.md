# Suite Runner and Configuration

## Authoring and Deployment Handoff

The agent creates or updates repository files and checks them statically. All runner behavior below occurs during a developer-started integration pipeline run after deployment. Do not execute test notebooks, trigger workflows, launch the pipeline, or deploy files while authoring.

```text
author and statically check repository files
  -> deploy production changes, test notebooks, and configuration
  -> developer starts integration pipeline
  -> setup -> optional production workflow -> validation
```

New or updated test notebooks and `integration_tests.json` must be deployed even when the production transforms are already in DEV. The runner's default config is `/Workspace/Shared/release/int/databricks/tests/integration/config/integration_tests.json`; editing the Git-folder copy does not update the deployed suite.

Before the developer runs the pipeline, the corresponding production functions and runtime libraries, configured job and dependencies, setup/validation notebooks, and config must be deployed. Report missing evidence as pending readiness according to `workflow-verification.md`. Do not add an automatic post-deployment trigger or new config fields.

Preserve `/Shared/release/int/databricks/...` notebook paths in config entries for pipeline execution. `/Workspace/Shared/...` is the filesystem path used to inspect deployed files. Shared remains read-only during authoring.

## Runner Contract

Treat this contract as a shared platform standard, not an initiative-specific design choice.

The runner executes each selected config entry in this order:

```text
setup notebook -> optional production workflow -> required validation notebook
```

It passes `initiative`, `test_type`, `environment`, `target_job_name`, `run_target_job`, `required_boundary`, and stringified custom parameters. A non-empty setup result is passed to validation as `setup_result`.

Controlled tests run the target job by default. Observational tests skip it by default. Add `run_target_job` only for an intentional override.

The runner executes initiatives sequentially. A per-initiative exception skips that initiative's remaining stages, records the failure, and continues with later initiatives. It prints a consolidated summary and fails the suite at the end when failures exist. Configuration, environment, or test-selection failures occur before the per-initiative loop and stop the suite immediately.

The runner supports one production workflow invocation per config entry. Each entry has exactly one setup notebook path and one validation notebook path. Multiple environment entries for the same initiative may reuse the same notebook pair.

While adding an initiative test, do not modify:

- `run_integration_suite.py`
- the shared integration-suite pipeline
- the `integration_tests.json` schema
- the setup/workflow/validation execution sequence
- the one-workflow invocation limit

Do not add arrays of setup notebooks, workflow names, or validation notebooks. Do not add `target_notebooks` or direct source-notebook execution.

Implement compatible initiative scenarios inside the one setup and validation pair. If required coverage cannot fit, report why, the highest supportable boundary, and the separate platform-level change that would require team approval. Never redesign the shared suite as an incidental part of initiative work.

## Canonical Values

- `test_type`: `controlled_test_data`, `observational`
- `allowed_envs`: `dev`, `qua`
- `required_boundary`: `raw`, `staging`, `enriched`, `curated`, `curated_ext`, `workspace`

Use JSON booleans. Use positive integer timeouts. Use a non-empty parameters object only when custom arguments are needed.

## Config Template

```json
{
  "initiative": "example",
  "test_type": "controlled_test_data",
  "allowed_envs": ["dev"],
  "enabled": true,
  "required_boundary": "curated",
  "target_job_name": "<product> int Workflow - example_int",
  "setup_notebook": "/Shared/release/int/databricks/tests/integration/example/setup_example",
  "validate_notebook": "/Shared/release/int/databricks/tests/integration/example/validate_example",
  "setup_timeout_seconds": 300,
  "target_timeout_seconds": 6000,
  "validate_timeout_seconds": 600
}
```

Omit `run_target_job` for normal entries. Do not add `target_notebooks` for platform transformations.

Validate after editing by running in a Claude Code cell:

```python
import json
with open(f"{_repo_root}/databricks/tests/integration/config/integration_tests.json") as _f:
    _cfg = json.load(_f)
print(f"Valid JSON — {len(_cfg['tests'])} entries")
```

(`_repo_root` is the value computed in the "Inspect the Repository" step in SKILL.md.)
