#!/usr/bin/env python3

from src.unimelb_phd_phase_1.sheet_manager import SheetManager
from pathlib import Path

# Test sheet manager formula access
sheet_manager = SheetManager(
    excel_file_path="data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
)

sheet_name = "BI - Comp+Stor Costs - VCGS"
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