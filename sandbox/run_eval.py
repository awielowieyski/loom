#!/usr/bin/env python3
"""Sandbox evaluation runner — executes inside the Docker container.

Reads a JSON task from stdin containing code_blocks and eval_scenarios,
performs syntax checking, linting, and scenario validation, then writes
a JSON result to stdout.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys


def _check_syntax(code: str, filename: str = "skill.py") -> list[str]:
    """Return syntax errors found via ast.parse, empty list if clean."""
    errors: list[str] = []
    try:
        ast.parse(code, filename=filename)
    except SyntaxError as exc:
        loc = f"line {exc.lineno}" if exc.lineno else "unknown location"
        errors.append(f"SyntaxError in {filename} at {loc}: {exc.msg}")
    return errors


def _run_ruff(code: str) -> list[str]:
    """Run ruff on Python code, returning lint warnings. Skips if ruff unavailable."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--stdin-filename=skill.py", "-"],
            input=code,
            capture_output=True,
            text=True,
            timeout=10,
        )
        warnings: list[str] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line and not line.startswith("All checks passed"):
                warnings.append(line)
        return warnings
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _validate_scenario(scenario: dict) -> list[str]:
    """Validate that an eval scenario has required fields."""
    errors: list[str] = []
    for field in ("description", "input_context", "success_criteria"):
        value = scenario.get(field)
        if not value or not str(value).strip():
            errors.append(f"Scenario missing or empty field: {field}")
    return errors


def main() -> None:
    """Entry point — read task from stdin, write result to stdout."""
    result = {
        "passed": False,
        "scenarios_run": 0,
        "scenarios_passed": 0,
        "errors": [],
        "lint_warnings": [],
    }

    try:
        raw = sys.stdin.read()
        task = json.loads(raw)

        code_blocks = task.get("code_blocks", [])
        eval_scenarios = task.get("eval_scenarios", [])

        errors: list[str] = []
        lint_warnings: list[str] = []

        # Check Python code blocks for syntax errors and lint
        for i, block in enumerate(code_blocks):
            lang = block.get("language", "").lower()
            code = block.get("code", "")
            if lang in ("python", "py", "python3"):
                filename = f"block_{i}.py"
                errors.extend(_check_syntax(code, filename))
                lint_warnings.extend(_run_ruff(code))

        # Validate eval scenarios
        scenarios_run = 0
        scenarios_passed = 0
        for scenario in eval_scenarios:
            scenarios_run += 1
            scenario_errors = _validate_scenario(scenario)
            if scenario_errors:
                errors.extend(scenario_errors)
            else:
                scenarios_passed += 1

        passed = len(errors) == 0 and scenarios_run > 0
        result = {
            "passed": passed,
            "scenarios_run": scenarios_run,
            "scenarios_passed": scenarios_passed,
            "errors": errors,
            "lint_warnings": lint_warnings,
        }
    except Exception as exc:
        result["errors"] = [f"Runner error: {type(exc).__name__}: {exc}"]

    json.dump(result, sys.stdout)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
