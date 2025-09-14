"""Test cases for the Data Consistency Validation module."""

import unittest
import pandas as pd
from unittest.mock import Mock

from src.unimelb_phd_phase_1.data_consistency_validator import DataConsistencyValidator
from src.unimelb_phd_phase_1.data_manager import DataManager


class TestDataConsistencyValidator(unittest.TestCase):
    """Test cases for the DataConsistencyValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.validator = DataConsistencyValidator(self.mock_data_manager)

    def test_init(self):
        """Test DataConsistencyValidator initialization."""
        self.assertIsInstance(self.validator, DataConsistencyValidator)
        self.assertEqual(self.validator.data_manager, self.mock_data_manager)

    def test_validate_sheet_integrity(self):
        """Test sheet integrity validation."""
        # Create test DataFrame
        df = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': [10, 20, 30, 40, 50],
            'C': ['x', 'y', 'z', 'a', 'b']
        })
        
        result = self.validator.validate_sheet_integrity("Test Sheet", df)
        
        self.assertIsInstance(result, dict)
        self.assertIn('sheet_name', result)
        self.assertIn('passed', result)
        self.assertIn('errors', result)
        self.assertIn('warnings', result)
        self.assertIn('metrics', result)
        
        self.assertEqual(result['sheet_name'], "Test Sheet")
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['errors']), 0)
        
        # Check metrics
        metrics = result['metrics']
        self.assertEqual(metrics['row_count'], 5)
        self.assertEqual(metrics['column_count'], 3)
        self.assertEqual(metrics['null_percentage'], 0.0)
        self.assertEqual(metrics['duplicate_rows'], 0)

    def test_validate_sheet_integrity_empty_sheet(self):
        """Test sheet integrity validation with empty sheet."""
        df = pd.DataFrame()
        
        result = self.validator.validate_sheet_integrity("Empty Sheet", df)
        
        self.assertFalse(result['passed'])
        self.assertIn("Sheet is empty", result['errors'])

    def test_validate_sheet_integrity_high_null_percentage(self):
        """Test sheet integrity validation with high null percentage."""
        df = pd.DataFrame({
            'A': [1, None, None, None, None],
            'B': [None, None, None, None, None],
            'C': [None, None, None, None, 5]
        })
        
        result = self.validator.validate_sheet_integrity("High Null Sheet", df)
        
        self.assertTrue(result['passed'])  # Still passes but with warning
        self.assertGreater(len(result['warnings']), 0)
        self.assertIn("High null percentage", result['warnings'][0])

    def test_validate_sheet_consistency(self):
        """Test sheet consistency validation."""
        # Create test DataFrames
        df_parquet = pd.DataFrame({
            'A': [1, 2, 3],
            'B': [10, 20, 30]
        })
        
        df_csv = pd.DataFrame({
            'A': [1, 2, 3],
            'B': [10, 20, 30]
        })
        
        result = self.validator.validate_sheet_consistency("Test Sheet", df_parquet, df_csv)
        
        self.assertIsInstance(result, dict)
        self.assertIn('sheet_name', result)
        self.assertIn('passed', result)
        self.assertIn('errors', result)
        self.assertIn('warnings', result)
        
        self.assertEqual(result['sheet_name'], "Test Sheet")
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['errors']), 0)

    def test_validate_sheet_consistency_shape_mismatch(self):
        """Test sheet consistency validation with shape mismatch."""
        # Create test DataFrames with different shapes
        df_parquet = pd.DataFrame({
            'A': [1, 2, 3],
            'B': [10, 20, 30]
        })
        
        df_csv = pd.DataFrame({
            'A': [1, 2],
            'B': [10, 20]
        })
        
        result = self.validator.validate_sheet_consistency("Test Sheet", df_parquet, df_csv)
        
        self.assertFalse(result['passed'])
        self.assertIn("Shape mismatch", result['errors'][0])

    def test_validate_sheet_consistency_column_mismatch(self):
        """Test sheet consistency validation with column mismatch."""
        # Create test DataFrames with different columns
        df_parquet = pd.DataFrame({
            'A': [1, 2, 3],
            'B': [10, 20, 30]
        })
        
        df_csv = pd.DataFrame({
            'A': [1, 2, 3],
            'C': [10, 20, 30]  # Different column name
        })
        
        result = self.validator.validate_sheet_consistency("Test Sheet", df_parquet, df_csv)
        
        self.assertFalse(result['passed'])
        self.assertIn("Column names mismatch", result['errors'][0])

    def test_validate_cross_sheet_references(self):
        """Test cross-sheet reference validation."""
        # Mock the data manager to return a DataFrame for one sheet and None for another
        self.mock_data_manager.load_sheet.side_effect = [
            pd.DataFrame({'A': [1, 2, 3]}),  # Found sheet
            None  # Missing sheet
        ]
        
        referenced_sheets = ["Found Sheet", "Missing Sheet"]
        result = self.validator.validate_cross_sheet_references("Test Sheet", 
                                                              pd.DataFrame(), 
                                                              referenced_sheets)
        
        self.assertIsInstance(result, dict)
        self.assertIn('sheet_name', result)
        self.assertIn('passed', result)
        self.assertIn('errors', result)
        self.assertIn('warnings', result)
        self.assertIn('referenced_sheets_found', result)
        self.assertIn('referenced_sheets_missing', result)
        
        self.assertEqual(result['sheet_name'], "Test Sheet")
        self.assertFalse(result['passed'])  # Should fail because one sheet is missing
        self.assertEqual(len(result['errors']), 1)
        self.assertIn("Referenced sheet 'Missing Sheet' not found", result['errors'][0])
        self.assertEqual(result['referenced_sheets_found'], ["Found Sheet"])
        self.assertEqual(result['referenced_sheets_missing'], ["Missing Sheet"])

    def test_validate_data_ranges(self):
        """Test data range validation."""
        df = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': [10, 20, 30, 40, 50]
        })
        
        expected_ranges = {
            'A': (1, 5),
            'B': (10, 50)
        }
        
        result = self.validator.validate_data_ranges("Test Sheet", df, expected_ranges)
        
        self.assertIsInstance(result, dict)
        self.assertIn('sheet_name', result)
        self.assertIn('passed', result)
        self.assertIn('errors', result)
        self.assertIn('warnings', result)
        self.assertIn('columns_checked', result)
        
        self.assertEqual(result['sheet_name'], "Test Sheet")
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['warnings']), 0)
        self.assertIn('A', result['columns_checked'])
        self.assertIn('B', result['columns_checked'])

    def test_validate_data_ranges_out_of_bounds(self):
        """Test data range validation with out-of-bounds values."""
        df = pd.DataFrame({
            'A': [1, 2, 3, 4, 10],  # 10 is out of bounds (1,5)
            'B': [10, 20, 30, 40, 50]
        })
        
        expected_ranges = {
            'A': (1, 5),
            'B': (10, 50)
        }
        
        result = self.validator.validate_data_ranges("Test Sheet", df, expected_ranges)
        
        self.assertTrue(result['passed'])  # Still passes but with warning
        self.assertEqual(len(result['warnings']), 1)
        self.assertIn("Column 'A' has 1 values outside expected range [1, 5]", result['warnings'][0])

    def test_validate_unique_constraints(self):
        """Test unique constraint validation."""
        df = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],  # All unique
            'B': [10, 20, 30, 40, 50]  # All unique
        })
        
        unique_columns = ['A', 'B']
        
        result = self.validator.validate_unique_constraints("Test Sheet", df, unique_columns)
        
        self.assertIsInstance(result, dict)
        self.assertIn('sheet_name', result)
        self.assertIn('passed', result)
        self.assertIn('errors', result)
        self.assertIn('warnings', result)
        self.assertIn('columns_checked', result)
        
        self.assertEqual(result['sheet_name'], "Test Sheet")
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['errors']), 0)
        self.assertIn('A', result['columns_checked'])
        self.assertIn('B', result['columns_checked'])

    def test_validate_unique_constraints_duplicates(self):
        """Test unique constraint validation with duplicates."""
        df = pd.DataFrame({
            'A': [1, 2, 2, 4, 5],  # Has duplicate (2)
            'B': [10, 20, 30, 40, 50]  # All unique
        })
        
        unique_columns = ['A', 'B']
        
        result = self.validator.validate_unique_constraints("Test Sheet", df, unique_columns)
        
        self.assertFalse(result['passed'])
        self.assertEqual(len(result['errors']), 1)
        self.assertIn("Column 'A' has 1 duplicate values (should be unique)", result['errors'][0])
        self.assertIn('A', result['columns_checked'])
        self.assertIn('B', result['columns_checked'])

    def test_generate_validation_report(self):
        """Test validation report generation."""
        # Mock the data manager
        self.mock_data_manager.list_available_sheets.return_value = {"test_sheet": ["parquet", "csv"]}
        self.mock_data_manager.load_sheet.return_value = pd.DataFrame({'A': [1, 2, 3]})
        
        # Generate report
        report = self.validator.generate_validation_report()
        
        # Check that report is generated
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Data Consistency Validation", report)
        self.assertIn("Validation Results by Sheet", report)


if __name__ == '__main__':
    unittest.main()