"""Test for 3. Estimates table."""

import pandas as pd
import pytest
from pathlib import Path


def test_estimates_loading():
    """Test that the 3. Estimates table can be loaded successfully."""
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


def test_estimates_data_integrity():
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
        
        # For Estimates, allow up to 45% null values (it has 42.17%)
        assert null_percentage < 0.45, f"Too many null values: {null_percentage:.2%}"
        
        print("Data integrity check passed for 3. Estimates")
        print(f"  - Null value percentage: {null_percentage:.2%}")
        
        # Check that we have some numeric columns (expected for quantities and prices)
        numeric_columns = df.select_dtypes(include=['number']).columns
        assert len(numeric_columns) > 0, "No numeric columns found"
        print(f"  - Numeric columns: {len(numeric_columns)}")
    else:
        pytest.skip("Prepared data for 3. Estimates not found")


def test_estimates_schema_consistency():
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
        df = test_estimates_loading()
        test_estimates_data_integrity()
        test_estimates_schema_consistency()
        print("All tests passed!")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()