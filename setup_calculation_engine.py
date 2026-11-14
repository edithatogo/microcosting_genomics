# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Initialize the calculation engine for manual analysis."""

import sys

from genomics_microcosting.calculation_engine import CalculationEngine


def setup_engine() -> CalculationEngine:
    """Initialize and sets up the calculation engine."""
    sys.stdout.writelines(("Setting up the calculation engine...", "\n"))
    engine = CalculationEngine()
    sys.stdout.writelines(("Calculation engine setup complete.", "\n"))
    sys.stdout.writelines((f"Loaded sheets: {engine.get_sheet_names()}", "\n"))
    return engine


if __name__ == "__main__":
    engine = setup_engine()
    # The 'engine' object is now ready for use.
    # You can now interact with it, for example, by getting data from a sheet:
