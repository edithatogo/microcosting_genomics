# Repository Structure

This document provides a comprehensive overview of the repository structure and organization.

## Root Directory

```
microcosting_genomics/
├── .github/                    # GitHub workflows and configurations
├── .qoder/                     # Qoder-specific files and quests
├── data/                       # Input data and prepared files
├── docs/                       # Documentation files
├── manuscripts/                # Research manuscripts
├── notebooks/                  # Jupyter notebooks for analysis
├── publication/                # Publication-ready outputs
├── reports/                    # Generated reports and analyses
├── scripts/                    # Helper scripts and utilities
├── src/                        # Source code
├── tests/                      # Test suite
├── .editorconfig               # Editor configuration
├── .gitignore                  # Git ignore file
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
├── CHANGELOG.md                # Project changelog
├── config.yaml                 # Project configuration
├── LICENSE                     # License file
├── pyproject.toml              # Python project configuration
├── README.md                   # Main project documentation
└── requirements.txt            # Python requirements
```

## Source Code Directory

```
src/unimelb_phd_phase_1/
├── __init__.py                 # Package initialization
├── calculation_engine.py       # Main calculation engine
├── config.py                   # Configuration management
├── data_manager.py             # Unified data management
├── excel_utils.py              # Excel utilities
├── excel_version_control.py    # Excel version control
├── formula_parser.py           # Formula parsing
├── logging_config.py           # Logging configuration
├── performance.py              # Performance monitoring
├── plugin_system.py            # Base plugin system
├── enhanced_plugin_system.py   # Enhanced plugin system
├── sheet_manager.py            # Sheet management
├── strategies.py               # Formula execution strategies
├── utils.py                    # Utility functions
├── visualization.py            # Basic visualization
├── advanced_visualization.py   # Advanced visualization
├── web.py                      # Web interface
├── web_viz.py                  # Web visualization
├── scenario_modeling.py        # Basic scenario modeling
├── advanced_scenario_modeling.py # Advanced scenario modeling
├── plugins/                    # Plugin directory
│   ├── __init__.py
│   ├── example_cost_analysis.py
│   ├── enhanced_cost_analysis.py
│   └── sample_enhanced_plugin.py
├── static/                     # Static web assets
│   ├── style.css
│   └── scripts.js
└── templates/                  # HTML templates
    ├── base.html
    ├── index.html
    ├── table.html
    └── visualize.html
```

## Data Directory

```
data/
├── prepared/                   # Processed Parquet files
├── extracted/                  # Extracted data files
├── metadata/                   # Data metadata
├── replicated/                 # Replicated data files
└── [Excel workbooks]           # Original Excel files
```

## Documentation Directory

```
docs/
├── API_REFERENCE.md            # API reference documentation
├── CALCULATION_ENGINE.md       # Calculation engine documentation
├── DATA_MANAGEMENT.md          # Data management documentation
├── DEVELOPMENT_GUIDE.md        # Development guide
├── MODELS.md                   # Model descriptions
├── PLUGIN_SYSTEM.md            # Plugin system documentation
├── README.md                   # Documentation index
├── REPOSITORY_STRUCTURE.md     # Repository structure (this file)
├── SCENARIO_ANALYSIS.md        # Scenario analysis documentation
├── table_overview.md           # Table overview
└── WEB_INTERFACE.md            # Web interface documentation
```

## Scripts Directory

```
scripts/
├── analyze_scenarios.py                # Scenario analysis script
├── demonstrate_excel_version_control.py # Excel version control demo
├── demonstrate_plugins.py              # Plugin system demo
├── enhanced_reporting.py               # Enhanced reporting
├── generate_advanced_visualizations.py # Advanced visualizations
├── list_excel_sheets.py                # List Excel sheets
├── manage_data.py                      # Data management
├── parse_additional_tables.py          # Parse additional tables
├── parse_cost_tables.py                # Parse cost tables
├── prepare_all_sheets.py               # Prepare all sheets
├── prepare_publication_tables.py       # Prepare publication tables
├── prepare_reference_tables.py         # Prepare reference tables
├── profile_and_optimize.py             # Performance profiling
├── replicate_bi_comp_stor_costs.py     # Replicate bi comp stor costs
├── replicate_calculations.py           # Replicate calculations
├── replicate_consumable_costs.py       # Replicate consumable costs
├── replicate_detailed_table.py         # Replicate detailed table
├── replicate_equipment_costs.py        # Replicate equipment costs
├── replicate_labour_costs.py           # Replicate labour costs
├── run_advanced_scenario_analysis.py   # Run advanced scenario analysis
├── run_scenario_analysis.py            # Run scenario analysis
├── run_web.py                          # Run web interface
├── test_web_ui.py                      # Test web UI
├── transfer_validate_tables.py         # Transfer and validate tables
├── validate_all_sheets.py              # Validate all sheets
├── validate_bi_comp_stor_costs.py      # Validate bi comp stor costs
├── validate_calculation_engine.py      # Validate calculation engine
├── validate_calculations.py            # Validate calculations
├── validate_engine.py                  # Validate engine
├── validate_labour_usage.py            # Validate labour usage
├── validate_process_sheet.py           # Validate process sheet
├── validate_simple_tables.py           # Validate simple tables
└── visualize_costs.py                  # Visualize costs
```

## Tests Directory

```
tests/
├── test_*.py                   # Unit tests for various components
├── conftest.py                 # Pytest configuration
├── __init__.py                 # Package initialization
└── test_data.xlsx              # Test data
```

## Publication Directory

```
publication/
├── *.csv                       # Publication-ready CSV files
├── *_dictionary.csv            # Data dictionaries
├── *_metadata.json             # Metadata files
└── README.md                   # Publication package documentation
```

## Reports Directory

```
reports/
├── advanced_scenarios/         # Advanced scenario reports
├── advanced_visualizations/    # Advanced visualization reports
├── enhanced_visualizations/    # Enhanced visualization reports
├── performance/                # Performance reports
├── visualizations/             # Visualization reports
├── *.md                        # Markdown reports
├── *.html                      # HTML reports
└── *.json                      # JSON reports
```