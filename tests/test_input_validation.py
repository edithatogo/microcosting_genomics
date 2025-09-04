"""Test input validation for genomics microcosting analysis.

This module tests the comprehensive input validation capabilities.
"""

import unittest
import sys
import logging
import tempfile
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.input_validation import (
    InputValidator,
    ValidationError,
    validate_cost_value,
    validate_percentage,
    validate_positive_integer
)


class TestInputValidation(unittest.TestCase):
    """Test input validation capabilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = InputValidator()
    
    def test_sheet_name_validation(self):
        """Test sheet name validation."""
        # Valid sheet names
        self.assertTrue(self.validator.validate_sheet_name("Detailed Table"))
        self.assertTrue(self.validator.validate_sheet_name("Sheet1"))
        self.assertTrue(self.validator.validate_sheet_name("2. Labor Prices"))
        
        # Invalid sheet names
        with self.assertRaises(ValidationError):
            self.validator.validate_sheet_name(None)
        
        with self.assertRaises(ValidationError):
            self.validator.validate_sheet_name("")
        
        with self.assertRaises(ValidationError):
            self.validator.validate_sheet_name("Sheet/Name")  # Contains invalid character
        
        with self.assertRaises(ValidationError):
            self.validator.validate_sheet_name("A" * 300)  # Too long
    
    def test_cell_reference_validation(self):
        """Test cell reference validation."""
        # Valid cell references
        self.assertTrue(self.validator.validate_cell_reference("A1"))
        self.assertTrue(self.validator.validate_cell_reference("BZ999"))
        self.assertTrue(self.validator.validate_cell_reference("XFD1048576"))  # Maximum values
        
        # Invalid cell references
        with self.assertRaises(ValidationError):
            self.validator.validate_cell_reference(None)
        
        with self.assertRaises(ValidationError):
            self.validator.validate_cell_reference("")
        
        with self.assertRaises(ValidationError):
            self.validator.validate_cell_reference("1A")  # Wrong order
        
        with self.assertRaises(ValidationError):
            self.validator.validate_cell_reference("A0")  # Invalid row
        
        with self.assertRaises(ValidationError):
            self.validator.validate_cell_reference("A1048577")  # Row too large
        
        with self.assertRaises(ValidationError):
            self.validator.validate_cell_reference("XFE1")  # Column too large
    
    def test_dataframe_validation(self):
        """Test DataFrame validation."""
        # Valid DataFrame
        df = pd.DataFrame({
            'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
            'Cost': [50000, 75000, 40000, 60000]
        })
        
        self.assertTrue(self.validator.validate_dataframe(df))
        self.assertTrue(self.validator.validate_dataframe(df, expected_columns=['Test', 'Cost']))
        self.assertTrue(self.validator.validate_dataframe(df, min_rows=1, max_rows=10))
        
        # Invalid DataFrame - wrong type
        with self.assertRaises(ValidationError):
            self.validator.validate_dataframe("not a dataframe")
        
        # Invalid DataFrame - missing columns
        with self.assertRaises(ValidationError):
            self.validator.validate_dataframe(df, expected_columns=['Test', 'Missing'])
        
        # Invalid DataFrame - not enough rows
        with self.assertRaises(ValidationError):
            self.validator.validate_dataframe(df, min_rows=10)
        
        # Invalid DataFrame - too many rows
        with self.assertRaises(ValidationError):
            self.validator.validate_dataframe(df, max_rows=2)
    
    def test_numeric_value_validation(self):
        """Test numeric value validation."""
        # Valid numeric values
        self.assertTrue(self.validator.validate_numeric_value(50000))
        self.assertTrue(self.validator.validate_numeric_value(50000.5))
        self.assertTrue(self.validator.validate_numeric_value(-5.5, min_value=-10, max_value=10))
        self.assertTrue(self.validator.validate_numeric_value(None, allow_none=True))
        
        # Invalid numeric values
        with self.assertRaises(ValidationError):
            self.validator.validate_numeric_value(None)
        
        with self.assertRaises(ValidationError):
            self.validator.validate_numeric_value("not a number")
        
        with self.assertRaises(ValidationError):
            self.validator.validate_numeric_value(5, min_value=10)
        
        with self.assertRaises(ValidationError):
            self.validator.validate_numeric_value(15, max_value=10)
        
        with self.assertRaises(ValidationError):
            self.validator.validate_numeric_value(float('nan'))
        
        with self.assertRaises(ValidationError):
            self.validator.validate_numeric_value(float('inf'))
    
    def test_string_value_validation(self):
        """Test string value validation."""
        # Valid string values
        self.assertTrue(self.validator.validate_string_value("test string"))
        self.assertTrue(self.validator.validate_string_value("short", max_length=10))
        self.assertTrue(self.validator.validate_string_value("", allow_empty=True))
        self.assertTrue(self.validator.validate_string_value("123", pattern=r'^\d+$'))
        
        # Invalid string values
        with self.assertRaises(ValidationError):
            self.validator.validate_string_value(None)
        
        with self.assertRaises(ValidationError):
            self.validator.validate_string_value("")  # Empty not allowed by default
        
        with self.assertRaises(ValidationError):
            self.validator.validate_string_value("too long", max_length=5)
        
        with self.assertRaises(ValidationError):
            self.validator.validate_string_value("abc", pattern=r'^\d+$')  # Doesn't match pattern
    
    def test_file_path_validation(self):
        """Test file path validation."""
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.xlsx') as temp_file:
            temp_path = temp_file.name
            
            # Valid file paths
            self.assertTrue(self.validator.validate_file_path(temp_path))
            self.assertTrue(self.validator.validate_file_path(temp_path, must_exist=True))
            self.assertTrue(self.validator.validate_file_path(temp_path, allowed_extensions=['.xlsx']))
            
            # Invalid file paths
            with self.assertRaises(ValidationError):
                self.validator.validate_file_path(None)
            
            with self.assertRaises(ValidationError):
                self.validator.validate_file_path("/nonexistent/file.xlsx", must_exist=True)
            
            with self.assertRaises(ValidationError):
                self.validator.validate_file_path(temp_path, allowed_extensions=['.csv'])
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration
        config = {
            "workbooks": {
                "main": {
                    "path": "data/file.xlsx",
                    "sheets": {
                        "Detailed Table": {
                            "header_rows": 4,
                            "data_starts_at": 5
                        }
                    }
                }
            },
            "default_workbook": "main"
        }
        
        self.assertTrue(self.validator.validate_configuration(config))
        self.assertTrue(self.validator.validate_configuration(config, required_keys=["workbooks", "default_workbook"]))
        
        # Invalid configuration - wrong type
        with self.assertRaises(ValidationError):
            self.validator.validate_configuration("not a dict")
        
        # Invalid configuration - missing required keys
        with self.assertRaises(ValidationError):
            self.validator.validate_configuration(config, required_keys=["missing_key"])
        
        # Invalid configuration - invalid structure
        invalid_config = {
            "workbooks": {
                "main": {
                    "path": "data/file.xlsx",
                    123: "invalid key type"  # Keys must be strings
                }
            }
        }
        
        with self.assertRaises(ValidationError):
            self.validator.validate_configuration(invalid_config)
    
    def test_predefined_validators(self):
        """Test predefined validators."""
        # Test cost value validator
        self.assertTrue(validate_cost_value(50000))
        self.assertTrue(validate_cost_value(0))
        
        with self.assertRaises(ValidationError):
            validate_cost_value(-5)
        
        # Test percentage validator
        self.assertTrue(validate_percentage(50))
        self.assertTrue(validate_percentage(0))
        self.assertTrue(validate_percentage(100))
        
        with self.assertRaises(ValidationError):
            validate_percentage(-5)
        
        with self.assertRaises(ValidationError):
            validate_percentage(105)
        
        # Test positive integer validator
        self.assertTrue(validate_positive_integer(5))
        self.assertTrue(validate_positive_integer("10"))  # String conversion
        
        with self.assertRaises(ValidationError):
            validate_positive_integer(0)
        
        with self.assertRaises(ValidationError):
            validate_positive_integer(-5)
        
        with self.assertRaises(ValidationError):
            validate_positive_integer("not a number")


if __name__ == '__main__':
    unittest.main()