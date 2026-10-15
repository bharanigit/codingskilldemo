# Setup and Validation Script Patterns

## File Format

Setup and validation scripts are plain Python files (no Databricks notebook format, no `# COMMAND ----------`, no `dbutils`, no `spark.table()`). They run locally with the mock pltdata framework and a local PySpark session.

## Naming

```text
databricks/tests/integration/<initiative>/
  setup_<initiative>.py
  validate_<initiative>.py
```

## Setup Script

The setup script builds in-memory synthetic DataFrames and runs the full transformation chain. It exposes a `_result` dict that the runner passes to the validate script.

```python
"""
Integration Test — <initiative> — Setup
Builds synthetic source data, runs the transformation chain, and
exposes _result for the validate script.
"""
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../..")))

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

from pltdata import (
    Attribute, AttrType, Entity, EntityProperty, EntityType,
    Layer, Parameter, RetentionDuration,
)

# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------
spark = (
    SparkSession.builder
    .master("local[1]")
    .appName("integration-test-<initiative>-setup")
    .config("spark.sql.shuffle.partitions", "1")
    .getOrCreate()
)

print("[START] setup_<initiative> | mode=controlled | scope=<layers>")

# ---------------------------------------------------------------------------
# Entity definitions (verbatim from source notebooks)
# ---------------------------------------------------------------------------
# ... copy Entity(...) constructors here ...

# ---------------------------------------------------------------------------
# Transformation functions (extracted from source notebooks)
# ---------------------------------------------------------------------------
# ... copy apply_<layer>_transform functions here ...

# ---------------------------------------------------------------------------
# Scenario: <scenario_name>
# Unique test key: <TEST_KEY> — reserved for integration tests only
# ---------------------------------------------------------------------------
TEST_KEY = "INT_TEST_001"

def scenario_<name>() -> dict:
    """Build synthetic data, run the chain, collect results for validation."""
    # 1. Build source fixture
    source_data = spark.createDataFrame([
        (TEST_KEY, "Alice", "Smith", ...),
    ], schema=_RAW_SCHEMA)

    # 2. Run transformation chain
    staging_df  = apply_staging_transform(source_data)
    enriched_df = apply_enriched_transform(staging_df)
    curated_df  = apply_curated_transform(enriched_df)

    # 3. Collect one result row keyed on the test identity
    rows = curated_df.filter(F.col("employee_id") == TEST_KEY).collect()
    assert rows, f"[FAIL] scenario_<name> | no curated row found for key={TEST_KEY!r}"
    row = rows[0]

    return {
        "disposition": "CONTROLLED",
        "key": {"employee_id": TEST_KEY},
        "actual": {
            "full_name":    row.full_name,
            "salary_band":  row.salary_band,
            "is_active":    row.is_active,
            "has_manager":  row.has_manager,
        },
    }

# ---------------------------------------------------------------------------
# Coverage metadata — printed only, not included in _result
# ---------------------------------------------------------------------------
coverage = {
    "raw_ingestion":  {"disposition": "EXCLUDED",    "reason": "Synthetic data; raw ingestion adapter not exercised"},
    "staging":        {"disposition": "CONTROLLED",  "entities": ["employees"]},
    "enriched":       {"disposition": "CONTROLLED",  "entities": ["mockapi_employees"]},
    "curated":        {"disposition": "CONTROLLED",  "entities": ["employee_profile"]},
}
print(f"[INFO] Coverage: {coverage}")

# ---------------------------------------------------------------------------
# Execute scenarios and expose _result for the runner
# ---------------------------------------------------------------------------
scenarios = {
    "scenario_<name>": scenario_<name>(),
}

_result = {
    "initiative": "<initiative>",
    "mode": "controlled_test_data",
    "scenarios": scenarios,
}
print(f"[OK] setup_<initiative> — scenarios: {list(scenarios.keys())}")
```

### Scenario design rules

- Use a unique, reserved test key (e.g., `INT_TEST_001`) that cannot collide with production data.
- Call transformation functions directly; do not import or execute source notebooks.
- Collect exactly the fields needed by the validate script — keep `actual` small.
- Include at least one row per significant branch (active/inactive, with/without manager, etc.).
- For multi-input transforms, design one independent identity per input path so one cannot mask another.

## Validate Script

The validate script receives `setup_result` (the `_result` dict from setup) as a builtin and asserts on the values collected during setup.

```python
"""
Integration Test — <initiative> — Validation
Asserts on values captured by the setup script.
"""

# setup_result is injected by the runner as a builtin
assert isinstance(setup_result, dict), "[FAIL] setup_result not provided"

scenarios = setup_result.get("scenarios", {})
EXPECTED_SCENARIOS = {"scenario_<name>"}
assert set(scenarios) == EXPECTED_SCENARIOS, (
    f"[FAIL] expected scenarios {sorted(EXPECTED_SCENARIOS)}, "
    f"got {sorted(scenarios)}"
)

print("[START] validate_<initiative> | boundary=curated")

failures = []
results  = {}

def validate_scenario(name: str, scenario: dict) -> None:
    actual   = scenario["actual"]
    expected = {
        "full_name":   "Alice Smith",
        "salary_band": "Band 2",
        "is_active":   True,
        "has_manager": True,
    }
    for field, exp_val in expected.items():
        got = actual.get(field)
        assert got == exp_val, (
            f"[FAIL] {name} | {field} expected={exp_val!r} got={got!r}"
        )

for name in sorted(scenarios):
    try:
        validate_scenario(name, scenarios[name])
        results[name] = "PASS"
    except AssertionError as exc:
        results[name] = "FAIL"
        failures.append({"scenario": name, "error": str(exc)})
        print(f"[FAIL] {name} | {exc}")

print("\n[SUMMARY] <initiative>")
for name in sorted(results):
    print(f"  [{results[name]}] {name}")

assert not failures, f"[FAIL] <initiative> scenario failures: {failures}"
print("[DONE] validate_<initiative> — all scenarios passed")
```

### Assertion rules

- Assert on specific field values, not row counts.
- Every asserted field must be fatal — do not downgrade to a warning.
- For multi-scenario runs, collect all results before asserting so every scenario reports its status.
- Write failure messages that include the scenario name, field, expected value, and actual value.
- Avoid assertions on current timestamps or mutable values not set by the test.

## Coverage — Print Only, Not in _result

Keep coverage metadata out of `_result`. Print it from the setup script:

```python
# RIGHT — coverage logged only
coverage = {"raw": {"disposition": "EXCLUDED", "reason": "external adapter"}}
print(f"[INFO] Coverage: {coverage}")
_result = {"initiative": "...", "mode": "...", "scenarios": scenarios}

# WRONG — coverage bloats _result
_result = {"initiative": "...", "scenarios": scenarios, "coverage": coverage}
```

## Running the Suite

```powershell
# From demo/ root
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
python databricks/tests/integration/common/run_integration_suite.py --initiative <name> --env dev
```
