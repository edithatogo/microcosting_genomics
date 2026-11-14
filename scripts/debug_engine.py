# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""List the sheets loaded by the calculation engine."""

import sys

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager

if __name__ == "__main__":
    manager = SheetManager()
    engine = CalculationEngine(manager)
    sys.stdout.write(f"Loaded sheets: {list(engine.sheets)}\n")
