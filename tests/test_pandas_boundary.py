# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Keep production source and package metadata free of pandas dependencies."""

import ast
import importlib.util
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_dependencies_exclude_pandas() -> None:
    """Reject pandas in every runtime, optional and development declaration."""
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = list(metadata["project"]["dependencies"])
    for group in metadata["project"]["optional-dependencies"].values():
        dependencies.extend(group)
    for group in metadata["dependency-groups"].values():
        dependencies.extend(group)
    names = {re.split(r"[\[<>=!~; ]", item)[0].lower() for item in dependencies}
    if "pandas" in names:
        raise AssertionError(names)


def test_locked_environment_excludes_pandas() -> None:
    """Check the resolved graph and the interpreter actually executing tests."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    names = {package["name"] for package in lock["package"]}
    if "pandas" in names or importlib.util.find_spec("pandas") is not None:
        message = "pandas is present in the locked/test environment"
        raise AssertionError(message)


def test_production_source_excludes_pandas_boundaries() -> None:
    """Reject pandas imports/conversions in production and the whole test tree."""
    violations: list[str] = []
    paths = [path for root in ("src", "tests") for path in (ROOT / root).rglob("*.py")]
    for path in paths:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                modules = [node.module or ""]
            else:
                modules = []
            if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                name.split(".")[0] == "pandas" for name in modules
            ):
                violations.append(f"{path.name}:{node.lineno}: import")
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            name = (
                function.attr
                if isinstance(function, ast.Attribute)
                else function.id
                if isinstance(function, ast.Name)
                else ""
            )
            if name in {"to_pandas", "from_pandas"}:
                violations.append(f"{path.name}:{node.lineno}: conversion")
            if _imports_pandas_dynamically(name, node):
                violations.append(f"{path.name}:{node.lineno}: dynamic import")
    if violations:
        raise AssertionError(violations)


def _imports_pandas_dynamically(name: str, call: ast.Call) -> bool:
    if name not in {"import_module", "__import__"} or not call.args:
        return False
    argument = call.args[0]
    return (
        isinstance(argument, ast.Constant)
        and isinstance(argument.value, str)
        and argument.value.split(".")[0] == "pandas"
    )
