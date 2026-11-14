# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Tests for DataManager multi-level header parsing functionality.

This module implements TDD tests for the DataManager's _fix_duplicate_columns method,
which handles multi-level headers from Excel files.
"""

import tempfile
from pathlib import Path

from genomics_microcosting.data_manager import DataManager
from tests.checks import require_equal, require_runtime_instance
from tests.header_fixtures import HeaderFixture


class TestDataManagerMultiLevelHeaders:
    """Test cases for multi-level header parsing in DataManager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create DataManager instance
        self.dm = DataManager(self.data_dir)

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_fix_duplicate_columns_regular_index(self) -> None:
        """Test _fix_duplicate_columns with regular (single-level) column index."""
        # Create test DataFrame with unique initial column names
        df = HeaderFixture(
            {
                "Col1": [1, 2, 3],
                "Col2": [7, 8, 9],
            },
        )

        # Manually set duplicate column names to test our logic
        df.columns = ["Test", "Test"]

        # Fix duplicate columns
        result = self.dm.normalize_headers(df)

        # Verify column names are made unique
        expected_columns = ["Test", "Test_2"]
        require_equal(list(result.columns), expected_columns)

        # Verify data integrity
        require_equal(result[0, 0], 1)  # First 'Test' column
        require_equal(result[0, 1], 7)  # Second 'Test' column (renamed to Test_2)
        require_equal(result[1, 0], 2)
        require_equal(result[1, 1], 8)

        # Verify data integrity
        require_equal(result[0, 0], 1)  # First 'Test' column
        require_equal(result[0, 1], 7)  # Second 'Test' column (renamed to Test_2)
        require_equal(result[1, 0], 2)
        require_equal(result[1, 1], 8)

    def test_fix_duplicate_columns_multiindex_simple(self) -> None:
        """Test _fix_duplicate_columns with simple MultiIndex columns."""
        # Create MultiIndex columns
        columns = [
            ("Test", "Test"),
            ("Category", "Category"),
            ("Sub-Category", "Sub-Category"),
            ("Step", "Step"),
        ]

        df = HeaderFixture([[1, 2, 3, 4]], columns=columns)

        # Fix duplicate columns
        result = self.dm.normalize_headers(df)

        # Verify MultiIndex is converted to regular index
        require_runtime_instance(result.columns, list)
        for column in result.columns:
            require_runtime_instance(column, str)

        # Verify column names are properly joined
        expected_columns = [
            "Test_Test",
            "Category_Category",
            "Sub-Category_Sub-Category",
            "Step_Step",
        ]
        require_equal(list(result.columns), expected_columns)

        # Verify data integrity
        require_equal(result[0, 0], 1)
        require_equal(result[0, 1], 2)
        require_equal(result[0, 2], 3)
        require_equal(result[0, 3], 4)

    def test_fix_duplicate_columns_multiindex_with_nulls(self) -> None:
        """Test _fix_duplicate_columns with MultiIndex containing null values."""
        # Create MultiIndex with some null values (common in Excel multi-level headers)
        columns = [
            ("Test", float("nan")),
            (float("nan"), "Category"),
            ("Sub-Category", "Sub-Category"),
            ("Step", "Step"),
        ]

        df = HeaderFixture([[1, 2, 3, 4]], columns=columns)

        # Fix duplicate columns
        result = self.dm.normalize_headers(df)

        # Verify null parts are excluded from joined names
        expected_columns = [
            "Test",
            "Category",
            "Sub-Category_Sub-Category",
            "Step_Step",
        ]
        require_equal(list(result.columns), expected_columns)

    def test_fix_duplicate_columns_multiindex_complex(self) -> None:
        """Test _fix_duplicate_columns with complex MultiIndex scenario."""
        # Simulate real Excel multi-level headers from genomics data
        columns = [
            ("Test Test", "Test Test"),
            ("Category Category", "Category Category"),
            ("Sub-Category Sub-Category", "Sub-Category Sub-Category"),
            ("Step Step", "Step Step"),
            ("Estimates", "Quantity of Use per Test LL"),
            ("Estimate", ""),
            ("UL", ""),
            ("Source", ""),
            ("Price (AUD $/unit)", "LL"),
            ("Estimate_2", ""),
            ("UL_2", ""),
            ("Source_2", ""),
            ("Unit Cost (AUD $/unit)", "LL"),
            ("Estimate_3", ""),
            ("UL_3", ""),
            ("DSA DSA", "LL"),
            ("Estimate_4", ""),
            ("UL_4", ""),
            ("LL", ""),
            ("Estimate_5", ""),
            ("UL_5", ""),
            ("LL_2", ""),
            ("Estimate_6", ""),
            ("UL_6", ""),
            ("LL_3", ""),
            ("Estimate_7", ""),
            ("UL_7", ""),
        ]

        # Create sample data similar to ground truth
        data = [
            [
                None,
                None,
                None,
                None,
                0.5,
                926,
                663,
                None,
                831,
                921,
                831,
                None,
                940,
                1014,
                940,
                682,
                682,
                682,
                682,
                682,
                682,
                264,
                264,
                264,
                264,
                264,
                264,
            ],
        ]
        df = HeaderFixture(data, columns=columns)

        # Fix duplicate columns
        result = self.dm.normalize_headers(df)

        # Verify conversion worked
        require_runtime_instance(result.columns, list)
        for column in result.columns:
            require_runtime_instance(column, str)

        # Check some key columns
        if "Test Test_Test Test" not in result.columns:
            raise AssertionError
        if "Category Category_Category Category" not in result.columns:
            raise AssertionError
        if "Unit Cost (AUD $/unit)_LL" not in result.columns:
            raise AssertionError
        if "Estimate" not in result.columns:
            raise AssertionError  # Empty string should be ignored
        if "UL" not in result.columns:
            raise AssertionError

        # Verify we have the right number of columns
        require_equal(len(result.columns), 27)

    def test_fix_duplicate_columns_empty_multiindex(self) -> None:
        """Test _fix_duplicate_columns with empty MultiIndex."""
        # Create empty DataFrame with MultiIndex columns
        columns: list[tuple[object, ...]] = []
        df = HeaderFixture(columns=columns)

        result = self.dm.normalize_headers(df)

        # Should handle empty case gracefully
        require_equal(len(result.columns), 0)

    def test_fix_duplicate_columns_mixed_types(self) -> None:
        """Test _fix_duplicate_columns with mixed data types in MultiIndex."""
        # Create MultiIndex with mixed types
        columns = [("Test", 1.0), ("Category", 2.5), ("Sub-Category", 1.0)]

        df = HeaderFixture([[1, 2, 3]], columns=columns)

        result = self.dm.normalize_headers(df)

        # Should convert all parts to strings and join
        # Note: pandas converts boolean True to 1.0 in MultiIndex
        expected_columns = ["Test_1", "Category_2.5", "Sub-Category_1"]
        require_equal(list(result.columns), expected_columns)

    def test_fix_duplicate_columns_preserves_data_integrity(self) -> None:
        """Test that _fix_duplicate_columns preserves data integrity."""
        # Create test data with known values
        original_data = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
        columns = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E")]

        df = HeaderFixture(original_data, columns=columns)

        result = self.dm.normalize_headers(df)

        # Verify all data is preserved
        require_equal(result.shape, (2, 5))
        require_equal(list(result.row(0)), [1, 2, 3, 4, 5])
        require_equal(list(result.row(1)), [6, 7, 8, 9, 10])

    def test_fix_duplicate_columns_error_handling(self) -> None:
        """Test _fix_duplicate_columns error handling."""
        # Create problematic MultiIndex that might cause issues
        columns = [("Test", "Test"), ("Bad", float("nan")), ("Category", "Category")]

        df = HeaderFixture([[1, 2, 3]], columns=columns)

        # Should handle NaN gracefully
        result = self.dm.normalize_headers(df)

        # Should have fallback column names
        require_equal(len(result.columns), 3)
        require_equal(result[0, 0], 1)
        require_equal(result[0, 1], 2)
        require_equal(result[0, 2], 3)
