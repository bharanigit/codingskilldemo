# Setup and Validation Notebook Patterns

## Databricks Notebook Format

Every setup and validation file must be a valid Databricks notebook regardless of the `.py` extension. Separate cells with `# COMMAND ----------`.

**Setup notebook** — include `environment_version = "5"` in the script block. Omit `base_environment`; the workspace default now covers it:

```python
# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# Integration Test - <initiative> - Setup Context
# <one-line description>

import json

from pltdata import Drl, LakeConnectFactory
from pltdata.schema import Layer
from pyspark.sql import functions as F

# COMMAND ----------

def resolve_table(...):
    ...

def require_first(df, scenario: str, order_columns: list[str]):
    rows = df.orderBy(*order_columns).limit(1).collect()
    assert rows, f"[FAIL] {scenario} | no stable source/target pair was found"
    return rows[0]

def my_scenario() -> dict:
    ...

# COMMAND ----------

print("[START] setup_<initiative> | mode=observational | scope=...")

scenarios = {
    "scenario_a": my_scenario(),
}

# Coverage metadata — logged but excluded from exit value to stay within
# widget parameter size limits used by validate_<initiative>.
coverage = {
    "scenario_a": {"disposition": "OBSERVATIONAL", "entities": [...], "reason": "..."},
}
print(f"[INFO] Coverage: {json.dumps(coverage, default=str)}")

context = {
    "initiative": "<initiative>",
    "mode": "observational",
    "scenarios": scenarios,
}
setup_result = json.dumps(context, default=str)
print(f"[OK] <initiative> consolidated context ({len(setup_result)} chars): {setup_result}")
dbutils.notebook.exit(setup_result)  # noqa: F821
```

**Validate notebook** — no `# /// script` block:

```python
# Databricks notebook source
# Integration Test - <initiative> - Consolidated Validation
# Runs every scenario independently and reports all failures together.

import json

from pyspark.sql import functions as F

# COMMAND ----------

DATE_KEY_FIELDS: set[str] = set()  # add date-type key columns for this initiative

def filter_by_key(df, key: dict):
    result = df
    for field_name, expected_value in key.items():
        if expected_value is None:
            result = result.filter(F.col(field_name).isNull())
        elif field_name in DATE_KEY_FIELDS:
            # Date-type columns must be cast to string for comparison with stored string values
            result = result.filter(
                F.col(field_name).cast("string") == F.lit(str(expected_value))
            )
        else:
            result = result.filter(F.col(field_name) == F.lit(expected_value))
    return result

def normalized(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)

def assert_expected_fields(row, expected: dict, scenario_name: str) -> None:
    for field_name, expected_value in expected.items():
        actual_value = normalized(row[field_name])
        assert actual_value == expected_value, (
            f"[FAIL] {scenario_name} | {field_name} expected={expected_value!r} "
            f"got={actual_value!r}"
        )

def validate_scenario(scenario_name: str, scenario: dict) -> None:
    target_table = scenario["target_table"]
    key = scenario["key"]
    print(f"[SECTION] {scenario_name} | target={target_table} | key={key}")
    result = filter_by_key(spark.table(target_table), key)  # noqa: F821
    count = result.count()
    assert count == 1, (
        f"[FAIL] {scenario_name} | expected exactly one row for key={key}, found={count}"
    )
    assert_expected_fields(result.first(), scenario["expected"], scenario_name)

# COMMAND ----------

try:
    dbutils.widgets.text("setup_result", "")  # noqa: F821
    setup_result = dbutils.widgets.get("setup_result")  # noqa: F821
except Exception:
    setup_result = ""

assert setup_result, "[FAIL] setup_result is required. Run setup_<initiative> and copy its JSON output to the widget."
context = json.loads(setup_result)
scenarios = context.get("scenarios", {})

EXPECTED_SCENARIOS = {"scenario_a", "scenario_b"}
assert set(scenarios) == EXPECTED_SCENARIOS, (
    f"[FAIL] <initiative> scenarios expected={sorted(EXPECTED_SCENARIOS)} "
    f"got={sorted(scenarios)}"
)

print("[START] validate_<initiative> | scope=... | boundary=...")

results = {}
failures = []
for name in sorted(scenarios):
    try:
        validate_scenario(name, scenarios[name])
        results[name] = "PASS"
    except Exception as exc:
        results[name] = "FAIL"
        failures.append({"scenario": name, "error": str(exc)})
        print(f"[FAIL] {name} | {exc}")

print("\n[SUMMARY] <initiative>")
for name in sorted(results):
    print(f"[{results[name]}] {name}")

assert not failures, f"[FAIL] <initiative> scenario failures: {failures}"
print("[DONE] validate_<initiative> - all scenarios passed")
```

