"""Test for 3. Estimates table (prepared data only)."""

import pandas as pd
import pytest
from pathlib import Path


def test_3_estimates_loading():
    """Test that the 3. Estimates table can be loaded successfully from prepared data."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert len(df.columns) > 0
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}")
        return df
    else:
        pytest.skip("Prepared data for 3. Estimates not found")


def test_3_estimates_data_integrity():
    """Test data integrity for 3. Estimates table."""
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        
        # Check for reasonable data types
        assert len(df.columns) > 0
        
        # Check for null values (should be reasonable amount)
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        null_percentage = null_cells / total_cells if total_cells > 0 else 0
        
        # Allow up to 50% null values (this might need adjustment based on the table)
        # For estimates, we expect more null values as not all estimates apply to all categories
        assert null_percentage < 0.5, f"Too many null values: {null_percentage:.2%}"
        
        print("Data integrity check passed for 3. Estimates")
        print(f"  - Null value percentage: {null_percentage:.2%}")
    else:
        pytest.skip("Prepared data for 3. Estimates not found")


def test_3_estimates_schema_consistency():
    """Test schema consistency for 3. Estimates table."""
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        
        # Check that we have columns
        assert len(df.columns) > 0
        
        # Check for duplicate column names
        columns_list = list(df.columns)
        assert len(columns_list) == len(set(columns_list)), "Duplicate column names found"
        
        print("Schema consistency check passed for 3. Estimates")
    else:
        pytest.skip("Prepared data for 3. Estimates not found")


if __name__ == "__main__":
    try:
        df = test_3_estimates_loading()
        test_3_estimates_data_integrity()
        test_3_estimates_schema_consistency()
        print("All tests passed!")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()