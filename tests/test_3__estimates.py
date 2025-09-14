"""Test for 3. Estimates table transfer and validation."""

import pandas as pd
import pytest
from pathlib import Path


def test_3__estimates_loading():
    """Test that the 3. Estimates table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "3._estimates.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert len(df.columns) > 0
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}")
    else:
        # Try alternative names
        alternatives = [
            "3._estimates",
            "3._Estimates",
        ]
        found = False
        for alt in alternatives:
            # Try different extensions
            for ext in [".parquet"]:
                prepared_path = Path("data/prepared") / f"{alt}{ext}"
                if prepared_path.exists():
                    df = pd.read_parquet(prepared_path)
                    assert isinstance(df, pd.DataFrame)
                    assert len(df) > 0
                    assert len(df.columns) > 0
                    print(f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}")
                    found = True
                    break
            if found:
                break
        if not found:
            # List available files for debugging
            print("Available prepared files:")
            for f in Path("data/prepared").glob("*.parquet"):
                print(f"  - {f.name}")
            pytest.skip("Prepared data for 3. Estimates not found")


def test_3__estimates_data_integrity():
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
        assert null_percentage < 0.5, f"Too many null values: {null_percentage:.2%}"
        
        print("Data integrity check passed for 3. Estimates")
        print(f"  - Null value percentage: {null_percentage:.2%}")
    else:
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "3._estimates" in f.name:
                df = pd.read_parquet(f)
                # Check for reasonable data types
                assert len(df.columns) > 0
                
                # Check for null values (should be reasonable amount)
                total_cells = df.shape[0] * df.shape[1]
                null_cells = df.isnull().sum().sum()
                null_percentage = null_cells / total_cells if total_cells > 0 else 0
                
                # Allow up to 50% null values (this might need adjustment based on the table)
                assert null_percentage < 0.5, f"Too many null values: {null_percentage:.2%}"
                
                print("Data integrity check passed for 3. Estimates")
                print(f"  - Null value percentage: {null_percentage:.2%}")
                found = True
                break
        if not found:
            pytest.skip("Prepared data for 3. Estimates not found")


def test_3__estimates_schema_consistency():
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
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "3._estimates" in f.name:
                df = pd.read_parquet(f)
                # Check that we have columns
                assert len(df.columns) > 0
                
                # Check for duplicate column names
                columns_list = list(df.columns)
                assert len(columns_list) == len(set(columns_list)), "Duplicate column names found"
                
                print("Schema consistency check passed for 3. Estimates")
                found = True
                break
        if not found:
            pytest.skip("Prepared data for 3. Estimates not found")


if __name__ == "__main__":
    try:
        test_3__estimates_loading()
        test_3__estimates_data_integrity()
        test_3__estimates_schema_consistency()
        print("All tests passed!")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