## Naming

Use lowercase snake case:

```text
databricks/tests/integration/<initiative>/
  setup_<initiative>.py
  validate_<initiative>.py
```

Prefer the same initiative value for the folder, filenames, and config entry.

## Coverage — Log Only, Do Not Exit With It

The `dbutils.notebook.exit()` value is passed as a widget parameter to the validate notebook. Widget parameters have a size limit. Keep coverage metadata out of the exit JSON — log it with `print` only:

```python
# RIGHT — coverage logged separately
coverage = {"path_a": {"disposition": "EXCLUDED", "reason": "..."}}
print(f"[INFO] Coverage: {json.dumps(coverage, default=str)}")

context = {"initiative": "...", "mode": "...", "scenarios": scenarios}
dbutils.notebook.exit(json.dumps(context, default=str))

# WRONG — coverage bloats the exit value
context = {"initiative": "...", "scenarios": scenarios, "coverage": coverage}
dbutils.notebook.exit(json.dumps(context, default=str))
```

## Serving Scenario Embedded in Parent Function

When a serving scenario is derived from the same join as a curated scenario, embed it in the curated scenario function and pop it out at the call site:

```python
def lead_opportunity_scenario() -> dict:
    ...
    return {
        "disposition": "OBSERVATIONAL",
        "source_table": source_table,
        "target_table": target_table,
        "key": {...},
        "expected": {...},
        "serving_scenario": {           # <-- embedded serving context
            "disposition": "OBSERVATIONAL",
            "source_table": target_table,
            "target_table": serving_table,
            "key": {"sub_business_unit": row["sub_business_unit"]},
            "expected": {"sub_business_unit_key": row["sub_business_unit_key"]},
        },
    }

# At call site — pop so scenarios dict stays flat
lead_opportunity = lead_opportunity_scenario()
generic_sub_business_unit = lead_opportunity.pop("serving_scenario")

scenarios = {
    "lead_opportunity": lead_opportunity,
    "generic_sub_business_unit_serving": generic_sub_business_unit,
}
```

## Date Key Fields in filter_by_key

Date-type columns (e.g., `at_date`, `visit_start_date`) stored as Spark `DateType` cannot be compared directly to a string literal from the JSON context. Define `DATE_KEY_FIELDS` at the top of the validate notebook and cast to string in `filter_by_key`:

```python
DATE_KEY_FIELDS = {"at_date", "visit_start_date"}
```

Add any date-type key column for the initiative to this set.

## Setup Notebook

The template above shows observational mode (read-only, no fixtures). For controlled mode (DEV, fixture-based), replace the scenario functions with fixture writers and apply the following rules:

- create a clearly identifiable test key (e.g. a reserved negative ID range)
- use a unique per-run marker for incremental serving or export flows
- insert or merge only into a safe CQ-owned anchor
- prepare owned lookup dependencies or select eligible stable read-only rows
- ensure incremental conditions include the fixture
- avoid duplicates across reruns

For observational setup: select a stable row using deterministic ordering and ensure it already exists at the intended validation checkpoint.

Use `require_first(df, scenario, order_columns)` to select a deterministic row and assert it exists.

Keep all initiative preparation in this notebook. Do not create additional setup notebook fields or change the runner.

## Validation Notebook

Read the runner widgets and parse `setup_result`. Resolve tables using repository DRL or entity patterns rather than guessed physical names.

Use fatal assertions for the declared boundary. Validate as applicable:

- record existence by the test identity
- critical field mappings
- joins and lookup resolution
- filters and deduplication
- target keys and identity maps
- incremental timestamps

Write failure messages that include the layer, entity, key, expected value, and actual value when possible.

Avoid fragile assertions based on full-table row counts, unordered results, exact current timestamps, or mutable production values.

Do not make an in-scope downstream assertion non-fatal. If a downstream system is intentionally excluded, state the boundary and reason instead.

For multiple scenarios, execute every scenario, collect its result, print one summary, and assert once at the end. A failure in one scenario must not prevent other scenario validations from reporting their status. Keep the single validation notebook required by the runner.
