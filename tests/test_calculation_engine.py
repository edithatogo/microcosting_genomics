import pytest
from pathlib import Path
import os
import pandas as pd
import math
import warnings

# Silence very verbose PerformanceWarnings emitted during data loading
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.utils import cell_to_coords, coords_to_cell
from unimelb_phd_phase_1 import excel_utils
import openpyxl

@pytest.fixture
def engine():
    """
    Provides a CalculationEngine instance initialized with prepared data.
    """
    return CalculationEngine()

@pytest.fixture
def test_engine():
    """
    Provides a CalculationEngine instance initialized with test data.
    """
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    engine = CalculationEngine(test_data_path)
    engine.sheet_configs['Sheet2'] = {'header_rows': 1, 'data_starts_at': 2}
    sheet_obj = engine._workbook['Sheet2']
    values, formulas = engine._load_raw_sheet_data(sheet_obj)
    engine.sheets['Sheet2'] = engine._process_raw_dataframe(values, sheet_obj, 'Sheet2', data_only=True)
    engine.formula_sheets['Sheet2'] = engine._process_raw_dataframe(formulas, sheet_obj, 'Sheet2', data_only=False)
    return engine

@pytest.fixture
def main_excel_engine():
    """
    Provides a CalculationEngine instance initialized with the main Excel file.
    """
    data_dir = Path(__file__).resolve().parents[1] / "data"
    excel_path = data_dir / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    return CalculationEngine(excel_path)

def test_coords_to_cell():
    assert coords_to_cell(0, 0) == 'A1'
    assert coords_to_cell(0, 1) == 'B1'
    assert coords_to_cell(1, 0) == 'A2'
    assert coords_to_cell(0, 25) == 'Z1'
    assert coords_to_cell(0, 26) == 'AA1'
    assert coords_to_cell(0, 51) == 'AZ1'

def test_cell_to_coords():
    assert cell_to_coords('A1') == (0, 0)
    assert cell_to_coords('B1') == (0, 1)
    assert cell_to_coords('A2') == (1, 0)
    assert cell_to_coords('Z1') == (0, 25)
    assert cell_to_coords('AA1') == (0, 26)
    assert cell_to_coords('AZ1') == (0, 51)
    assert cell_to_coords('$A1') == (0, 0)
    assert cell_to_coords('A$1') == (0, 0)
    assert cell_to_coords('$A$1') == (0, 0)

def test_get_cell_value_test_data(test_engine):
    assert test_engine.get_cell_value('Sheet1', 'A2') == 1
    assert test_engine.get_cell_value('Sheet1', 'B2') == 4

def test_get_cell_value_detailed_table(main_excel_engine):
    pytest.skip("Skip heavy Excel check")

def test_get_cell_formula_detailed_table(main_excel_engine):
    pytest.skip("Skip heavy Excel check")

def test_run_engine(test_engine):
    results, errors = test_engine.run_engine('Sheet1')
    assert errors == []
    assert results.shape[0] == 3

def test_engine_initialization(engine):
    """
    Tests the basic initialization of the CalculationEngine.
    """
    assert engine is not None
    sheet_names = engine.get_sheet_names()
    assert isinstance(sheet_names, list)
    assert 'Detailed Table' in sheet_names


def test_detailed_table_header(engine):
    df = engine.get_data('Detailed Table')
    assert df.columns.nlevels == 4

    expected = [
        (float('nan'), 'Test', 'Test', 'Test'),
        (float('nan'), 'Category', 'Category', 'Category'),
        (float('nan'), 'Sub-Category', 'Sub-Category', 'Sub-Category'),
        (float('nan'), 'Step', 'Step', 'Step'),
        ('Estimates', 'Quantity of Use per Test', 'LL', 'LL'),
    ]

    for actual, exp in zip(list(df.columns[:5]), expected):
        for a, e in zip(actual, exp):
            if isinstance(e, float) and math.isnan(e):
                assert pd.isna(a)
            else:
                assert a == e


def test_get_cell_formula(test_engine):
    """
    Tests the get_cell_formula method.
    """
    # Assuming 'test_data.xlsx' has a formula in cell 'C2'
    formula = test_engine.get_cell_formula('Sheet1', 'C2')
    assert formula is not None
    assert formula == "=A2*B2"


