# Production Workflow Verification

## Find the Candidate Workflow

Open `.config/module.json` and find workflow entries whose `entities` contain the selected source, curated target, or serving target. Convert the workflow name to the deployed form:

```text
<product> int Workflow - <workflow_name>_int
```

Treat this as candidate discovery, not proof of final task membership.

## Match Evidence to the Current Code

Check that job settings, generated definitions, and graphs correspond to the production code being tested. Use deployed settings for the matching release when available. For new or modified code not deployed yet, use current generated evidence; an older deployed job cannot prove or disprove the new task path.

Keep compiled-artifact availability, workflow wiring, deployment readiness, and test execution separate. Compilation can establish current function definitions without establishing the other three. Inspect evidence read-only; do not deploy or trigger a job to obtain it.

## Map Source Definitions to Runtime Tasks

For every claimed layer:

1. Locate the production transformation source.
2. Identify the compiled function name.
3. Confirm a current compiled artifact exists using the repository, matching Shared reference, or packaged artifact. Follow the Claude Code reference for missing or stale artifacts.
4. Locate the task in a matching deployed job or current generated workflow definition that invokes the function through the platform execution framework, normally `_platform_app/run/execute_function.py`.
5. Inspect task dependencies.

Never execute a transformation source notebook directly as a substitute.

## Prove Same-Workflow Serving

Classify serving as part of the same workflow only when current evidence for the configured `target_job_name` contains:

- the compiled task that produces the selected curated entity
- the compiled task that produces the selected serving entity
- a direct or transitive dependency path from the curated task to the serving task

Both tasks appearing in a job without the required ordering is insufficient.

Among evidence that represents the current code, use this priority:

1. Deployed Databricks job settings and task DAG
2. Generated deployment job definition
3. Generated platform workflow graph
4. `.config/module.json` workflow configuration
5. Naming or directory inference

Only the first three can substantiate workflow coverage. `generateDirection`, entity membership, and naming are hints.

When current generated evidence establishes the ordered path before deployment, distinguish verified generated wiring from pending deployment. Neither establishes a passing test result. Do not invent workflow tasks for views.

## Classify Confirmed Workflow Limits

Use scenario 3 only when current evidence confirms that:

- the serving task belongs to another workflow
- the serving task is absent from the configured workflow
- the tasks exist but have no required dependency path

Stop validation at the highest boundary executed by the configured job. Report the serving entity, compiled function, candidate workflow, evidence inspected, and reason for exclusion.

The shared runner invokes one `target_job_name`. Never change that contract as part of creating or updating an initiative test. A multi-workflow design requires a separate platform-level task and team approval. Report the confirmed limitation and highest supportable boundary.

## Author While Verification Is Pending

If deployed or generated membership for the current code is unavailable, mark the affected path `UNVERIFIED` and leave its serving scenario classification pending. Do not classify it as separate or silently lower the requested boundary merely because the new code is not deployed.

Setup and validation may be drafted from current production definitions where schemas and expected behavior are known. Record the candidate workflow, intended boundary, compiled functions, and exact task or dependency evidence still needed. Do not invent missing task names, claim verified workflow coverage, or describe the test as ready for execution.

Deployment readiness remains pending until the corresponding deployed job contains the required ordered path and the production artifacts, test notebooks, and configuration are deployed. Report this in the coverage manifest and handoff; do not add verification fields to the suite config schema. Preserve the intended fatal assertions and existing valid coverage while the wiring is unverified.
