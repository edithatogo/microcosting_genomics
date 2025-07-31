import pytest
from pathlib import Path
from unimelb_phd_phase_1.calculation_engine import CalculationEngine

@pytest.fixture
def test_engine():
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    engine = CalculationEngine(test_data_path)
    return engine


def test_multiplication_cross_sheet_cells(test_engine):
    result = test_engine.execute_formula("='Sheet2'!A2*'Sheet2'!B2", 'Sheet1', 'F1')
    assert result == 400


def test_sum_range_cross_sheet(test_engine):
    formula = "=SUM(Sheet2!A2, Sheet2!B2, Sheet2!A3, Sheet2!B3)"
    result = test_engine.execute_formula(formula, 'Sheet1', 'F2')
    assert result == 0


def test_iferror_with_vlookup_cross_sheet(test_engine):
    formula = "=IFERROR(VLOOKUP(999, Sheet2!$A$1:$B$3, 2, FALSE), 99)"
    result = test_engine.execute_formula(formula, 'Sheet1', 'F3')
    assert result == 99


def test_if_condition_cross_sheet(test_engine):
    result = test_engine.execute_formula("=IF(Sheet2!A2>5, 'ok', 'fail')", 'Sheet1', 'F4')
    assert result is None


def test_pmt_cross_sheet_values(test_engine):
    result = test_engine.execute_formula("=PMT(50%, Sheet1!A2, -Sheet2!B2)", 'Sheet1', 'F5')
    assert result == 0.0


def test_vlookup_cross_sheet_approximate(test_engine):
    result = test_engine.execute_formula("=VLOOKUP(15, Sheet2!$A$1:$B$3, 2, TRUE)", 'Sheet1', 'F6')
    assert result == 40


def test_absolute_references_cross_sheet(test_engine):
    result = test_engine.execute_formula("='Sheet2'!$A$2+'Sheet2'!$B$3", 'Sheet1', 'F7')
    assert result == 60
