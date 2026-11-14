#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0


"""Inspect prepared data and worksheet mappings."""

import sys

from src.genomics_microcosting.sheet_manager import SheetManager

# Test sheet manager formula access
sheet_manager = SheetManager(
    excel_file_path=(
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    ),
)

sheet_name = "BI - Comp+Stor Costs - VCGS"
sys.stdout.writelines((f"Testing sheet: {sheet_name}", "\n"))

# Check if sheet exists in config
if sheet_name in sheet_manager.sheet_configs:
    sys.stdout.writelines(("✓ Sheet found in configuration", "\n"))
    config = sheet_manager.sheet_configs[sheet_name]
    sys.stdout.writelines((f"  Config: {config}", "\n"))
else:
    sys.stdout.writelines(("✗ Sheet NOT found in configuration", "\n"))
    sys.stdout.writelines(
        (f"  Available sheets: {list(sheet_manager.sheet_configs.keys())}", "\n"),
    )

# Try to get formula data
sys.stdout.writelines((f"\nTrying to get formula data for {sheet_name}...", "\n"))
formulas_df = sheet_manager.get_formulas(sheet_name)
if formulas_df is not None:
    sys.stdout.writelines(("✓ Formula data loaded successfully", "\n"))
    sys.stdout.writelines((f"  Shape: {formulas_df.shape}", "\n"))
    sys.stdout.writelines(
        (f"  Columns: {list(formulas_df.columns[:5])}...", "\n"),
    )  # First 5 columns
else:
    sys.stdout.writelines(("✗ Failed to load formula data", "\n"))
