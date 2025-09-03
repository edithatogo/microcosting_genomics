#!/usr/bin/env python3
"""
Script to list all sheets in the Excel workbook and their basic information.
"""

import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
import json


def list_excel_sheets():
    """List all sheets in the Excel workbook."""
    # Try to find the Excel file
    possible_paths = [
        'data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm',
        'data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx'
    ]
    
    excel_file_path = None
    for path in possible_paths:
        if Path(path).exists():
            excel_file_path = path
            break
    
    if not excel_file_path:
        print("No Excel file found")
        return
    
    print(f"Found Excel file: {excel_file_path}")
    
    # Load the workbook
    wb = load_workbook(excel_file_path, read_only=True, data_only=True)
    
    print(f"\nAvailable sheets ({len(wb.sheetnames)} total):")
    print("=" * 50)
    
    sheet_info = []
    
    for i, sheet_name in enumerate(wb.sheetnames, 1):
        try:
            ws = wb[sheet_name]
            # Get dimensions
            rows = ws.max_row
            cols = ws.max_column
            
            # Get first few cells to understand structure
            first_row = []
            for col in range(1, min(6, cols + 1)):  # First 5 columns
                cell_value = ws.cell(row=1, column=col).value
                first_row.append(str(cell_value) if cell_value is not None else "")
            
            info = {
                "index": i,
                "name": sheet_name,
                "dimensions": f"{rows} rows × {cols} columns",
                "first_row": first_row
            }
            sheet_info.append(info)
            
            print(f"{i:2d}. {sheet_name}")
            print(f"     Dimensions: {rows} rows × {cols} columns")
            print(f"     First row: {', '.join(first_row[:3])}")
            if len(first_row) > 3:
                print(f"                ... and {len(first_row) - 3} more columns")
            print()
            
        except Exception as e:
            print(f"{i:2d}. {sheet_name} - Error: {e}")
            continue
    
    wb.close()
    
    # Save sheet information to JSON
    output_file = "data/metadata/excel_sheets_info.json"
    with open(output_file, 'w') as f:
        json.dump(sheet_info, f, indent=2)
    print(f"Sheet information saved to {output_file}")


if __name__ == "__main__":
    list_excel_sheets()