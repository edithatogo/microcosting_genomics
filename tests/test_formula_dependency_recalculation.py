# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Formula dependencies must not depend on pre-existing workbook caches."""

lazy from pathlib import Path

from openpyxl import Workbook

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager


def test_division_recursively_evaluates_uncached_operands(tmp_path: Path) -> None:
    """Both cell-by-cell and cell-by-literal division use fresh dependencies."""
    workbook = Workbook()
    sheet = workbook.active
    if sheet is None:
        raise AssertionError
    sheet.title = "Sheet1"
    for column in "ABCDEFGHIJ":
        sheet[f"{column}1"] = column
    sheet["A2"] = "=12*2"
    sheet["B2"] = "=2"
    sheet["C2"] = "=A2/B2"
    sheet["D2"] = "=A2/3"
    sheet["E2"] = "=A2/2*B2"
    sheet["F2"] = "=12/A2"
    sheet["G2"] = "=A2/2*B2*3"
    sheet["H2"] = "=A2/2/3"
    sheet["I2"] = "=A2*B2*3"
    sheet["J2"] = "=A2/2/B2"
    path = tmp_path / "uncached.xlsx"
    workbook.save(path)
    engine = CalculationEngine(SheetManager(path))
    results, errors = engine.run_engine("Sheet1")
    if errors or results is None:
        raise AssertionError(errors)
    expected_cell_division = 12
    expected_literal_division = 8
    if (
        results["C"][0] != expected_cell_division
        or results["D"][0] != expected_literal_division
    ):
        raise AssertionError(results.row(0))
    expected = {"E": 24, "F": 0.5, "G": 72, "H": 4, "I": 144, "J": 6}
    for column, value in expected.items():
        if results[column][0] != value:
            raise AssertionError((column, results[column][0], value))


def test_specialized_arithmetic_rejects_text_formula_operands(tmp_path: Path) -> None:
    """A text-producing dependency cannot become a repeated-string cost."""
    workbook = Workbook()
    sheet = workbook.active
    if sheet is None:
        raise AssertionError
    sheet.title = "Sheet1"
    sheet.append(["A", "B", "C"])
    sheet.append(['="not a cost"', 2, "=A2*B2*3"])
    path = tmp_path / "text.xlsx"
    workbook.save(path)
    engine = CalculationEngine(SheetManager(path))
    value = engine.execute_formula("=A2*B2*3", "Sheet1", "C2")
    if value is not None:
        raise AssertionError(value)
