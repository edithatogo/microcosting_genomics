# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check cross-sheet strategy evaluation."""

from pathlib import Path

import pytest

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager
from tests.checks import require_equal


@pytest.fixture
def test_engine() -> CalculationEngine:
    """Create an engine with the cross-sheet strategy fixtures."""
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"

    sheet_manager = SheetManager(test_data_path)
    return CalculationEngine(sheet_manager)


def test_multiplication_cross_sheet_cells(test_engine: CalculationEngine) -> None:
    """Check multiplication cross sheet cells."""
    result = test_engine.execute_formula("='Sheet2'!A2*'Sheet2'!B2", "Sheet1", "F1")
    require_equal(result, 400)


def test_sum_range_cross_sheet(test_engine: CalculationEngine) -> None:
    """Check SUM range cross sheet."""
    formula = "=SUM(Sheet2!A2, Sheet2!B2, Sheet2!A3, Sheet2!B3)"
    result = test_engine.execute_formula(formula, "Sheet1", "F2")
    # Original fixture cells are 10, 40, 20 and 50; qualified SUM now resolves them.
    require_equal(result, 120)


def test_iferror_with_vlookup_cross_sheet(test_engine: CalculationEngine) -> None:
    """Check IFERROR with VLOOKUP cross sheet."""
    formula = "=IFERROR(VLOOKUP(999, Sheet2!$A$1:$B$3, 2, FALSE), 99)"
    result = test_engine.execute_formula(formula, "Sheet1", "F3")
    require_equal(result, 99)


def test_if_condition_cross_sheet(test_engine: CalculationEngine) -> None:
    """Check IF condition cross sheet."""
    result = test_engine.execute_formula(
        "=IF(Sheet2!A2>5, 'ok', 'fail')",
        "Sheet1",
        "F4",
    )
    if result is not None:
        raise AssertionError


def test_pmt_cross_sheet_values(test_engine: CalculationEngine) -> None:
    """Check PMT cross sheet values."""
    result = test_engine.execute_formula(
        "=PMT(50%, Sheet1!A2, -Sheet2!B2)",
        "Sheet1",
        "F5",
    )
    if not (result == pytest.approx(60.0)):
        raise AssertionError


def test_vlookup_cross_sheet_approximate(test_engine: CalculationEngine) -> None:
    """Check VLOOKUP cross sheet approximate."""
    result = test_engine.execute_formula(
        "=VLOOKUP(15, Sheet2!$A$1:$B$3, 2, TRUE)",
        "Sheet1",
        "F6",
    )
    require_equal(result, 40)


def test_absolute_references_cross_sheet(test_engine: CalculationEngine) -> None:
    """Check absolute references cross sheet."""
    result = test_engine.execute_formula("='Sheet2'!$A$2+'Sheet2'!$B$3", "Sheet1", "F7")
    require_equal(result, 60)
