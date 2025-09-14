#!/usr/bin/env python3
"""
Standardized script for preparing all sheets consistently.

This script provides a consistent approach for handling all sheets in the microcosting analysis,
ensuring that all sheets are treated uniformly regardless of their source or purpose.
"""

import sys
from pathlib import Path
import pandas as pd

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.data_manager import DataManager  # noqa: E402
from genomics_microcosting.sheet_manager import SheetManager  # noqa: E402


def create_sheet_metadata(df: pd.DataFrame, sheet_name: str) -> dict:
    """Create metadata for a sheet.

    Args:
        df (pd.DataFrame): DataFrame containing the sheet data
        sheet_name (str): Name of the sheet

    Returns:
        dict: Metadata about the sheet
    """
    metadata = {
        "sheet_name": sheet_name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [],
        "data_types": {},
        "null_counts": {},
        "memory_usage_bytes": df.memory_usage(deep=True).sum()
    }
    
    for col in df.columns:
        metadata["columns"].append(str(col))
        metadata["data_types"][str(col)] = str(df[col].dtype)
        metadata["null_counts"][str(col)] = int(df[col].isnull().sum())
        
    return metadata


def prepare_sheet(sheet_name: str, sheet_manager: SheetManager, 
                 data_manager: DataManager) -> bool:
    """Prepare a single sheet with consistent handling.

    Args:
        sheet_name (str): Name of the sheet to prepare
        sheet_manager (SheetManager): Sheet manager instance
        data_manager (DataManager): Data manager instance

    Returns:
        bool: True if successfully prepared, False otherwise
    """
    print(f"Preparing sheet: {sheet_name}")
    
    try:
        # Load data from Excel
        df = sheet_manager.get_data(sheet_name)
        if df is None:
            print(f"  Failed to load data for sheet '{sheet_name}'")
            return False
            
        print(f"  Loaded data with shape {df.shape}")
        
        # Save in consistent formats
        success = data_manager.save_sheet(sheet_name, df, formats=["parquet", "csv"])
        
        if success:
            # Create and save metadata
            metadata = create_sheet_metadata(df, sheet_name)
            publication_success = data_manager.save_for_publication(sheet_name, df, metadata)
            
            if publication_success:
                print(f"  Successfully prepared sheet '{sheet_name}'")
                return True
            else:
                print(f"  Prepared sheet '{sheet_name}' but failed to save for publication")
                return False
        else:
            print(f"  Failed to save sheet '{sheet_name}'")
            return False
            
    except Exception as e:
        print(f"  Error preparing sheet '{sheet_name}': {e}")
        return False


def main():
    """Main function to prepare all sheets consistently."""
    print("Preparing all sheets with consistent approach...")
    print("=" * 50)
    
    try:
        # Initialize managers
        sheet_manager = SheetManager()
        data_manager = DataManager()
        
        # Get list of sheets to process
        sheet_names = sheet_manager.get_sheet_names()
        
        if not sheet_names:
            print("No sheets found to process!")
            return 1
            
        print(f"Found {len(sheet_names)} sheets to process:")
        for name in sheet_names:
            print(f"  - {name}")
        print()
        
        # Process each sheet
        success_count = 0
        for sheet_name in sheet_names:
            if prepare_sheet(sheet_name, sheet_manager, data_manager):
                success_count += 1
            print()
            
        print("=" * 50)
        print(f"Preparation complete: {success_count}/{len(sheet_names)} sheets processed successfully")
        
        # Show available sheets
        available_sheets = data_manager.list_available_sheets()
        print("\nAvailable sheets in prepared directory:")
        for sheet, formats in available_sheets.items():
            print(f"  - {sheet}: {', '.join(formats)}")
            
        return 0 if success_count == len(sheet_names) else 1
        
    except Exception as e:
        print(f"Error in main preparation process: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())