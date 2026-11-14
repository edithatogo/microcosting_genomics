# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Data Consistency Validation module."""

import unittest
from unittest.mock import Mock

import polars as pl

from genomics_microcosting.data_consistency_validator import (
    DataConsistencyValidator,
)
from genomics_microcosting.data_manager import DataManager
from tests.checks import require, require_equal, require_keys, require_runtime_instance


class TestDataConsistencyValidator(unittest.TestCase):
    """Test cases for the DataConsistencyValidator class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.validator = DataConsistencyValidator(self.mock_data_manager)

    def test_init(self) -> None:
        """Test DataConsistencyValidator initialization."""
        require_runtime_instance(self.validator, DataConsistencyValidator)
        if not ((self.validator.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_validate_sheet_integrity(self) -> None:
        """Test sheet integrity validation."""
        # Create test DataFrame
        df = pl.DataFrame(
            {
                "A": [1, 2, 3, 4, 5],
                "B": [10, 20, 30, 40, 50],
                "C": ["x", "y", "z", "a", "b"],
            },
        )

        result = self.validator.validate_sheet_integrity("Test Sheet", df)

        require_runtime_instance(result, dict)
        require_keys(result, ("sheet_name",))
        require_keys(result, ("passed",))
        require_keys(result, ("errors",))
        require_keys(result, ("warnings",))
        require_keys(result, ("metrics",))

        require_equal(result["sheet_name"], "Test Sheet")
        require(condition=result["passed"])
        require_equal(len(result["errors"]), 0)

        # Check metrics
        metrics = result["metrics"]
        require_equal(metrics["row_count"], 5)
        require_equal(metrics["column_count"], 3)
        require_equal(metrics["null_percentage"], 0.0)
        require_equal(metrics["duplicate_rows"], 0)

    def test_validate_sheet_integrity_empty_sheet(self) -> None:
        """Test sheet integrity validation with empty sheet."""
        df = pl.DataFrame()

        result = self.validator.validate_sheet_integrity("Empty Sheet", df)

        if result["passed"]:
            raise AssertionError
        if ("Sheet is empty") not in (result["errors"]):
            raise AssertionError

    def test_validate_sheet_integrity_high_null_percentage(self) -> None:
        """Test sheet integrity validation with high null percentage."""
        df = pl.DataFrame(
            {
                "A": [1, None, None, None, None],
                "B": [None, None, None, None, None],
                "C": [None, None, None, None, 5],
            },
        )

        result = self.validator.validate_sheet_integrity("High Null Sheet", df)

        if not (result["passed"]):
            raise AssertionError  # Still passes but with warning
        if not ((len(result["warnings"])) > (0)):
            raise AssertionError
        if ("High null percentage") not in (result["warnings"][0]):
            raise AssertionError

    def test_validate_sheet_consistency(self) -> None:
        """Test sheet consistency validation."""
        # Create test DataFrames
        df_parquet = pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [10, 20, 30],
            },
        )

        df_csv = pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [10, 20, 30],
            },
        )

        result = self.validator.validate_sheet_consistency(
            "Test Sheet",
            df_parquet,
            df_csv,
        )

        require_runtime_instance(result, dict)
        if ("sheet_name") not in (result):
            raise AssertionError
        if ("passed") not in (result):
            raise AssertionError
        if ("errors") not in (result):
            raise AssertionError
        if ("warnings") not in (result):
            raise AssertionError

        if not ((result["sheet_name"]) == ("Test Sheet")):
            raise AssertionError
        if not (result["passed"]):
            raise AssertionError
        if not ((len(result["errors"])) == (0)):
            raise AssertionError

    def test_validate_sheet_consistency_shape_mismatch(self) -> None:
        """Test sheet consistency validation with shape mismatch."""
        # Create test DataFrames with different shapes
        df_parquet = pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [10, 20, 30],
            },
        )

        df_csv = pl.DataFrame(
            {
                "A": [1, 2],
                "B": [10, 20],
            },
        )

        result = self.validator.validate_sheet_consistency(
            "Test Sheet",
            df_parquet,
            df_csv,
        )

        if result["passed"]:
            raise AssertionError
        if ("Shape mismatch") not in (result["errors"][0]):
            raise AssertionError

    def test_validate_sheet_consistency_column_mismatch(self) -> None:
        """Test sheet consistency validation with column mismatch."""
        # Create test DataFrames with different columns
        df_parquet = pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [10, 20, 30],
            },
        )

        df_csv = pl.DataFrame(
            {
                "A": [1, 2, 3],
                "C": [10, 20, 30],  # Different column name
            },
        )

        result = self.validator.validate_sheet_consistency(
            "Test Sheet",
            df_parquet,
            df_csv,
        )

        if result["passed"]:
            raise AssertionError
        if ("Column names mismatch") not in (result["errors"][0]):
            raise AssertionError

    def test_validate_cross_sheet_references(self) -> None:
        """Test cross-sheet reference validation."""
        # Mock the data manager to return a DataFrame for one sheet and None for another
        self.mock_data_manager.load_sheet.side_effect = [
            pl.DataFrame({"A": [1, 2, 3]}),  # Found sheet
            None,  # Missing sheet
        ]

        referenced_sheets = ["Found Sheet", "Missing Sheet"]
        result = self.validator.validate_cross_sheet_references(
            "Test Sheet",
            pl.DataFrame(),
            referenced_sheets,
        )

        require_runtime_instance(result, dict)
        require_keys(result, ("sheet_name",))
        require_keys(result, ("passed",))
        require_keys(result, ("errors",))
        require_keys(result, ("warnings",))
        require_keys(result, ("referenced_sheets_found",))
        require_keys(result, ("referenced_sheets_missing",))

        require_equal(result["sheet_name"], "Test Sheet")
        require(
            condition=not (result["passed"]),
        )  # Should fail because one sheet is missing
        require_equal(len(result["errors"]), 1)
        require_keys(
            result["errors"][0],
            ("Referenced sheet 'Missing Sheet' not found",),
        )
        require_equal(result["referenced_sheets_found"], ["Found Sheet"])
        require_equal(result["referenced_sheets_missing"], ["Missing Sheet"])

    def test_validate_data_ranges(self) -> None:
        """Test data range validation."""
        df = pl.DataFrame(
            {
                "A": [1, 2, 3, 4, 5],
                "B": [10, 20, 30, 40, 50],
            },
        )

        expected_ranges: dict[str, tuple[float, float]] = {
            "A": (1, 5),
            "B": (10, 50),
        }

        result = self.validator.validate_data_ranges("Test Sheet", df, expected_ranges)

        require_runtime_instance(result, dict)
        require_keys(result, ("sheet_name",))
        require_keys(result, ("passed",))
        require_keys(result, ("errors",))
        require_keys(result, ("warnings",))
        require_keys(result, ("columns_checked",))

        require_equal(result["sheet_name"], "Test Sheet")
        require(condition=result["passed"])
        require_equal(len(result["errors"]), 0)
        require_equal(len(result["warnings"]), 0)
        require_keys(result["columns_checked"], ("A",))
        require_keys(result["columns_checked"], ("B",))

    def test_validate_data_ranges_out_of_bounds(self) -> None:
        """Test data range validation with out-of-bounds values."""
        df = pl.DataFrame(
            {
                "A": [1, 2, 3, 4, 10],  # 10 is out of bounds (1,5)
                "B": [10, 20, 30, 40, 50],
            },
        )

        expected_ranges: dict[str, tuple[float, float]] = {
            "A": (1, 5),
            "B": (10, 50),
        }

        result = self.validator.validate_data_ranges("Test Sheet", df, expected_ranges)

        if not (result["passed"]):
            raise AssertionError  # Still passes but with warning
        if not ((len(result["warnings"])) == (1)):
            raise AssertionError
        if ("Column 'A' has 1 values outside expected range [1, 5]") not in (
            result["warnings"][0]
        ):
            raise AssertionError

    def test_validate_unique_constraints(self) -> None:
        """Test unique constraint validation."""
        df = pl.DataFrame(
            {
                "A": [1, 2, 3, 4, 5],  # All unique
                "B": [10, 20, 30, 40, 50],  # All unique
            },
        )

        unique_columns = ["A", "B"]

        result = self.validator.validate_unique_constraints(
            "Test Sheet",
            df,
            unique_columns,
        )

        require_runtime_instance(result, dict)
        require_keys(result, ("sheet_name",))
        require_keys(result, ("passed",))
        require_keys(result, ("errors",))
        require_keys(result, ("warnings",))
        require_keys(result, ("columns_checked",))

        require_equal(result["sheet_name"], "Test Sheet")
        require(condition=result["passed"])
        require_equal(len(result["errors"]), 0)
        require_keys(result["columns_checked"], ("A",))
        require_keys(result["columns_checked"], ("B",))

    def test_validate_unique_constraints_duplicates(self) -> None:
        """Test unique constraint validation with duplicates."""
        df = pl.DataFrame(
            {
                "A": [1, 2, 2, 4, 5],  # Has duplicate (2)
                "B": [10, 20, 30, 40, 50],  # All unique
            },
        )

        unique_columns = ["A", "B"]

        result = self.validator.validate_unique_constraints(
            "Test Sheet",
            df,
            unique_columns,
        )

        if result["passed"]:
            raise AssertionError
        if not ((len(result["errors"])) == (1)):
            raise AssertionError
        if ("Column 'A' has 1 duplicate values (should be unique)") not in (
            result["errors"][0]
        ):
            raise AssertionError
        if ("A") not in (result["columns_checked"]):
            raise AssertionError
        if ("B") not in (result["columns_checked"]):
            raise AssertionError

    def test_generate_validation_report(self) -> None:
        """Test validation report generation."""
        # Mock the data manager
        self.mock_data_manager.list_available_sheets.return_value = {
            "test_sheet": ["parquet", "csv"],
        }
        self.mock_data_manager.load_sheet.return_value = pl.DataFrame({"A": [1, 2, 3]})

        # Generate report
        report = self.validator.generate_validation_report()

        # Check that report is generated
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Data Consistency Validation") not in (report):
            raise AssertionError
        if ("Validation Results by Sheet") not in (report):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
