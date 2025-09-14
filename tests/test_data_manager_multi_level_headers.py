"""Tests for DataManager multi-level header parsing functionality.

This module implements TDD tests for the DataManager's _fix_duplicate_columns method,
which handles multi-level headers from Excel files.
"""

import pandas as pd
import pytest
from pathlib import Path
import tempfile

from genomics_microcosting.data_manager import DataManager


class TestDataManagerMultiLevelHeaders:
    """Test cases for multi-level header parsing in DataManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create DataManager instance
        self.dm = DataManager(self.data_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_fix_duplicate_columns_regular_index(self):
        """Test _fix_duplicate_columns with regular (single-level) column index."""
        # Create test DataFrame with unique initial column names
        df = pd.DataFrame({
            'Col1': [1, 2, 3],
            'Col2': [7, 8, 9]
        })
        
        # Manually set duplicate column names to test our logic
        df.columns = ['Test', 'Test']
        
        # Fix duplicate columns
        result = self.dm._fix_duplicate_columns(df)

        # Verify column names are made unique
        expected_columns = ['Test', 'Test_2']
        assert list(result.columns) == expected_columns

        # Verify data integrity
        assert result.iloc[0, 0] == 1  # First 'Test' column
        assert result.iloc[0, 1] == 7  # Second 'Test' column (renamed to Test_2)
        assert result.iloc[1, 0] == 2
        assert result.iloc[1, 1] == 8

        # Verify data integrity
        assert result.iloc[0, 0] == 1  # First 'Test' column
        assert result.iloc[0, 1] == 7  # Second 'Test' column (renamed to Test_2)
        assert result.iloc[1, 0] == 2
        assert result.iloc[1, 1] == 8

    def test_fix_duplicate_columns_multiindex_simple(self):
        """Test _fix_duplicate_columns with simple MultiIndex columns."""
        # Create MultiIndex columns
        columns = pd.MultiIndex.from_tuples([
            ('Test', 'Test'),
            ('Category', 'Category'),
            ('Sub-Category', 'Sub-Category'),
            ('Step', 'Step')
        ])

        df = pd.DataFrame([[1, 2, 3, 4]], columns=columns)

        # Fix duplicate columns
        result = self.dm._fix_duplicate_columns(df)

        # Verify MultiIndex is converted to regular index
        assert isinstance(result.columns, pd.Index)
        assert not isinstance(result.columns, pd.MultiIndex)

        # Verify column names are properly joined
        expected_columns = ['Test_Test', 'Category_Category', 'Sub-Category_Sub-Category', 'Step_Step']
        assert list(result.columns) == expected_columns

        # Verify data integrity
        assert result.iloc[0, 0] == 1
        assert result.iloc[0, 1] == 2
        assert result.iloc[0, 2] == 3
        assert result.iloc[0, 3] == 4

    def test_fix_duplicate_columns_multiindex_with_nulls(self):
        """Test _fix_duplicate_columns with MultiIndex containing null values."""
        # Create MultiIndex with some null values (common in Excel multi-level headers)
        columns = pd.MultiIndex.from_tuples([
            ('Test', None),
            (None, 'Category'),
            ('Sub-Category', 'Sub-Category'),
            ('Step', 'Step')
        ])

        df = pd.DataFrame([[1, 2, 3, 4]], columns=columns)

        # Fix duplicate columns
        result = self.dm._fix_duplicate_columns(df)

        # Verify null parts are excluded from joined names
        expected_columns = ['Test', 'Category', 'Sub-Category_Sub-Category', 'Step_Step']
        assert list(result.columns) == expected_columns

    def test_fix_duplicate_columns_multiindex_complex(self):
        """Test _fix_duplicate_columns with complex MultiIndex scenario."""
        # Simulate real Excel multi-level headers from genomics data
        columns = pd.MultiIndex.from_tuples([
            ('Test Test', 'Test Test'),
            ('Category Category', 'Category Category'),
            ('Sub-Category Sub-Category', 'Sub-Category Sub-Category'),
            ('Step Step', 'Step Step'),
            ('Estimates', 'Quantity of Use per Test LL'),
            ('Estimate', ''),
            ('UL', ''),
            ('Source', ''),
            ('Price (AUD $/unit)', 'LL'),
            ('Estimate_2', ''),
            ('UL_2', ''),
            ('Source_2', ''),
            ('Unit Cost (AUD $/unit)', 'LL'),
            ('Estimate_3', ''),
            ('UL_3', ''),
            ('DSA DSA', 'LL'),
            ('Estimate_4', ''),
            ('UL_4', ''),
            ('LL', ''),
            ('Estimate_5', ''),
            ('UL_5', ''),
            ('LL_2', ''),
            ('Estimate_6', ''),
            ('UL_6', ''),
            ('LL_3', ''),
            ('Estimate_7', ''),
            ('UL_7', '')
        ])

        # Create sample data similar to ground truth
        data = [
            [None, None, None, None, 0.5, 926, 663, None, 831, 921, 831, None, 940, 1014, 940, 682, 682, 682, 682, 682, 682, 264, 264, 264, 264, 264, 264]
        ]
        df = pd.DataFrame(data, columns=columns)

        # Fix duplicate columns
        result = self.dm._fix_duplicate_columns(df)

        # Verify conversion worked
        assert isinstance(result.columns, pd.Index)
        assert not isinstance(result.columns, pd.MultiIndex)

        # Check some key columns
        assert 'Test Test_Test Test' in result.columns
        assert 'Category Category_Category Category' in result.columns
        assert 'Unit Cost (AUD $/unit)_LL' in result.columns
        assert 'Estimate' in result.columns  # Empty string should be ignored
        assert 'UL' in result.columns

        # Verify we have the right number of columns
        assert len(result.columns) == 27

    def test_fix_duplicate_columns_empty_multiindex(self):
        """Test _fix_duplicate_columns with empty MultiIndex."""
        # Create empty DataFrame with MultiIndex columns
        columns = pd.MultiIndex.from_tuples([], names=['level1', 'level2'])
        df = pd.DataFrame(columns=columns)

        result = self.dm._fix_duplicate_columns(df)

        # Should handle empty case gracefully
        assert len(result.columns) == 0

    def test_fix_duplicate_columns_mixed_types(self):
        """Test _fix_duplicate_columns with mixed data types in MultiIndex."""
        # Create MultiIndex with mixed types
        columns = pd.MultiIndex.from_tuples([
            ('Test', 1),
            ('Category', 2.5),
            ('Sub-Category', True)
        ])

        df = pd.DataFrame([[1, 2, 3]], columns=columns)

        result = self.dm._fix_duplicate_columns(df)

        # Should convert all parts to strings and join
        # Note: pandas converts boolean True to 1.0 in MultiIndex
        expected_columns = ['Test_1', 'Category_2.5', 'Sub-Category_1']
        assert list(result.columns) == expected_columns

    def test_fix_duplicate_columns_preserves_data_integrity(self):
        """Test that _fix_duplicate_columns preserves data integrity."""
        # Create test data with known values
        original_data = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
        columns = pd.MultiIndex.from_tuples([
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D'),
            ('E', 'E')
        ])

        df = pd.DataFrame(original_data, columns=columns)

        result = self.dm._fix_duplicate_columns(df)

        # Verify all data is preserved
        assert result.shape == (2, 5)
        assert list(result.iloc[0]) == [1, 2, 3, 4, 5]
        assert list(result.iloc[1]) == [6, 7, 8, 9, 10]

    def test_fix_duplicate_columns_error_handling(self):
        """Test _fix_duplicate_columns error handling."""
        # Create problematic MultiIndex that might cause issues
        columns = pd.MultiIndex.from_tuples([
            ('Test', 'Test'),
            ('Bad', float('nan')),  # NaN value
            ('Category', 'Category')
        ])

        df = pd.DataFrame([[1, 2, 3]], columns=columns)

        # Should handle NaN gracefully
        result = self.dm._fix_duplicate_columns(df)

        # Should have fallback column names
        assert len(result.columns) == 3
        assert result.iloc[0, 0] == 1
        assert result.iloc[0, 1] == 2
        assert result.iloc[0, 2] == 3