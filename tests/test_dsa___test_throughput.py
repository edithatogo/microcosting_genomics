"""Test for DSA - Test Throughput table transfer and validation."""

import pandas as pd
import pytest
from pathlib import Path


def test_dsa___test_throughput_loading():
    """Test that the DSA - Test Throughput table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "dsa___test_throughput.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert len(df.columns) > 0
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}")
    else:
        # Try alternative names
        alternatives = [
            "dsa---test-throughput",
            "dsa   test throughput",
            "DSA - Test Throughput"
        ]
        found = False
        for alt in alternatives:
            prepared_path = Path("data/prepared") / f"{alt}.parquet"
            if prepared_path.exists():
                df = pd.read_parquet(prepared_path)
                assert isinstance(df, pd.DataFrame)
                assert len(df) > 0
                assert len(df.columns) > 0
                print(f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}")
                found = True
                break
        if not found:
            pytest.skip(f"Prepared data for DSA - Test Throughput not found")


def test_dsa___test_throughput_data_integrity():
    """Test data integrity for DSA - Test Throughput table."""
    prepared_path = Path("data/prepared") / "dsa___test_throughput.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        
        # Check for reasonable data types
        assert len(df.columns) > 0
        
        # Check for null values (should be reasonable amount)
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        null_percentage = null_cells / total_cells if total_cells > 0 else 0
        
        # Allow up to 50% null values (this might need adjustment based on the table)
        assert null_percentage < 0.5, f"Too many null values: {null_percentage:.2%}"
        
        print(f"Data integrity check passed for DSA - Test Throughput")
        print(f"  - Null value percentage: {null_percentage:.2%}")
    else:
        pytest.skip(f"Prepared data for DSA - Test Throughput not found")


def test_dsa___test_throughput_schema_consistency():
    """Test schema consistency for DSA - Test Throughput table."""
    prepared_path = Path("data/prepared") / "dsa___test_throughput.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        
        # Check that we have columns
        assert len(df.columns) > 0
        
        # Check for duplicate column names
        columns_list = list(df.columns)
        assert len(columns_list) == len(set(columns_list)), "Duplicate column names found"
        
        print(f"Schema consistency check passed for DSA - Test Throughput")
    else:
        pytest.skip(f"Prepared data for DSA - Test Throughput not found")


if __name__ == "__main__":
    try:
        test_dsa___test_throughput_loading()
        test_dsa___test_throughput_data_integrity()
        test_dsa___test_throughput_schema_consistency()
        print("All tests passed!")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
