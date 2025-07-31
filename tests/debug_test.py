from pathlib import Path

import pytest

from unimelb_phd_phase_1.calculation_engine import CalculationEngine


@pytest.fixture
def test_engine():
    """
    Provides a CalculationEngine instance initialized with test data.
    """
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    engine = CalculationEngine(test_data_path)
    engine.sheet_configs["Sheet1"] = {"header_rows": 1, "data_starts_at": 2}
    return engine


def test_sum_range_debug(test_engine):
    formula = "=SUM(A2:A4)"
    result = test_engine.execute_formula(formula, "Sheet1", "A5")
    assert result == 4


def test_numpy_values(test_engine):
    import numpy as np
    import pandas as pd

    df = test_engine.sheets["Sheet1"]
    df.loc[0, "col1"] = np.int64(1)
    df.loc[1, "col1"] = np.float64(2.0)
    df.loc[0, "col2"] = np.float64(4.0)

    test_engine.formula_sheets["Sheet1"] = pd.DataFrame(
        [[None] * df.shape[1] for _ in range(df.shape[0])],
        index=df.index,
        columns=df.columns,
        dtype=object,
    )

    result_add = test_engine.execute_formula("=A2+A3", "Sheet1", "D1")
    assert result_add == 3

    result_mul = test_engine.execute_formula("=A2*B2", "Sheet1", "D2")
    assert result_mul == 4

