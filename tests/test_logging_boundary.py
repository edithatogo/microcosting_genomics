# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Library diagnostics use logging without configuring the caller's root logger."""

import ast
from pathlib import Path


def test_library_diagnostics_do_not_print() -> None:
    """Keep direct stdout diagnostics out of the installed library."""
    root = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    paths = [path for name in ("src", "tests") for path in (root / name).rglob("*.py")]
    for path in paths:
        tree = ast.parse(path.read_text())
        violations.extend(
            f"{path.name}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        )
        violations.extend(
            f"{path.name}:{node.lineno}: root logging setup"
            for node in tree.body
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "basicConfig"
        )
    if violations:
        raise AssertionError(violations)
