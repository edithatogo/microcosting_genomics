"""University of Melbourne PhD (Economics of Rare Disease Genomics) - Phase 1 Microcosting Genomics.

This package provides tools for programmatically validating and analyzing economic calculations
from Excel-based microcosting models. It includes a calculation engine that parses Excel formulas
and recreates results so they can be tested and validated programmatically.

Modules:
    calculation_engine: Main calculation engine for processing Excel formulas
    config: Configuration loading and management
    data_management: Data loading and management utilities
    excel_utils: Excel file handling utilities
    excel_version_control: Excel workbook version control utilities
    formula_parser: Excel formula parsing utilities
    logging_config: Logging configuration
    performance: Performance monitoring and optimization
    plugin_system: Plugin system for extending functionality
    scenario_modeling: Scenario modeling tools for what-if analysis
    sheet_manager: Sheet loading and management
    strategies: Formula calculation strategies
    utils: General utility functions
    visualization: Data visualization tools
    web: Web interface for non-technical users
    web_viz: Web-based visualization utilities

The main components of this package are:
- CalculationEngine: Parses and executes Excel formulas
- SheetManager: Manages loading data from Excel sheets and Parquet files
- FormulaParser: Parses Excel formulas into structured representations
- Strategies: Implements different calculation approaches for various formula types
- Visualization: Provides plotting functions for data analysis
- Web interface: Flask-based web application for data exploration
"""

__version__ = "1.0.0"
__author__ = "University of Melbourne PhD Researcher"