# Microcosting Genomics Analysis Toolkit

University of Melbourne PhD (Economics of Rare Disease Genomics) - Phase 1 Microcosting Genomics

## Overview

This project re-implements complex microcosting calculations from Excel workbooks into Python for rare disease genomics research. It enables programmatic validation, testing, and extension of economic models with enhanced transparency, reproducibility, and analytical capabilities.

The toolkit provides a complete framework for:
- Parsing and executing Excel formulas programmatically
- Validating calculations against ground truth datasets
- Performing deterministic and probabilistic sensitivity analyses
- Generating publication-ready reports in multiple formats
- Extending the model with plugins and custom analyses

## Repository Structure

```
microcosting_genomics/
├── src/unimelb_phd_phase_1/     # Core Python package
│   ├── calculation_engine.py    # Main calculation logic
│   ├── formula_parser.py        # Excel formula parsing
│   ├── strategies.py            # Calculation strategies
│   ├── sheet_manager.py         # Data loading and management
│   ├── data_manager.py          # Unified data handling
│   ├── excel_version_control.py # Workbook version control
│   ├── advanced_scenario_modeling.py # DSA/PSA analyses
│   ├── advanced_visualization.py # Enhanced visualization tools
│   ├── enhanced_plugin_system.py # Plugin architecture
│   └── web.py                   # Web interface
├── scripts/                     # Helper scripts and utilities
├── data/                        # Input data and prepared files
│   └── prepared/                # Processed Parquet files
├── publication/                 # Publication-ready outputs
├── reports/                     # Generated reports and analyses
├── notebooks/                   # Jupyter notebooks for analysis
├── docs/                        # Documentation
├── tests/                       # Test suite
└── manuscripts/                 # Research manuscripts
```

## Installation

The Python sources live under the `src/` directory. Install the package **with the developer extras** in editable mode so changes are reflected and the test dependencies are available:

```bash
pip install -e .[dev]
```

This command installs tools such as `pytest`, `black` and `pre-commit`. **Run it before executing any tests.**

## Quick Start

1. Clone this repository
2. Install dependencies: `pip install -e .[dev]`
3. Place the Excel workbook in the `data/` directory
4. Prepare data files: `python prepare_data.py`
5. Run validation: `python scripts/validate_engine.py`

## Data Preparation

All input files used by the helper scripts live in the `data/` directory. The Excel workbook referenced in `config.yaml` is required by most helper scripts.

After copying the workbook to the `data/` directory, run:

```bash
python prepare_data.py
```

This extracts all required sheets and creates Parquet files under `data/prepared/`. These files are essential for running tests and validation scripts.

## Core Components

### Calculation Engine
The calculation engine parses Excel formulas and recreates results programmatically. It supports:
- Formula parsing for common Excel functions (SUM, IF, VLOOKUP, etc.)
- Cross-sheet references
- Memoization for performance optimization
- Error handling and logging

### Data Management
Unified data handling for all sheets with:
- Consistent loading and saving in Parquet and CSV formats
- Automatic metadata generation
- Publication-ready outputs
- Duplicate column name resolution

### Scenario Analysis
Comprehensive sensitivity analysis capabilities:
- Deterministic Sensitivity Analysis (DSA)
- Probabilistic Sensitivity Analysis (PSA)
- Custom scenario modeling
- Monte Carlo simulation

### Visualization
Enhanced visualization tools:
- Interactive Plotly charts
- Dashboard capabilities
- Export to multiple formats
- Web-based interface

### Plugin System
Extensible architecture for adding functionality:
- Plugin loading and management
- Metadata and configuration support
- Dependency management
- Tag-based filtering

## Workbook Dependencies

The Excel workbook contains several worksheets that work together to calculate final unit costs:

### Core Model
1. **Detailed Table** - Primary sheet containing all process steps and calculations
2. **Labor Prices** - Hourly salary rates for personnel categories
3. **Estimates** - Default quantities and prices for consumables, equipment, and labor

### Sensitivity Analysis
4. **DSA - Equipment Throughput** - Equipment utilization factors
5. **DSA - Overheads** - Overhead percentages
6. **DSA - Consumable Discounts** - Discount rates for consumables
7. **DSA - Labor Prices** - Alternative labor rates
8. **PSA** - Probabilistic analysis parameters

## Configuration

Workbook locations and sheet names are defined in `config.yaml` at the repository root. A minimal configuration looks like:

```yaml
default_workbook: main
workbooks:
  main:
    path: "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    sheets:
      "Detailed Table":
        header_rows: 4
        data_starts_at: 5
        string_columns: ["Test", "Category", "Sub-Category", "Step"]
      "2. Labor Prices":
        header_rows: 1
        data_starts_at: 2
      "3. Estimates":
        header_rows: 1
        data_starts_at: 2
```

## Testing

Before running the tests make sure the developer extras are installed **and** the Parquet files generated by `prepare_data.py` are available:

```bash
pip install -e .[dev]
python prepare_data.py
pytest
```

## Generating Reports

The project includes enhanced reporting capabilities that can generate reports in multiple formats:

1. **Markdown reports** - Basic text-based reports
2. **HTML reports** - Interactive web-based reports with enhanced formatting
3. **PDF reports** - Printable documents (requires weasyprint)
4. **JSON reports** - Machine-readable data summaries

To generate all report formats, run:

```bash
python scripts/enhanced_reporting.py
```

## Web Interface

The project includes a web interface for exploring data and visualizations:

```bash
python scripts/run_web.py
```

Access the application at: http://127.0.0.1:5000

## Pre-commit Hooks

Install the Git hooks so that formatting and linting run automatically on each commit:

```bash
pre-commit install
```

You can run all hooks manually with:

```bash
pre-commit run --all-files
```

## Requirements

Python 3.8 or later is required. Runtime dependencies are declared in `pyproject.toml` and include:

- `pandas` - Data manipulation
- `openpyxl` - Excel file handling
- `numpy-financial` - Financial calculations
- `PyYAML` - Configuration parsing
- `matplotlib` - Basic visualization
- `plotly` - Interactive visualization
- `flask` - Web interface

The test suite and developer utilities rely on additional optional dependencies, installed via the `dev` extras:

- `bandit` - Security checks
- `black` - Code formatting
- `isort` - Import sorting
- `pre-commit` - Git hooks
- `pytest` - Testing framework
- `ruff` - Code linting

Install all requirements with:

```bash
pip install -e .[dev]
```

## Documentation

Additional documentation can be found in the `docs/` directory:

- [Repository Structure](docs/REPOSITORY_STRUCTURE.md) - Detailed repository organization
- [Development Guide](docs/DEVELOPMENT_GUIDE.md) - Guide for developers
- [API Reference](docs/API_REFERENCE.md) - Detailed API documentation
- [Calculation Engine](docs/CALCULATION_ENGINE.md) - Core calculation logic and formula parsing
- [Data Management](docs/DATA_MANAGEMENT.md) - Unified data handling and preparation
- [Data Manager](docs/DATA_MANAGER.md) - Data manager implementation details
- [Configuration](docs/CONFIG.md) - Configuration management
- [Scenario Analysis](docs/SCENARIO_ANALYSIS.md) - Deterministic and probabilistic sensitivity analysis
- [Plugin System](docs/PLUGIN_SYSTEM.md) - Extensible plugin architecture
- [Models](docs/MODELS.md) - Overview of microcosting models
- [Table Overview](docs/table_overview.md) - Detailed table descriptions
- [Web Interface](docs/WEB_INTERFACE.md) - Web interface documentation
- [docs/README.md](docs/README.md) - Module documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.