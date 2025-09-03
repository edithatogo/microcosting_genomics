"""Test for Detailed Table table transfer and validation."""

import pandas as pd
import pytest
from pathlib import Path


def test_detailed_table_loading():
    """Test that the Detailed Table table can be loaded successfully."""
    # Test loading from prepared data
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
    if prepared_path.exists():
        df = pd.read_parquet(prepared_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert len(df.columns) > 0
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns from {prepared_path}")
    else:
        # Try alternative names
        alternatives = [
            "detailed_table",
            "Detailed_Table",
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
            pytest.skip(f"Prepared data for Detailed Table not found")


def test_detailed_table_data_integrity():
    """Test data integrity for Detailed Table table."""
    prepared_path = Path("data/prepared") / "detailed_table.parquet"
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
        
        print(f"Data integrity check passed for Detailed Table")
        print(f"  - Null value percentage: {null_percentage:.2%}")
    else:
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "detailed_table" in f.name:
                df = pd.read_parquet(f)
                # Check for reasonable data types
                assert len(df.columns) > 0
                
                # Check for null values (should be reasonable amount)
                total_cells = df.shape[0] * df.shape[1]
                null_cells = df.isnull().sum().sum()
                null_percentage = null_cells / total_cells if total_cells > 0 else 0
                
                # Allow up to 50% null values (this might need adjustment based on the table)
                assert null_percentage < 0.5, f"Too many null values: {null_percentage:.2%}"
                
                print(f"Data integrity check passed for Detailed Table")
                print(f"  - Null value percentage: {null_percentage:.2%}")
                found = True
                break
        if not found:
            pytest.skip(f"Prepared data for Detailed Table not found")


def test_detailed_table_schema_consistency():
    """Test schema consistency for Detailed Table table."""
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
        # Try to find the file
        found = False
        for f in Path("data/prepared").glob("*.parquet"):
            if "detailed_table" in f.name:
                df = pd.read_parquet(f)
                # Check that we have columns
                assert len(df.columns) > 0
                
                # Check for duplicate column names
                columns_list = list(df.columns)
                assert len(columns_list) == len(set(columns_list)), "Duplicate column names found"
                
                print(f"Schema consistency check passed for Detailed Table")
                found = True
                break
        if not found:
            pytest.skip(f"Prepared data for Detailed Table not found")


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
