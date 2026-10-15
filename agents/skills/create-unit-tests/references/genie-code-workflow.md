# Claude Code Workflow

Use this reference only when creating or updating the repository's pytest unit tests from Claude Code in Databricks. The common test structure, fixture rules, mocks, and assertions remain defined in `implementation-guide.md`.

## Preserve the Repository Test Contract

Generate ordinary pytest modules under `databricks/tests/unit/`. Do not generate Databricks test notebooks, `%run` cells, top-level assertion cells, or `dbutils`-based path setup. Do not add workspace paths to generated imports. The PR pipeline compiles the checked-out branch and resolves normal `integration.bin` imports from the repository.

## Detect the Workspace Context

Use available runtime evidence such as a `/Workspace` filesystem, Databricks runtime environment variables, or workspace tools. Do not ask the user to identify the environment when it can be detected. If the environment remains ambiguous, preserve the local pytest format and do not perform workspace mutations.

## Find a Compiled Reference

Search in this order:

1. The current Git folder or repository at `databricks/lib/integration-lib/integration/bin/`.
2. `/Workspace/Shared/release/int/databricks/lib/integration-lib/integration/bin/`.

The Shared directory is a read-only analysis fallback. Never create, modify, copy over, delete, or compile files there. Never include its path in generated tests, fixtures, pytest configuration, or `sys.path` statements.

Use an actual artifact to confirm the generated module name, transform function, decorator sources, positional source order, target entity, `export_type`, and runtime calls. Generated tests must still import through `integration.bin`.

## Check Freshness

Do not treat a Shared artifact as authoritative merely because its filename matches. Treat it as stale or unavailable when:

- The selected notebook is new.
- The notebook contains changes not represented by the deployed artifact.
- The target entity, version, decorator sources, function signature, or transformation logic differs.
- Correspondence between the notebook and Shared artifact cannot be established confidently.

Use repository status or diffs when available and compare the source notebook with the compiled reference. When correspondence cannot be established confidently, treat the Shared artifact as stale and run the repository compiler before generating the test.

## Handle New or Modified Notebooks

Do not use a missing or stale Shared artifact for a new or modified notebook, and do not deploy to Dev merely to obtain a compiled module. Tell the user which current artifact is missing, then run the repository compiler from the current Git folder root:

```text
python databricks/.azuredevops/scripts/run_compile_transform.py
```

The compiler processes all transforms and writes generated modules to the repository `databricks/lib/integration-lib/integration/bin/` directory. It must never write to `/Workspace/Shared/release`. After compilation, use the repository artifact to confirm the module/function name, direct source order, schemas, decorator configuration, and transformation behavior.

If compilation fails or does not create the expected repository artifact, stop and report the compiler result. Do not generate a test by guessing and do not redirect imports to a stale Shared module. Report compiler-generated file changes, but do not revert unrelated generated changes automatically.

## Unity Catalog Boundaries

For a direct `spark.table(...)` input, resolve a repository or Shared entity definition first. If none exists, Unity Catalog schema metadata may be inspected to construct synthetic data. Do not select production rows or use live table contents as fixtures.

Test execution must remain isolated: generated tests route expected table names to synthetic DataFrames and fail on any unexpected table access. User access and permissions do not make a live table read appropriate for a unit test.

## Do Not Execute Pytest In Claude Code

Compilation and pytest execution are separate operations. Claude Code may run the repository compiler and generate pytest modules and fixtures, but it must never execute pytest in the Databricks workspace, including `pytest --collect-only`.

The repository `conftest.py` intentionally creates a local Spark session for local and CI execution. Do not create, replace, or modify `conftest.py`, `pytest.ini`, runtime stubs, test utilities, Spark master settings, or Spark-session configuration to make the tests run on an active Databricks cluster. Do not generate an alternate Databricks-only test harness.

After generation, defer execution to either:

- A developer running the narrow pytest target locally.
- The PR unit-test pipeline, which compiles the checked-out branch and runs pytest before deployment.

## Report Verification Honestly

For an unchanged notebook inspected from Shared, identify Shared as a read-only generation reference, not a generated test dependency.

After generating a test in Claude Code, report:

```text
The unit test and synthetic fixtures were generated with portable
integration.bin imports using the current compiled artifact. The generated
test does not depend on an absolute workspace or Shared path.

Pytest was not executed in Claude Code because the repository unit-test
framework creates a local Spark session and is intended for local or CI
execution. Run the target test locally, or use the PR unit-test pipeline,
which compiles the checked-out branch and executes pytest before deployment.
```

Report repository compilation separately when it ran. Never claim test success based on reading source code, inspecting a Shared artifact, compiling files, or generating test files.
