import pytest
from pathlib import Path
from unimelb_phd_phase_1.calculation_engine import CalculationEngine

@pytest.fixture
def test_engine():
    """
    Provides a CalculationEngine instance initialized with test data.
    """
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    engine = CalculationEngine(test_data_path)
    engine.sheet_configs['Sheet1'] = {'header_rows': 1, 'data_starts_at': 2}
    return engine

def test_sum_range_debug(test_engine):
    formula = '=SUM(A2:A4)'
    result = test_engine.execute_formula(formula, 'Sheet1', 'A5')
    assert result == 6
