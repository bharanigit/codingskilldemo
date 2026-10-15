# Claude Code Workflow

Use this reference when authoring integration tests in Claude Code in Databricks. Artifact freshness and the repository compiler fallback also apply to local authoring. Keep the shared suite contract and full-initiative coverage rules defined in the main skill.

## Author in the Current Repository

Identify the current Git folder or repository from the available workspace context and locate its root. Read production definitions, existing integration tests, and `.config/module.json` there. Write the setup and validation notebooks and configuration changes to that repository, including when the production changes are not deployed yet.

Keep the existing Databricks notebook format and runner parameters. Do not convert integration tests to pytest or invoke compiled transforms directly with `run_unittest=True`. The pipeline exercises production behavior through the configured workflow.

## Resolve Current Compiled References

For every production transform needed to design the initiative's coverage, search in this order:

1. `databricks/lib/integration-lib/integration/bin/` under the current repository root.
2. `/Workspace/Shared/release/int/databricks/lib/integration-lib/integration/bin/` as a read-only fallback.

At either location, compare the artifact with the current production definition before using it. Inspect the actual generated module and function names, source and target entities, schemas, decorator configuration, transformation logic, and relevant runtime calls. Repository status or diffs can help establish correspondence; a matching filename alone cannot.

Treat an artifact as missing or stale when there is no corresponding artifact for a production notebook, its relevant definitions or behavior differ, or correspondence cannot be established confidently. An unchanged deployed transform may use a matching Shared reference. For new or modified code not represented by the deployment, use a current repository artifact. A newly compiled artifact that matches the source is valid even when that source is not deployed. Record the origin of the references used.

Shared is read-only during authoring. Never create, modify, delete, overwrite, or compile files there. Preserve the existing `/Shared/release/...` notebook paths in suite configuration; they are the intended pipeline runtime paths. Use `/Workspace/Shared/...` for filesystem inspection. Do not add Shared `sys.path` changes or execute Shared transforms to verify them.

## Compile When No Current Reference Exists

Creating or editing integration tests alone does not require compilation. Compile when a required production artifact is missing or stale in the repository and no matching Shared artifact is available.

Identify the transforms that need current artifacts, then run the existing compiler from the repository root:

```text
python databricks/.azuredevops/scripts/run_compile_transform.py
```

The compiler processes all transforms and writes generated modules to the repository `databricks/lib/integration-lib/integration/bin/` directory. Do not redirect its output to Shared or deploy merely to obtain a compiled reference.

After compilation, inspect the expected generated modules and function definitions and confirm that they represent the current production definitions. Do not invoke transforms as a verification step. If compilation fails or the required artifacts are still missing or stale, stop dependent test generation and report the result. Do not guess names, use stale artifacts, or bypass production execution with direct source-notebook calls.

Report compiler-generated changes without automatically reverting unrelated generated files. Compilation does not deploy functions, update production jobs, or demonstrate test success.

## Keep Workflow Evidence Separate

Use `workflow-verification.md` to map compiled functions to tasks and dependencies for the current code. Repository compilation alone does not prove workflow membership. A deployed job from an older release cannot establish the execution path for new code.

Use current generated job definitions or workflow graphs when deployment is pending. If wiring cannot yet be verified, record the affected paths as `UNVERIFIED`, identify the intended boundary and missing evidence, and report deployment readiness as pending. Draft tests only where schemas and expected behavior are known; do not invent workflow tasks or claim verified coverage.

## Verify Statically and Hand Off

Parse the generated Python source and JSON without executing or importing the setup, validation, or runner notebooks. Review config values, artifact references, scenario coverage, fixture isolation, and fatal assertions against the repository contract.

Do not run pytest or execute integration-test notebook cells, setup, validation, the suite runner, production workflows, or the integration pipeline as part of authoring. Do not insert fixtures or perform cleanup against live tables to try the tests. Keep fixture creation and validation in the generated notebooks for pipeline execution.

Follow the deployment handoff in `runner-and-config.md`. Report the changed files and coverage, compiled artifacts inspected, compilation performed or skipped, static verification, and remaining deployment or workflow evidence. State explicitly that integration tests were not executed. The developer starts the pipeline after the production changes, test notebooks, and configuration are deployed.
