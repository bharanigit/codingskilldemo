"""
Integration Test — mockapi_employees — Validation

Reads setup_result written by the runner to a temp JSON file (path in
_INTEGRATION_SETUP_RESULT_PATH env var) and asserts curated output values
for all three scenarios.
"""
import json
import os

_path = os.environ.get("_INTEGRATION_SETUP_RESULT_PATH")
assert _path, (
    "[FAIL] _INTEGRATION_SETUP_RESULT_PATH not set — "
    "run via databricks/tests/integration/common/run_integration_suite.py"
)
with open(_path, encoding="utf-8") as _f:
    setup_result = json.load(_f)

assert isinstance(setup_result, dict), "[FAIL] setup_result is not a dict"
scenarios = setup_result.get("scenarios", {})

_EXPECTED_SCENARIOS = {
    "active_employee_with_manager",
    "inactive_employee_without_manager",
    "deduplication",
}
assert set(scenarios) == _EXPECTED_SCENARIOS, (
    f"[FAIL] expected scenarios {sorted(_EXPECTED_SCENARIOS)}, got {sorted(scenarios)}"
)

print("[START] validate_mockapi_employees | boundary=curated")

failures = []
results  = {}

# ---------------------------------------------------------------------------
# Scenario: active_employee_with_manager
# Key: INT_TEST_001 — Senior Engineer, salary=85000, active, manager present
# ---------------------------------------------------------------------------
def _validate_active_employee_with_manager(scenario: dict) -> None:
    actual = scenario["actual"]
    checks = {
        "full_name":       "Test Senior",
        "salary_band":     "Band 3",
        "job_level":       "Senior",
        "has_manager":     True,
        "is_active":       True,
        "email_domain":    "mockapi.io",
        "office_location": "London",
    }
    for field, expected in checks.items():
        got = actual.get(field)
        assert got == expected, (
            f"[FAIL] active_employee_with_manager | {field} expected={expected!r} got={got!r}"
        )


# ---------------------------------------------------------------------------
# Scenario: inactive_employee_without_manager
# Key: INT_TEST_002 — Recruiter, salary=48000, inactive, no manager
# ---------------------------------------------------------------------------
def _validate_inactive_employee_without_manager(scenario: dict) -> None:
    actual = scenario["actual"]
    checks = {
        "full_name":    "Test Standard",
        "salary_band":  "Band 1",
        "job_level":    "Standard",
        "has_manager":  False,
        "is_active":    False,
        "email_domain": "mockapi.io",
    }
    for field, expected in checks.items():
        got = actual.get(field)
        assert got == expected, (
            f"[FAIL] inactive_employee_without_manager | {field} expected={expected!r} got={got!r}"
        )


# ---------------------------------------------------------------------------
# Scenario: deduplication
# Key: INT_TEST_003 — two source rows, newer updated_at must survive
# ---------------------------------------------------------------------------
def _validate_deduplication(scenario: dict) -> None:
    actual = scenario["actual"]
    assert actual["row_count"] == 1, (
        f"[FAIL] deduplication | row_count expected=1 got={actual['row_count']!r}"
    )
    checks = {
        "last_name":       "Winner",
        "job_level":       "Senior",
        "office_location": "Sydney",
    }
    for field, expected in checks.items():
        got = actual.get(field)
        assert got == expected, (
            f"[FAIL] deduplication | {field} expected={expected!r} got={got!r}"
        )


_VALIDATORS = {
    "active_employee_with_manager":      _validate_active_employee_with_manager,
    "inactive_employee_without_manager": _validate_inactive_employee_without_manager,
    "deduplication":                     _validate_deduplication,
}

for name in sorted(scenarios):
    try:
        _VALIDATORS[name](scenarios[name])
        results[name] = "PASS"
    except AssertionError as exc:
        results[name] = "FAIL"
        failures.append({"scenario": name, "error": str(exc)})
        print(str(exc))

print("\n[SUMMARY] mockapi_employees")
for name in sorted(results):
    print(f"  [{results[name]}] {name}")

assert not failures, f"[FAIL] mockapi_employees scenario failures: {failures}"
print("[DONE] validate_mockapi_employees — all scenarios passed")
