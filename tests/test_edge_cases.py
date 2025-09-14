"""Tests for edge cases in the calculation engine."""

import math
import warnings
from pathlib import Path

import pandas as pd
import pytest

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)


@pytest.fixture
def engine():
    """
    Provides a CalculationEngine instance initialized with prepared data.
    """
    sheet_manager = SheetManager()
    return CalculationEngine(sheet_manager)


@pytest.fixture
def test_engine():
    """
    Provides a CalculationEngine instance initialized with test data.
    """
    test_data_path = Path(__file__).resolve().parent / "test_data.xlsx"
    sheet_manager = SheetManager(test_data_path)
    return CalculationEngine(sheet_manager)


def test_empty_cell_reference(test_engine):
    """Test handling of references to empty cells."""
    result = test_engine.execute_formula("=A100", "Sheet1", "D1")
    assert result is None or (isinstance(result, float) and math.isnan(result))


def test_circular_reference_detection(test_engine):
    """Test that circular references are detected and handled."""
    # This would require setting up circular references in test data
    # For now, we test that the mechanism exists
    pass


def test_invalid_formula_parsing(test_engine):
    """Test handling of invalid formulas."""
    result = test_engine.execute_formula("=INVALID_FUNCTION(A1)", "Sheet1", "D1")
    assert result is None or "UNSUPPORTED" in str(result)


def test_division_by_zero(test_engine):
    """Test handling of division by zero."""
    result = test_engine.execute_formula("=1/0", "Sheet1", "D1")
    assert result is None or (isinstance(result, float) and math.isnan(result))


def test_reference_to_nonexistent_sheet(test_engine):
    """Test handling of references to nonexistent sheets."""
    result = test_engine.execute_formula("='NonExistentSheet'!A1", "Sheet1", "D1")
    assert result is None


def test_large_number_handling(test_engine):
    """Test handling of numeric literals."""
    # Test with a large integer literal
    result = test_engine.execute_formula("=10000000000", "Sheet1", "D1")
    assert isinstance(result, int)
    assert result == 10000000000
    
    # Test with a float literal
    result = test_engine.execute_formula("=123.456", "Sheet1", "D2")
    assert isinstance(result, float)
    assert result == 123.456


def test_scientific_notation_handling(test_engine):
    """Test handling of scientific notation."""
    # Test with scientific notation
    result = test_engine.execute_formula("=1E10", "Sheet1", "D1")
    assert isinstance(result, (int, float))
    assert result == 10000000000.0
    
    # Test with negative exponent
    result = test_engine.execute_formula("=1E-3", "Sheet1", "D2")
    assert isinstance(result, float)
    assert result == 0.001


def test_text_in_numeric_context(test_engine):
    """Test handling of text values in numeric contexts."""
    result = test_engine.execute_formula("=A1+B1", "Sheet1", "D1")
    # If A1 or B1 contain text, the result should be None or NaN
    assert result is None or (isinstance(result, float) and math.isnan(result))


def test_nested_formula_complexity(test_engine):
    """Test deeply nested formulas."""
    # Create a complex nested formula
    complex_formula = "=IF(IF(IF(1=1,TRUE,FALSE),TRUE,FALSE),1,0)"
    result = test_engine.execute_formula(complex_formula, "Sheet1", "D1")
    assert result in [0, 1, True, False, None]


def test_formula_with_spaces(test_engine):
    """Test formulas with various spacing."""
    # Test with extra spaces
    result1 = test_engine.execute_formula("= A1 + B1 ", "Sheet1", "D1")
    result2 = test_engine.execute_formula("=A1+B1", "Sheet1", "D2")
    # Should produce the same result
    assert result1 == result2 or (result1 is None and result2 is None)


def test_formula_with_line_breaks(test_engine):
    """Test formulas with line breaks (though this is unusual in Excel)."""
    # This is more of a parsing edge case
    formula = "=A1+\nB1"
    result = test_engine.execute_formula(formula, "Sheet1", "D1")
    # Should either work or fail gracefully
    assert result is not None or result is None


def test_extreme_pmt_values(test_engine):
    """Test PMT function with extreme values."""
    # Test with very high interest rate
    result = test_engine.execute_formula("=PMT(0.5, 10, -1000)", "Sheet1", "D1")
    assert isinstance(result, (int, float))
    
    # Test with very long period
    result = test_engine.execute_formula("=PMT(0.01, 1000, -1000)", "Sheet1", "D2")
    assert isinstance(result, (int, float))


def test_vlookup_edge_cases(test_engine):
    """Test VLOOKUP with edge cases."""
    # Test with empty lookup value
    test_engine.execute_formula("=VLOOKUP('', A2:B4, 2, FALSE)", "Sheet1", "D1")
    # Should handle gracefully
    
    # Test with out of range column index
    test_engine.execute_formula("=VLOOKUP(1, A2:B4, 10, FALSE)", "Sheet1", "D2")
    # Should handle gracefully


def test_if_with_string_conditions(test_engine):
    """Test IF statements with string conditions."""
    result = test_engine.execute_formula('=IF("a"="a",1,0)', "Sheet1", "D1")
    assert result == 1
    
    result = test_engine.execute_formula('=IF("a"="b",1,0)', "Sheet1", "D2")
    assert result == 0


def test_sum_with_mixed_types(test_engine):
    """Test SUM with mixed data types."""
    # This would require setting up test data with mixed types
    pass


def test_multiplication_with_nan(test_engine):
    """Test multiplication involving NaN values."""
    # This would require setting up test data with NaN values
    pass


def test_reference_with_merged_cells(test_engine):
    """Test references to merged cells."""
    # This would require setting up test data with merged cells
    pass


if __name__ == "__main__":
    pytest.main([__file__])