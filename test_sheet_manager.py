#!/usr/bin/env python3

from src.genomics_microcosting.sheet_manager import SheetManager
from pathlib import Path

# Test sheet manager formula access
sheet_manager = SheetManager(
    excel_file_path="data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
)

sheet_name = "BI - Comp Stor Costs - VCGS"
print(f"Testing sheet: {sheet_name}")

# Check if sheet exists in config
if sheet_name in sheet_manager.sheet_configs:
    print("✓ Sheet found in configuration")
    config = sheet_manager.sheet_configs[sheet_name]
    print(f"  Config: {config}")
else:
    print("✗ Sheet NOT found in configuration")
    print(f"  Available sheets: {list(sheet_manager.sheet_configs.keys())}")

# Try to get formula data
print(f"\nTrying to get formula data for {sheet_name}...")
formulas_df = sheet_manager.get_formulas(sheet_name)
if formulas_df is not None:
    print("✓ Formula data loaded successfully")
    print(f"  Shape: {formulas_df.shape}")
    print(f"  Columns: {list(formulas_df.columns[:5])}...")  # First 5 columns
else:
    print("✗ Failed to load formula data")

# Try to get a specific cell formula
print("\nTrying to get formula for cell V3...")
try:
    formula = sheet_manager.get_formulas(sheet_name)
    if formula is not None and len(formula) > 2:  # Row 3 (0-indexed as 2)
        # Convert column V to index (V is the 22nd column, 0-indexed as 21)
        col_idx = ord('V') - ord('A')  # V = 21
        if col_idx < len(formula.columns):
            cell_formula = formula.iloc[2, col_idx]  # Row 3, Column V
            print(f"  Cell V3 formula: {cell_formula}")
        else:
            print(f"  Column V (index {col_idx}) out of bounds")
    else:
        print("  Formula dataframe too small or None")
except Exception as e:
    print(f"  Error getting cell formula: {e}")