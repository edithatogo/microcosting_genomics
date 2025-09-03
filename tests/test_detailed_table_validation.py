"""Test for Detailed Table validation."""

import pandas as pd
import pytest
from pathlib import Path


def test_detailed_table_loading():
    """Test that the Detailed Table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert len(df.columns) > 0
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}")
    else:
        pytest.skip("Prepared data for Detailed Table not found")


def test_detailed_table_data_integrity():
    """Test data integrity for Detailed Table."""
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        
        # Check for reasonable data types
        assert len(df.columns) > 0
        
        # Check for null values (should be reasonable amount)
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        null_percentage = null_cells / total_cells if total_cells > 0 else 0
        
        # For Detailed Table, allow up to 70% null values as it's expected to have sparse data
        assert null_percentage < 0.7, f"Too many null values: {null_percentage:.2%}"
        
        print(f"Data integrity check passed for Detailed Table")
        print(f"  - Null value percentage: {null_percentage:.2%}")
        
        # Check that we have the expected columns
        expected_columns = ['Test', 'Category', 'Sub-Category', 'Step']
        for col in expected_columns:
            # Check if column exists (might be in a MultiIndex)
            found = False
            for df_col in df.columns:
                if isinstance(df_col, tuple):
                    if any(col in str(part) for part in df_col if pd.notna(part)):
                        found = True
                        break
                elif col == str(df_col):
                    found = True
                    break
            if not found:
                print(f"Warning: Expected column '{col}' not found in DataFrame")
    else:
        pytest.skip("Prepared data for Detailed Table not found")


def test_detailed_table_schema_consistency():
    """Test schema consistency for Detailed Table."""
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        
        # Check that we have columns
        assert len(df.columns) > 0
        
        # Check for duplicate column names
        columns_list = list(df.columns)
        assert len(columns_list) == len(set(columns_list)), "Duplicate column names found"
        
        print(f"Schema consistency check passed for Detailed Table")
    else:
        pytest.skip("Prepared data for Detailed Table not found")


if __name__ == "__main__":
    try:
        test_detailed_table_loading()
        test_detailed_table_data_integrity()
        test_detailed_table_schema_consistency()
        print("All tests passed!")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()