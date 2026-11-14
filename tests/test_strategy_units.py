# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check worksheet strategy operations against fixed inputs."""

from pathlib import Path

import openpyxl
import pytest

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager
from genomics_microcosting.strategies import ReferenceStrategy
from tests.checks import require_equal


@pytest.fixture
def strategy_engine() -> CalculationEngine:
    """Create the engine used by the strategy tests."""
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"

    sheet_manager = SheetManager(test_data_path)
    return CalculationEngine(sheet_manager)


def test_multiplication_absolute(strategy_engine: CalculationEngine) -> None:
    """Check multiplication absolute."""
    formula = "=A2*B2"
    result = strategy_engine.execute_formula(formula, "Sheet1", "D1")
    require_equal(result, 4)


def test_sum_range_absolute(strategy_engine: CalculationEngine) -> None:
    """Check SUM range absolute."""
    formula = "=SUM($A$2:$A$4)"
    result = strategy_engine.execute_formula(formula, "Sheet1", "D1")
    require_equal(result, 6)


def test_sum_cells_literals_and_refs(strategy_engine: CalculationEngine) -> None:
    """Check SUM cells literals and refs."""
    formula = "=SUM($A$2,$A$3,5)"
    result = strategy_engine.execute_formula(formula, "Sheet1", "D1")
    require_equal(result, 8)


def test_if_with_cross_sheet_condition(strategy_engine: CalculationEngine) -> None:
    """Check IF with cross sheet condition."""
    formula = '=IF(Sheet2!A2=10, "yes", "no")'
    result = strategy_engine.execute_formula(formula, "Sheet1", "D1")
    if not (result == "yes"):
        raise AssertionError


def test_iferror_cross_sheet_missing_cell(strategy_engine: CalculationEngine) -> None:
    """Check IFERROR cross sheet missing cell."""
    formula = "=IFERROR(Sheet2!C1, 99)"
    result = strategy_engine.execute_formula(formula, "Sheet1", "D1")
    require_equal(result, 99)


def test_vlookup_cross_sheet_absolute(strategy_engine: CalculationEngine) -> None:
    """Check VLOOKUP cross sheet absolute."""
    formula = "=VLOOKUP(Sheet2!A3, Sheet2!$A$2:$B$4, 2, FALSE)"
    result = strategy_engine.execute_formula(formula, "Sheet1", "D1")
    require_equal(result, 50)


def test_pmt_cross_sheet_values(strategy_engine: CalculationEngine) -> None:
    """Check PMT cross sheet values."""
    formula = "=PMT(5%, Sheet2!A2, -Sheet2!B2)"
    result = strategy_engine.execute_formula(formula, "Sheet1", "D1")
    if not (result == pytest.approx(5.180182998618266)):
        raise AssertionError


@pytest.mark.parametrize("sheet", [{}, {"sheet": None}])
def test_reference_defaults_to_current_sheet(
    strategy_engine: CalculationEngine,
    sheet: dict[str, object],
) -> None:
    """Resolve both absent and explicit-null sheet qualifiers locally."""
    record = {"type": "reference", "cell": "A2", **sheet}
    strategy = ReferenceStrategy()
    if not (strategy.execute(strategy_engine, record, "Sheet1", "D1") == 1):
        raise AssertionError
    if not (strategy.resolve_reference(strategy_engine, record, "Sheet1") == 1):
        raise AssertionError


@pytest.mark.parametrize("formula", ["=SUM(A2,B2)", "=SUM(A2:B2)"])
def test_sum_does_not_hide_failed_formula(
    tmp_path: Path,
    formula: str,
) -> None:
    """A failed referenced formula must not become a plausible partial total."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    if sheet is None:
        pytest.fail("Synthetic workbook has no active worksheet")
    sheet.title = "Sheet1"
    sheet.append(["first", "second"])
    sheet.append(["=UNSUPPORTED(3)", 5])
    source = tmp_path / "failed-formula.xlsx"
    workbook.save(source)
    workbook.close()
    manager = SheetManager(
        source,
        sheet_configs={"Sheet1": {"header_rows": 1, "data_starts_at": 2}},
    )
    engine = CalculationEngine(manager)
    if engine.execute_formula(formula, "Sheet1", "C2") is not None:
        raise AssertionError
    manager.close()


@pytest.mark.parametrize(
    ("formula", "expected"),
    [("=SUM(A2,A3)*0.27", 0.81), ("=(Sheet2!A2)", 10.0)],
)
def test_composed_source_formulas(
    strategy_engine: CalculationEngine,
    formula: str,
    expected: float,
) -> None:
    """Evaluate source overhead compositions and parenthesized references."""
    if not (
        strategy_engine.execute_formula(formula, "Sheet1", "D1")
        == pytest.approx(
            expected,
        )
    ):
        raise AssertionError


@pytest.mark.parametrize(
    ("formula", "expected"),
    [("=SUM(Sheet2!A2,Sheet2!B2)", 50), ("=SUM(Sheet2!A2:B3)", 120)],
)
def test_sum_preserves_qualified_sheet_targets(
    strategy_engine: CalculationEngine,
    formula: str,
    expected: int,
) -> None:
    """Sum qualified cells and ranges rather than ignoring invalid local names."""
    if not (strategy_engine.execute_formula(formula, "Sheet1", "D1") == expected):
        raise AssertionError


@pytest.mark.parametrize(
    ("formula", "expected"),
    [("=Sheet2!A3-Sheet2!A2", 10), ("=-Sheet2!A2", -10), ("=A2*A3*A4", 6)],
)
def test_remaining_arithmetic_preserves_order(
    strategy_engine: CalculationEngine,
    formula: str,
    expected: int,
) -> None:
    """Preserve subtraction direction, unary signs and three-cell products."""
    if not (strategy_engine.execute_formula(formula, "Sheet1", "D1") == expected):
        raise AssertionError


def test_parentheses_and_sheet_name_plus_are_not_split(
    strategy_engine: CalculationEngine,
) -> None:
    """Preserve grouped arithmetic before the legacy addition matcher runs."""
    require_equal(strategy_engine.execute_formula("=A2+((A4-A2)/2)", "Sheet1", "D1"), 2)


def test_arithmetic_blank_is_distinct_from_unavailable_formula(tmp_path: Path) -> None:
    """Apply Excel blank arithmetic only to a verified empty source cell."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    if sheet is None:
        pytest.fail("Synthetic workbook has no active worksheet")
    sheet.title = "Sheet1"
    sheet.append(["blank", "numeric"])
    sheet.append([None, 5])
    source = tmp_path / "blank-arithmetic.xlsx"
    workbook.save(source)
    workbook.close()
    manager = SheetManager(
        source,
        sheet_configs={"Sheet1": {"header_rows": 1, "data_starts_at": 2}},
    )
    engine = CalculationEngine(manager)
    require_equal(engine.execute_formula("=A2+B2", "Sheet1", "C2"), 5)
    if engine.get_cell_value("Sheet1", "A2") is not None:
        raise AssertionError
    if not (engine.execute_formula("=A2", "Sheet1", "D2") == 0):
        raise AssertionError
    manager.close()
