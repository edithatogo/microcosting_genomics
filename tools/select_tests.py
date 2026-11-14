# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Run affected tests; fail closed to the full suite for uncertain source impact."""

import ast
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def select_tests(paths: list[str]) -> list[str]:
    """Select changed tests and conservative reverse import dependencies."""
    changed = {Path(path).as_posix() for path in paths}
    shared = {"pyproject.toml", "uv.lock", "tests/conftest.py", "tests/checks.py"}
    if changed & shared or any(path.startswith("data/") for path in changed):
        return ["tests"]
    if any(
        path.startswith("tests/")
        and path.endswith(".py")
        and not Path(path).name.startswith("test_")
        for path in changed
    ):
        return ["tests"]
    source = [
        path for path in changed if path.startswith("src/") and path.endswith(".py")
    ]
    selected = {
        path
        for path in changed
        if path.startswith("tests/test_") and path.endswith(".py")
    }
    if not source:
        if any(
            path.endswith(".py") and not path.startswith("tests/") for path in changed
        ):
            return ["tests"]
        return sorted(selected)
    affected = {Path(path).stem for path in source}
    modules = list((ROOT / "src").rglob("*.py"))
    tests = list((ROOT / "tests").rglob("test_*.py"))
    imports = _import_graph(modules + tests)
    while True:
        expanded = affected | {
            path.stem for path in modules if imports[path] & affected
        }
        if expanded == affected:
            break
        affected = expanded
    selected.update(
        str(path.relative_to(ROOT)) for path in tests if imports[path] & affected
    )
    # Unmapped source, package initialization and dynamic consumers require a milestone.
    if not selected or any(Path(path).name == "__init__.py" for path in source):
        return ["tests"]
    return sorted(selected)


def main() -> int:
    """Run the selected tests with normal pytest cache and visible first failures."""
    if os.environ.get("MICROCOSTING_CI_COVERAGE") == "1":
        coverage_xml = os.environ.get("COVERAGE_XML", "coverage.xml")
        return int(
            pytest.main(
                [
                    "tests",
                    "--disable-socket",
                    "--allow-unix-socket",
                    "--timeout=120",
                    "--cov=src",
                    "--cov-fail-under=30",
                    f"--cov-report=xml:{coverage_xml}",
                    "--cov-report=term-missing",
                    "-q",
                ],
            ),
        )
    paths = select_tests(sys.argv[1:])
    if not paths:
        return 0
    return int(pytest.main([*paths, "-q"]))


def _import_graph(paths: list[Path]) -> dict[Path, set[str]]:
    """Read direct import edges without executing project modules."""
    imports: dict[Path, set[str]] = {}
    for path in paths:
        tree = ast.parse(path.read_text())
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(
                    part for alias in node.names for part in alias.name.split(".")
                )
            elif isinstance(node, ast.ImportFrom):
                names.update((node.module or "").split("."))
                names.update(alias.name for alias in node.names)
        imports[path] = names
    return imports


if __name__ == "__main__":
    raise SystemExit(main())
