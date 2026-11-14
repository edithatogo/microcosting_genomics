# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Translate restricted arithmetic syntax into existing formula strategy records."""

import ast
import re

MAX_EXPRESSION_LENGTH = 10_000
MAX_SYNTAX_NODES = 256
REFERENCE = re.compile(
    r"(?<![\w.])(?:(?:'(?:[^']|'')+'|[A-Za-z_][\w.]*)!)?"
    r"\$?[A-Za-z]+\$?\d+(?![\w.])",
)


class UnsupportedArithmeticError(ValueError):
    """Retain unsupported expressions for review instead of evaluating text."""


def _negative(record: dict[str, object]) -> dict[str, object]:
    """Express a unary minus using the existing multiplication contract."""
    return {
        "type": "multiplication",
        "operands": [{"type": "literal", "value": -1}, record],
    }


def _binary(
    node: ast.BinOp,
    references: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Retain Excel arithmetic order with explicit nested operands."""
    operations: dict[type[ast.operator], str] = {
        ast.Add: "addition",
        ast.Mult: "multiplication",
        ast.Div: "division",
    }
    left = _convert(node.left, references)
    right = _convert(node.right, references)
    if isinstance(node.op, ast.Sub):
        return {"type": "addition", "operands": [left, _negative(right)]}
    kind = operations.get(type(node.op))
    if kind is None:
        raise UnsupportedArithmeticError
    return {"type": kind, "operands": [left, right]}


def _convert(
    node: ast.AST,
    references: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Accept numeric constants, known cell tokens and four arithmetic operators."""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return {"type": "literal", "value": node.value}
    if isinstance(node, ast.Name) and node.id in references:
        return references[node.id]
    if isinstance(node, ast.BinOp):
        return _binary(node, references)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _convert(node.operand, references)
        return _negative(operand) if isinstance(node.op, ast.USub) else operand
    raise UnsupportedArithmeticError


def parse_arithmetic(formula: str) -> dict[str, object] | None:
    """Parse arithmetic without function calls, attribute access or Python eval."""
    if len(formula) > MAX_EXPRESSION_LENGTH:
        return None
    references: dict[str, dict[str, object]] = {}

    def substitute(match: re.Match[str]) -> str:
        token = match.group()
        sheet: str | None = None
        if "!" in token:
            qualifier, token = token.rsplit("!", 1)
            sheet = qualifier.strip("'").replace("''", "'")
        name = f"REF_{len(references)}"
        references[name] = {"type": "reference", "sheet": sheet, "cell": token}
        return name

    expanded = REFERENCE.sub(substitute, formula)
    try:
        tree = ast.parse(expanded, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > MAX_SYNTAX_NODES:
            return None
        if isinstance(tree.body, ast.Constant):
            # Standalone literal syntax remains the existing parser contract.
            return None
        return _convert(tree.body, references)
    except SyntaxError, UnsupportedArithmeticError, RecursionError:
        return None
