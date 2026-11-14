# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Retain range/NumPy regressions with a disposable synthetic workbook."""

from typing import TYPE_CHECKING

import numpy as np
import polars as pl
import pytest
from openpyxl import Workbook

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager
from tests.checks import require_equal

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def test_engine(tmp_path: Path) -> CalculationEngine:
    """Load the same synthetic cell values without a source-tree binary fixture."""
    test_data_path = tmp_path / "test_data.xlsx"
    workbook = Workbook()
    first = workbook.active
    if first is None:
        raise AssertionError
    first.title = "Sheet1"
    first.append(["col1", "col2", "col3"])
    for row in ((1, 4, "=A2*B2"), (2, 5, "=A3*B3"), (3, 6, "=A4*B4")):
        first.append(row)
    second = workbook.create_sheet("Sheet2")
    for row in (("colA", "colB"), (10, 40), (20, 50), (30, 60)):
        second.append(row)
    try:
        workbook.save(test_data_path)
    finally:
        workbook.close()

    sheet_manager = SheetManager(test_data_path)
    engine = CalculationEngine(sheet_manager)
    engine.sheet_configs["Sheet1"] = {"header_rows": 1, "data_starts_at": 2}
    return engine


def test_sum_range_debug(test_engine: CalculationEngine) -> None:
    """Retain the original exact SUM result."""
    formula = "=SUM(A2:A4)"
    result = test_engine.execute_formula(formula, "Sheet1", "A5")
    require_equal(result, 6)


def test_numpy_values(test_engine: CalculationEngine) -> None:
    """Retain exact addition/multiplication of NumPy-valued workbook cells."""
    df = test_engine.sheets["Sheet1"]
    df[0, "col1"] = np.int64(1)
    df[1, "col1"] = np.float64(2.0)
    df[0, "col2"] = np.float64(4.0)

    test_engine.formula_sheets["Sheet1"] = pl.DataFrame(
        {name: [None] * df.height for name in df.columns},
    )

    result_add = test_engine.execute_formula("=A2+A3", "Sheet1", "D1")
    require_equal(result_add, 3)

    result_mul = test_engine.execute_formula("=A2*B2", "Sheet1", "D2")
    require_equal(result_mul, 4)
