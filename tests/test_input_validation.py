# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test input validation for genomics microcosting analysis.

This module tests the comprehensive input validation capabilities.
"""

import tempfile
import unittest

import polars as pl
import pytest

from genomics_microcosting.input_validation import (
    InputValidator,
    ValidationError,
    validate_cost_value,
    validate_percentage,
    validate_positive_integer,
)


class TestInputValidation(unittest.TestCase):
    """Test input validation capabilities."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.validator = InputValidator()

    def test_sheet_name_validation(self) -> None:
        """Test sheet name validation."""
        # Valid sheet names
        if not (self.validator.validate_sheet_name("Detailed Table")):
            raise AssertionError
        if not (self.validator.validate_sheet_name("Sheet1")):
            raise AssertionError
        if not (self.validator.validate_sheet_name("2. Labor Prices")):
            raise AssertionError

        # Invalid sheet names
        with pytest.raises(ValidationError):
            self.validator.validate_sheet_name(None)

        with pytest.raises(ValidationError):
            self.validator.validate_sheet_name("")

        with pytest.raises(ValidationError):
            self.validator.validate_sheet_name(
                "Sheet/Name",
            )  # Contains invalid character

        with pytest.raises(ValidationError):
            self.validator.validate_sheet_name("A" * 300)  # Too long

    def test_cell_reference_validation(self) -> None:
        """Test cell reference validation."""
        # Valid cell references
        if not (self.validator.validate_cell_reference("A1")):
            raise AssertionError
        if not (self.validator.validate_cell_reference("BZ999")):
            raise AssertionError
        if not (self.validator.validate_cell_reference("XFD1048576")):
            raise AssertionError  # Maximum values

        # Invalid cell references
        with pytest.raises(ValidationError):
            self.validator.validate_cell_reference(None)

        with pytest.raises(ValidationError):
            self.validator.validate_cell_reference("")

        with pytest.raises(ValidationError):
            self.validator.validate_cell_reference("1A")  # Wrong order

        with pytest.raises(ValidationError):
            self.validator.validate_cell_reference("A0")  # Invalid row

        with pytest.raises(ValidationError):
            self.validator.validate_cell_reference("A1048577")  # Row too large

        with pytest.raises(ValidationError):
            self.validator.validate_cell_reference("XFE1")  # Column too large

    def test_dataframe_validation(self) -> None:
        """Test DataFrame validation."""
        # Valid DataFrame
        df = pl.DataFrame(
            {
                "Test": ["Panel", "WES (P)", "WES (T)", "WGS"],
                "Cost": [50000, 75000, 40000, 60000],
            },
        )

        if not (self.validator.validate_dataframe(df)):
            raise AssertionError
        if not (
            self.validator.validate_dataframe(df, expected_columns=["Test", "Cost"])
        ):
            raise AssertionError
        if not (self.validator.validate_dataframe(df, min_rows=1, max_rows=10)):
            raise AssertionError

        # Invalid DataFrame - wrong type
        with pytest.raises(ValidationError):
            self.validator.validate_dataframe("not a dataframe")

        # Invalid DataFrame - missing columns
        with pytest.raises(ValidationError):
            self.validator.validate_dataframe(df, expected_columns=["Test", "Missing"])

        # Invalid DataFrame - not enough rows
        with pytest.raises(ValidationError):
            self.validator.validate_dataframe(df, min_rows=10)

        # Invalid DataFrame - too many rows
        with pytest.raises(ValidationError):
            self.validator.validate_dataframe(df, max_rows=2)

    def test_numeric_value_validation(self) -> None:
        """Test numeric value validation."""
        # Valid numeric values
        if not (self.validator.validate_numeric_value(50000)):
            raise AssertionError
        if not (self.validator.validate_numeric_value(50000.5)):
            raise AssertionError
        if not (
            self.validator.validate_numeric_value(-5.5, min_value=-10, max_value=10)
        ):
            raise AssertionError
        if not (self.validator.validate_numeric_value(None, allow_none=True)):
            raise AssertionError

        # Invalid numeric values
        with pytest.raises(ValidationError):
            self.validator.validate_numeric_value(None)

        with pytest.raises(ValidationError):
            self.validator.validate_numeric_value("not a number")

        with pytest.raises(ValidationError):
            self.validator.validate_numeric_value(5, min_value=10)

        with pytest.raises(ValidationError):
            self.validator.validate_numeric_value(15, max_value=10)

        with pytest.raises(ValidationError):
            self.validator.validate_numeric_value(float("nan"))

        with pytest.raises(ValidationError):
            self.validator.validate_numeric_value(float("inf"))

    def test_string_value_validation(self) -> None:
        """Test string value validation."""
        # Valid string values
        if not (self.validator.validate_string_value("test string")):
            raise AssertionError
        if not (self.validator.validate_string_value("short", max_length=10)):
            raise AssertionError
        if not (self.validator.validate_string_value("", allow_empty=True)):
            raise AssertionError
        if not (self.validator.validate_string_value("123", pattern=r"^\d+$")):
            raise AssertionError

        # Invalid string values
        with pytest.raises(ValidationError):
            self.validator.validate_string_value(None)

        with pytest.raises(ValidationError):
            self.validator.validate_string_value("")  # Empty not allowed by default

        with pytest.raises(ValidationError):
            self.validator.validate_string_value("too long", max_length=5)

        with pytest.raises(ValidationError):
            self.validator.validate_string_value(
                "abc",
                pattern=r"^\d+$",
            )  # Doesn't match pattern

    def test_file_path_validation(self) -> None:
        """Test file path validation."""
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            temp_path = temp_file.name

            # Valid file paths
            if not (self.validator.validate_file_path(temp_path)):
                raise AssertionError
            if not (self.validator.validate_file_path(temp_path, must_exist=True)):
                raise AssertionError
            if not (
                self.validator.validate_file_path(
                    temp_path,
                    allowed_extensions=[".xlsx"],
                )
            ):
                raise AssertionError

            # Invalid file paths
            with pytest.raises(ValidationError):
                self.validator.validate_file_path(None)

            with pytest.raises(ValidationError):
                self.validator.validate_file_path(
                    "/nonexistent/file.xlsx",
                    must_exist=True,
                )

            with pytest.raises(ValidationError):
                self.validator.validate_file_path(
                    temp_path,
                    allowed_extensions=[".csv"],
                )

    def test_configuration_validation(self) -> None:
        """Test configuration validation."""
        # Valid configuration
        config = {
            "workbooks": {
                "main": {
                    "path": "data/file.xlsx",
                    "sheets": {
                        "Detailed Table": {
                            "header_rows": 4,
                            "data_starts_at": 5,
                        },
                    },
                },
            },
            "default_workbook": "main",
        }

        if not (self.validator.validate_configuration(config)):
            raise AssertionError
        if not (
            self.validator.validate_configuration(
                config,
                required_keys=["workbooks", "default_workbook"],
            )
        ):
            raise AssertionError

        # Invalid configuration - wrong type
        with pytest.raises(ValidationError):
            self.validator.validate_configuration("not a dict")

        # Invalid configuration - missing required keys
        with pytest.raises(ValidationError):
            self.validator.validate_configuration(config, required_keys=["missing_key"])

        # Invalid configuration - invalid structure
        invalid_config = {
            "workbooks": {
                "main": {
                    "path": "data/file.xlsx",
                    123: "invalid key type",  # Keys must be strings
                },
            },
        }

        with pytest.raises(ValidationError):
            self.validator.validate_configuration(invalid_config)

    def test_predefined_validators(self) -> None:
        """Test predefined validators."""
        # Test cost value validator
        if not (validate_cost_value(50000)):
            raise AssertionError
        if not (validate_cost_value(0)):
            raise AssertionError

        with pytest.raises(ValidationError):
            validate_cost_value(-5)

        # Test percentage validator
        if not (validate_percentage(50)):
            raise AssertionError
        if not (validate_percentage(0)):
            raise AssertionError
        if not (validate_percentage(100)):
            raise AssertionError

        with pytest.raises(ValidationError):
            validate_percentage(-5)

        with pytest.raises(ValidationError):
            validate_percentage(105)

        # Test positive integer validator
        if not (validate_positive_integer(5)):
            raise AssertionError
        if not (validate_positive_integer("10")):
            raise AssertionError  # String conversion

        with pytest.raises(ValidationError):
            validate_positive_integer(0)

        with pytest.raises(ValidationError):
            validate_positive_integer(-5)

        with pytest.raises(ValidationError):
            validate_positive_integer("not a number")


if __name__ == "__main__":
    unittest.main()
