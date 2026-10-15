"""
Integration test suite runner.

Usage:
    python run_integration_suite.py [--initiative <name>] [--env <dev|qua>]

Reads integration_tests.json, runs each enabled entry's setup then validate
script in sequence, and prints a consolidated pass/fail summary.
"""
import argparse
import importlib.util
import json
import os
import sys
import tempfile
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, "../../../../"))
_CONFIG = os.path.join(_ROOT, "databricks/tests/integration/config/integration_tests.json")
_TESTS_DIR = os.path.join(_ROOT, "databricks/tests/integration")

_SETUP_RESULT_ENV = "_INTEGRATION_SETUP_RESULT_PATH"


def _run_script(path: str) -> dict:
    spec = importlib.util.spec_from_file_location("_int_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "_result", {})


def run(initiative_filter=None, env="dev"):
    with open(_CONFIG) as f:
        cfg = json.load(f)

    entries = [
        e for e in cfg["tests"]
        if e.get("enabled", True) and env in e.get("allowed_envs", ["dev"])
        and (initiative_filter is None or e["initiative"] == initiative_filter)
    ]

    if not entries:
        print(f"[WARN] No enabled entries for initiative={initiative_filter!r} env={env!r}")
        return True

    results = {}
    for entry in entries:
        name = entry["initiative"]
        print(f"\n{'='*60}")
        print(f"[SUITE] {name} | env={env} | type={entry['test_type']}")

        setup_path    = os.path.join(_TESTS_DIR, name, f"setup_{name}.py")
        validate_path = os.path.join(_TESTS_DIR, name, f"validate_{name}.py")

        tmp_path = None
        try:
            print(f"[SETUP]    {setup_path}")
            setup_result = _run_script(setup_path)
            scenarios = list(setup_result.get("scenarios", {}).keys())
            print(f"[SETUP]    OK — scenarios: {scenarios}")

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump(setup_result, tmp, default=str)
                tmp_path = tmp.name

            os.environ[_SETUP_RESULT_ENV] = tmp_path
            sys.modules.pop("_int_script", None)

            print(f"[VALIDATE] {validate_path}")
            _run_script(validate_path)

            results[name] = "PASS"
            print(f"[PASS] {name}")

        except Exception as exc:
            results[name] = f"FAIL: {exc}"
            print(f"[FAIL] {name} | {exc}")
            traceback.print_exc()
        finally:
            os.environ.pop(_SETUP_RESULT_ENV, None)
            sys.modules.pop("_int_script", None)
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    print(f"\n{'='*60}")
    print("[SUITE SUMMARY]")
    all_passed = True
    for n, outcome in results.items():
        status = "PASS" if outcome == "PASS" else "FAIL"
        print(f"  [{status}] {n}: {outcome}")
        if status == "FAIL":
            all_passed = False

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--initiative", default=None)
    parser.add_argument("--env", default="dev")
    args = parser.parse_args()
    sys.exit(0 if run(args.initiative, args.env) else 1)
