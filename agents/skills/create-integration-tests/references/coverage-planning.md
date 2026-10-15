# Full-Initiative Coverage Planning

## Inventory Every Path

Default to full-initiative discovery. Inventory every production transform, entity, SQL view, export, external adapter, compiled function, and workflow association related to the requested initiative.

Treat a production path as the coverage unit rather than a filename. Supporting logs, external ingestion adapters, independent curated roots, shared lookups, and serving SQL views may require different evidence even when their names share the initiative.

Build a manifest containing:

- path or entity
- source and target layers
- compiled function or deployed artifact
- configured workflow and membership evidence
- ownership and safe anchor
- scenario identity
- testability disposition
- validation checkpoint
- exclusion or uncertainty reason

Assign exactly one disposition:

- `CONTROLLED`: setup can create deterministic data at a safe CQ-owned anchor.
- `OBSERVATIONAL`: setup must select stable existing data without mutation.
- `EXCLUDED`: the path is outside the suite boundary or unsafe to exercise.
- `UNVERIFIED`: required ownership, lineage, deployment, or workflow evidence is unavailable.

Do not silently omit a discovered path and do not equate task execution with validated behavior.

## Maintain Coverage as the Initiative Changes

Compare the current initiative inventory with its existing setup notebook, validation notebook, and config entries before editing. Full-initiative coverage remains the goal even when the request starts with one new or modified production notebook.

| Development change | Integration-test work |
| --- | --- |
| Existing production notebook modified | Preserve valid scenarios; update affected fixtures, expectations, and downstream assertions; add scenarios for new behavior and supported gaps. |
| New production notebook added | Extend the existing pair for the new path, its dependencies, downstream results, and interactions with existing paths. |
| New initiative or no existing integration tests | Create one pair and its config entries for all currently implemented, supported paths. |

Preserve valid coverage for unchanged paths. Extend the existing notebooks and matching environment entries instead of creating duplicate pairs or registrations. Update assertions to reflect intended production behavior; do not remove or weaken them merely to accommodate a change. Add independent and combined scenarios where interactions require them.

Fill safely testable gaps that fit the single configured workflow and test mode, including gaps found in existing coverage. Account for the remaining paths with explicit dispositions and reasons. Cover implemented development; do not invent future notebooks or requirements.

When workflow evidence for new development is pending, keep the path in the manifest as `UNVERIFIED`, record its intended scenario and boundary, and follow `workflow-verification.md`. Pending deployment is not evidence that a path belongs to a separate workflow.

## Fit Coverage Into the Fixed Contract

Use one setup notebook, one optional production workflow invocation, and one validation notebook per config entry. Use one setup and validation notebook pair per initiative, reusing it across environment-specific config entries when needed.

Place all compatible scenarios for the configured workflow and test mode inside that pair. Return one `setup_result` object with a `scenarios` map. Do not introduce extra setup or validation notebook fields, multiple workflow names, ordered jobs, or runner changes.

If a path belongs to a separate workflow, stop at the highest boundary executed by the configured workflow and report the separate path. If the requested result cannot be honestly represented, report that limitation instead of changing the suite architecture.

## Design Independent and Combined Scenarios

For multi-input transformations, prefer a distinct unique identity per input path so one path cannot mask another. Validate null preservation and mapping behavior independently.

Add a shared-identity scenario when production logic combines inputs through joins, unions, coalescing, deduplication, precedence, or aggregation. A combined scenario complements rather than replaces independent path coverage.

Reuse stable read-only lookup rows inside a controlled scenario when ownership prevents mutation. This does not make the whole scenario observational. Treat an independent historical-data check as observational and do not claim current-run propagation from it.

## Report Coverage

In the authoring response, distinguish:

- scenarios designed to prove controlled current-run propagation
- scenarios designed for observational coverage
- workflow tasks with no corresponding validation assertions
- excluded external adapters or systems
- separate workflows
- unverified production wiring

Summarize coverage preserved, updated, added, and still unsupported or unverified. These are statements about test design. Report executed or passed coverage only when actual pipeline results are supplied; this skill does not execute the tests.
