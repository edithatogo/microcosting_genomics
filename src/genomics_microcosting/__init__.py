# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Native Polars tools for source-backed genomics microcosting.

CalculationEngine evaluates supported workbook formulas through SheetManager,
formula_parser and calculation strategies. DataManager handles native tables;
analysis, reporting, visualization and Flask modules provide consumer interfaces.
Qualification limits and source-oracle exceptions are recorded in Conductor.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("genomics-microcosting")
except PackageNotFoundError:
    __version__ = "0+uninstalled"
__author__ = "University of Melbourne PhD Researcher"
