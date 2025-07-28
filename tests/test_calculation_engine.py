import pytest
import os
print(os.getcwd())
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.utils import cell_to_coords, coords_to_cell

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
    # Construct an absolute path to the test data file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_data_path = os.path.join(current_dir, 'test_data.xlsx')
    return CalculationEngine(test_data_path)

@pytest.fixture
def main_excel_engine():
    """
    Provides a CalculationEngine instance initialized with the main Excel file.
    """
    return CalculationEngine('data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm')

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
    # Test a known value from 'Detailed Table'
    # Based on manual inspection, A4 should be 'Panel'
    assert main_excel_engine.get_cell_value('Detailed Table', 'A6') == 'Panel'
    # Test a known value from 'Detailed Table' that is numeric
    # Based on manual inspection, E6 should be 1
    assert main_excel_engine.get_cell_value('Detailed Table', 'E6') == 1

def test_get_cell_formula_detailed_table(main_excel_engine):
    # Test a known formula from 'Detailed Table'
    # Based on manual inspection, M4 should be "=E4*I4"
    sheet_name = 'Detailed Table'
    cell = 'N6'
    row, col = cell_to_coords(cell)
    config = main_excel_engine.sheet_configs.get(sheet_name, {'header_rows': 0, 'data_starts_at': 1})
    data_starts_at = config['data_starts_at']
    print(f"Debug: Formula sheet N6 content: {main_excel_engine.formula_sheets[sheet_name].iloc[row - (data_starts_at - 1), col]}")
    assert main_excel_engine.get_cell_formula(sheet_name, cell) == "=IFERROR(M6/I6,0)"

def test_run_engine(test_engine):
    results = test_engine.run_engine('Sheet1')
    assert results.iloc[0, 2] == 4
    assert results.iloc[1, 2] == 10
    assert results.iloc[2, 2] == 18

def test_engine_initialization(engine):
    """
    Tests the basic initialization of the CalculationEngine.
    """
    assert engine is not None
    sheet_names = engine.get_sheet_names()
    assert isinstance(sheet_names, list)
    assert 'Detailed Table' in sheet_names


def test_get_cell_formula(test_engine):
    """
    Tests the get_cell_formula method.
    """
    # Assuming 'test_data.xlsx' has a formula in cell 'C2'
    formula = test_engine.get_cell_formula('Sheet1', 'C2')
    assert formula is not None
    assert formula == "=A2*B2"


def test_execute_formula(engine):
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
    result = engine.execute_formula("=1+1")
    assert result == 2

    result = engine.execute_formula("=SUM(1,2,3)")
    assert result == 6

    result = engine.execute_formula("=AVERAGE(2,4,6)")
    assert result == 4

def test_vlookup_exact_match(test_engine):
    # Test VLOOKUP with an exact match
    result = test_engine.execute_formula('=VLOOKUP(1, A2:B4, 2, FALSE)')
    assert result == 4

def test_vlookup_approximate_match(test_engine):
    # Test VLOOKUP with an approximate match
    result = test_engine.execute_formula('=VLOOKUP(1.5, A2:B4, 2, TRUE)')
    assert result == 4  # Should find the value for 1

def test_if_true(test_engine):
    # Test IF when the condition is true
    result = test_engine.execute_formula('=IF(1=1, "true", "false")')
    assert result == "true"

def test_if_false(test_engine):
    # Test IF when the condition is false
    result = test_engine.execute_formula('=IF(1=2, "true", "false")')
    assert result == "false"

def test_iferror_no_error(test_engine):
    # Test IFERROR when there is no error
    result = test_engine.execute_formula('=IFERROR(1/1, 0)')
    assert result == 1

def test_iferror_with_error(test_engine):
    # Test IFERROR when there is an error
    result = test_engine.execute_formula('=IFERROR(1/0, 0)')
    assert result == 0