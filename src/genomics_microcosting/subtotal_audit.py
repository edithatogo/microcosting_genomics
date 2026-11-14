# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reconcile source subtotal references without selecting alternative branches."""

import ast
import operator
import re
lazy from collections.abc import Callable

import openpyxl
import polars as pl
from openpyxl.utils.cell import range_boundaries
lazy from openpyxl.cell.cell import Cell, MergedCell
lazy from openpyxl.workbook.workbook import Workbook

_CACHE_COMPARISON_TOLERANCE = 0.01


def _reference(token: str, sheet: str) -> tuple[str, str]:
    if "!" in token:
        target, token = token.rsplit("!", 1)
        sheet = target.strip("'").replace("''", "'")
    return sheet, token.replace("$", "")


def _sum_ranges(values: Workbook, sheet: str, arguments: str) -> float:
    total = 0.0
    for token in arguments.split(","):
        target, address = _reference(token.strip(), sheet)
        if not re.fullmatch(r"[A-Z]+\d+(?::[A-Z]+\d+)?", address):
            msg = "unsupported SUM argument"
            raise ValueError(msg)
        left, top, right, bottom = range_boundaries(address)
        for row in values[target].iter_rows(
            min_row=top,
            max_row=bottom,
            min_col=left,
            max_col=right,
        ):
            for item in row:
                value = item.value
                if isinstance(value, (int, float)):
                    total += float(value)
    return total


def _evaluate_arithmetic(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(
        node.op,
        (ast.UAdd, ast.USub),
    ):
        value = _evaluate_arithmetic(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    operations: dict[type[ast.operator], Callable[[float, float], float]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: lambda a, b: a / b,
    }
    if isinstance(node, ast.BinOp) and type(node.op) in operations:
        return operations[type(node.op)](
            _evaluate_arithmetic(node.left),
            _evaluate_arithmetic(node.right),
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id.upper() == "SUM"
        and not node.keywords
    ):
        return sum(_evaluate_arithmetic(argument) for argument in node.args)
    msg = "unsupported arithmetic; retained for review"
    raise ValueError(msg)


def _parse_arithmetic(expanded: str) -> float:
    try:
        return _evaluate_arithmetic(ast.parse(expanded, mode="eval").body)
    except (SyntaxError, ZeroDivisionError) as error:
        msg = "unsupported arithmetic; retained for review"
        raise ValueError(msg) from error


def _evaluate_cell(
    formulas: Workbook,
    values: Workbook,
    sheet: str,
    cell: str,
    visiting: set[tuple[str, str]],
) -> float:
    identity = (sheet, cell)
    if identity in visiting:
        msg = "circular reference"
        raise ValueError(msg)
    formula = formulas[sheet][cell].value
    cached = values[sheet][cell].value
    if not isinstance(formula, str) or not formula.startswith("="):
        if isinstance(cached, (float, int)):
            return float(cached)
        if cached is None:
            return 0.0  # Excel SUM ignores blank referenced cells.
        msg = "nonnumeric reference"
        raise ValueError(msg)
    expression = formula[1:]
    match = re.fullmatch(r"SUM\((.+)\)", expression, re.IGNORECASE)
    if match:
        return _sum_ranges(values, sheet, match.group(1))
    target, address = _reference(expression, sheet)
    if re.fullmatch(r"[A-Z]+\d+", address):
        return _evaluate_cell(formulas, values, target, address, visiting | {identity})

    def substitute(match: re.Match[str]) -> str:
        target, address = _reference(match.group(0), sheet)
        value = values[target][address].value
        if value is None:
            return "0.0"
        if not isinstance(value, (int, float)):
            msg = "nonnumeric arithmetic reference"
            raise TypeError(msg)
        return repr(float(value))

    expanded = re.sub(r"(?:'[^']+'!)?\$?[A-Z]+\$?\d+", substitute, expression)

    return _parse_arithmetic(expanded)


def audit_subtotals(workbook: str) -> pl.DataFrame:
    """Compare supported SUM/reference subtotals with their cached components."""
    formulas = openpyxl.load_workbook(workbook, data_only=False)
    rows: list[dict[str, str | float | None]] = []
    try:
        values = openpyxl.load_workbook(workbook, data_only=True)
        try:
            sheet = values["Detailed Table"]
            for row in sheet.iter_rows(min_row=5):
                label = row[3].value
                if isinstance(label, str) and re.match(r"(?i)^\s*total\b", label):
                    rows.extend(
                        _subtotal_row(formulas, values, sheet.title, row[index], label)
                        for index in (12, 13, 14)
                    )
        finally:
            values.close()
    finally:
        formulas.close()
    return pl.DataFrame(rows)


def _subtotal_row(
    formulas: Workbook,
    values: Workbook,
    sheet: str,
    cell: Cell | MergedCell,
    label: str,
) -> dict[str, str | float | None]:
    formula = formulas[sheet][cell.coordinate].value
    cached = cell.value
    status = "missing_cached_total"
    estimate = None
    difference = None
    if cached is not None or formula is not None:
        try:
            estimate = _evaluate_cell(formulas, values, sheet, cell.coordinate, set())
        except (ValueError, TypeError, KeyError) as error:
            status = str(error)
        else:
            if isinstance(cached, (int, float)):
                difference = estimate - float(cached)
                status = (
                    "agrees"
                    if abs(difference) <= _CACHE_COMPARISON_TOLERANCE
                    else "disagrees"
                )
    return {
        "cell": cell.coordinate,
        "label": label,
        "formula": str(formula),
        "status": status,
        "recalculated": estimate,
        "difference": difference,
    }
