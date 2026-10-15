# Suite Runner and Configuration

## Authoring and Execution Handoff

The agent creates or updates repository files and checks them statically. All runner behavior occurs during a developer-started integration pipeline run after authoring.

```text
author and statically check repository files
  -> developer runs: python run_integration_suite.py
  -> setup script -> validation script
```

## Bootstrap When Infrastructure Is Absent

If `run_integration_suite.py` or `integration_tests.json` do not exist, create both. This happens once — they then become the immutable shared suite contract.

### run_integration_suite.py

Create at `databricks/tests/integration/common/run_integration_suite.py`:

```python
"""
Integration test suite runner.

Usage:
    python run_integration_suite.py [--initiative <name>] [--env <dev|qua>]

Reads integration_tests.json, executes each enabled entry's setup and
validate scripts in sequence, and reports consolidated results.
"""
import argparse
import importlib.util
import json
import os
import sys
import traceback

_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../.."))
_CONFIG = os.path.join(_ROOT, "databricks/tests/integration/config/integration_tests.json")
_TESTS_DIR = os.path.join(_ROOT, "databricks/tests/integration")


def _load_script(path: str) -> dict:
    """Execute a setup or validate script and return its _result dict."""
    spec = importlib.util.spec_from_file_location("_integration_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "_result", {})


def run(initiative_filter: str | None = None, env: str = "dev") -> bool:
    with open(_CONFIG) as f:
        cfg = json.load(f)

    entries = cfg["tests"]
    if initiative_filter:
        entries = [e for e in entries if e["initiative"] == initiative_filter]
    entries = [e for e in entries if e.get("enabled", True) and env in e.get("allowed_envs", ["dev"])]

    if not entries:
        print(f"[WARN] No enabled entries found for initiative={initiative_filter!r} env={env!r}")
        return True

    results = {}
    for entry in entries:
        name = entry["initiative"]
        print(f"\n{'='*60}")
        print(f"[SUITE] {name} | env={env} | type={entry['test_type']}")

        setup_path = os.path.join(_TESTS_DIR, name, f"setup_{name}.py")
        validate_path = os.path.join(_TESTS_DIR, name, f"validate_{name}.py")

        try:
            print(f"[SETUP] {setup_path}")
            setup_result = _load_script(setup_path)
            print(f"[SETUP] OK — scenarios: {list(setup_result.get('scenarios', {}).keys())}")

            print(f"[VALIDATE] {validate_path}")
            sys.modules.pop("_integration_script", None)
            import builtins
            _original = builtins.__dict__.copy()
            builtins.setup_result = setup_result
            try:
                _load_script(validate_path)
            finally:
                builtins.__dict__.clear()
                builtins.__dict__.update(_original)

            results[name] = "PASS"
            print(f"[PASS] {name}")

        except Exception as exc:
            results[name] = f"FAIL: {exc}"
            print(f"[FAIL] {name} | {exc}")
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("[SUITE SUMMARY]")
    all_passed = True
    for name, outcome in results.items():
        status = "PASS" if outcome == "PASS" else "FAIL"
        print(f"  [{status}] {name}: {outcome}")
        if status == "FAIL":
            all_passed = False

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--initiative", default=None)
    parser.add_argument("--env", default="dev")
    args = parser.parse_args()

    ok = run(args.initiative, args.env)
    sys.exit(0 if ok else 1)
```

### integration_tests.json

Create at `databricks/tests/integration/config/integration_tests.json`:

```json
{
  "tests": []
}
```

## Runner Contract

Once created, treat this contract as immutable:

```text
setup script -> validation script
```

The runner executes each config entry in this order:
1. Loads and executes `setup_<initiative>.py` — collects `_result` (a dict with a `scenarios` key).
2. Passes `setup_result` as a builtin to `validate_<initiative>.py`.
3. Records PASS or FAIL per initiative and prints a consolidated summary.

Do not modify the runner while adding an initiative test. If required coverage cannot fit the contract, report the limitation.

## Config Entry Template

```json
{
  "initiative": "mockapi_employees",
  "test_type": "controlled_test_data",
  "allowed_envs": ["dev"],
  "enabled": true,
  "required_boundary": "curated",
  "setup_timeout_seconds": 300,
  "validate_timeout_seconds": 600
}
```

### Canonical values

- `test_type`: `controlled_test_data`, `observational`
- `allowed_envs`: `dev`, `qua`
- `required_boundary`: `raw`, `staging`, `enriched`, `curated`

Use JSON booleans. Use positive integer timeouts. Omit `target_job_name` — there is no Databricks job in the demo.

## Validate JSON After Editing

```python
import json
with open("databricks/tests/integration/config/integration_tests.json") as f:
    cfg = json.load(f)
print(f"Valid JSON — {len(cfg['tests'])} entries")
```

## Run the Suite

```powershell
# From demo/ root with pltdata on PYTHONPATH
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
python databricks/tests/integration/common/run_integration_suite.py --initiative mockapi_employees --env dev
```