def test_execute_formula(test_engine):
    """
    Tests the execute_formula method with a simple formula.
    """
    # This test requires knowledge of the data in 'test_data.xlsx'
    # Let's assume we have a test Excel file with the following data in 'Sheet1':
    #   A  B
    # 1 10 20
    # 2 5  3
    # And we want to compute the formula '=A1+B2'
    # We'll need a way to load a specific test file.
    # For now, let's test a simple arithmetic operation.
    result = test_engine.execute_formula("=SUM(1,2,3)", "Sheet1", "A1")
    assert result == 6

    result = test_engine.execute_formula("=SUM(A2:A4)", "Sheet1", "A5")
    assert result == 6

def test_vlookup_exact_match(test_engine):
    # Test VLOOKUP with an exact match
    result = test_engine.execute_formula('=VLOOKUP(1, A2:B4, 2, FALSE)', 'Sheet1', 'D1')
    assert result == 4

def test_vlookup_approximate_match(test_engine):
    # Test VLOOKUP with an approximate match
    result = test_engine.execute_formula('=VLOOKUP(1.5, A2:B4, 2, TRUE)', 'Sheet1', 'D1')
    assert result == 4  # Should find the value for 1

def test_if_true(test_engine):
    # Test IF when the condition is true
    result = test_engine.execute_formula('=IF(1=1, "true", "false")', 'Sheet1', 'D1')
    assert result == "true"

def test_if_false(test_engine):
    # Test IF when the condition is false
    result = test_engine.execute_formula('=IF(1=2, "true", "false")', 'Sheet1', 'D1')
    assert result == "false"

def test_iferror_no_error(test_engine):
    # Test IFERROR when there is no error
    result = test_engine.execute_formula('=IFERROR(1/1, 0)', 'Sheet1', 'D1')
    assert result == 1

def test_iferror_with_error(test_engine):
    # Test IFERROR when there is an error
    result = test_engine.execute_formula('=IFERROR(1/0, 0)', 'Sheet1', 'D1')
    assert result == 0

def test_addition_literals(test_engine):
    result = test_engine.execute_formula('=1+2', 'Sheet1', 'D1')
    assert result == 3

def test_addition_cell_references(test_engine):
    result = test_engine.execute_formula('=A2+A3', 'Sheet1', 'D1')
    assert result == 3

def test_pmt_literal_values(test_engine):
    result = test_engine.execute_formula('=PMT(0.05, 10, -1000)', 'Sheet1', 'D1')
    assert round(result, 2) == 129.50

def test_pmt_percent_and_cells(test_engine):
    # Ensure cells exist: A2=1, B2=4 as per test data
    result = test_engine.execute_formula('=PMT(50%, A2, -B2)', 'Sheet1', 'D1')
    # rate 50% => 0.5, nper=1, pv=-4 -> payment should be approx 6.0
    assert pytest.approx(result, rel=1e-2) == 6.0

def test_multilevel_header_parsing(test_engine):
    """Ensure headers are loaded as a MultiIndex."""
    df = test_engine.get_data('Sheet1')
    expected = pd.MultiIndex.from_arrays([
        ['col1', 'col2', 'col3'],
    ])
    assert isinstance(df.columns, pd.MultiIndex)
    assert df.columns.equals(expected)


def test_multilevel_header_loader(tmp_path):
    """Load a simple sheet with two header rows and ensure MultiIndex columns."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["lvl1a", "lvl1a", "lvl1b"])
    ws.append(["col1", "col2", "col3"])
    ws.append([1, 2, 3])
    ws.append([4, 5, 6])
    file_path = tmp_path / "multi.xlsx"
    wb.save(file_path)
    wb.close()

    df = excel_utils.load_sheet_with_headers(file_path, "Sheet1", header_rows=2)

    expected = pd.MultiIndex.from_arrays([
        ["lvl1a", "lvl1a", "lvl1b"],
        ["col1", "col2", "col3"],
    ])
    assert isinstance(df.columns, pd.MultiIndex)
    assert df.columns.equals(expected)

def test_multiplication_by_number_other_sheet(test_engine):
    result = test_engine.execute_formula("='Sheet2'!A2*3", 'Sheet1', 'D1')
    assert result == 30

def test_nested_if_with_sum(test_engine):
    result = test_engine.execute_formula('=IF(1=1, SUM(A2:A4), 0)', 'Sheet1', 'E1')
    assert result == 6


def test_absolute_relative_references(test_engine):
    result = test_engine.execute_formula('=$A$2+B$3', 'Sheet1', 'E1')
    assert result == 6


def test_vlookup_cross_sheet(test_engine):
    formula = '=VLOOKUP(A2+19, Sheet2!$A$1:$B$3, 2, FALSE)'
    result = test_engine.execute_formula(formula, 'Sheet1', 'E1')
    assert result == 50
