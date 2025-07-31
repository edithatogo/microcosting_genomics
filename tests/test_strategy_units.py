import pytest
from pathlib import Path
from unimelb_phd_phase_1.calculation_engine import CalculationEngine

@pytest.fixture
def strategy_engine():
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    engine = CalculationEngine(test_data_path)
    engine.sheet_configs['Sheet2'] = {'header_rows': 1, 'data_starts_at': 2}
    sheet_obj = engine._workbook['Sheet2']
    values, formulas = engine._load_raw_sheet_data(sheet_obj)
    engine.sheets['Sheet2'] = engine._process_raw_dataframe(values, sheet_obj, 'Sheet2', data_only=True)
    engine.formula_sheets['Sheet2'] = engine._process_raw_dataframe(formulas, sheet_obj, 'Sheet2', data_only=False)
    return engine


def test_multiplication_absolute(strategy_engine):
    formula = "=A2*B2"
    result = strategy_engine.execute_formula(formula, 'Sheet1', 'D1')
    assert result == 4


def test_sum_range_absolute(strategy_engine):
    formula = "=SUM($A$2:$A$4)"
    result = strategy_engine.execute_formula(formula, 'Sheet1', 'D1')
    assert result == 6


def test_sum_cells_literals_and_refs(strategy_engine):
    formula = "=SUM($A$2,$A$3,5)"
    result = strategy_engine.execute_formula(formula, 'Sheet1', 'D1')
    assert result == 8


def test_if_with_cross_sheet_condition(strategy_engine):
    formula = "=IF(Sheet2!A2=10, \"yes\", \"no\")"
    result = strategy_engine.execute_formula(formula, 'Sheet1', 'D1')
    assert result == "yes"


def test_iferror_cross_sheet_missing_cell(strategy_engine):
    formula = "=IFERROR(Sheet2!C1, 99)"
    result = strategy_engine.execute_formula(formula, 'Sheet1', 'D1')
    assert result == 99


def test_vlookup_cross_sheet_absolute(strategy_engine):
    formula = "=VLOOKUP(Sheet2!A3, Sheet2!$A$2:$B$4, 2, FALSE)"
    result = strategy_engine.execute_formula(formula, 'Sheet1', 'D1')
    assert result == 50


def test_pmt_cross_sheet_values(strategy_engine):
    formula = "=PMT(5%, Sheet2!A2, -Sheet2!B2)"
    result = strategy_engine.execute_formula(formula, 'Sheet1', 'D1')
    assert result == 0.0

