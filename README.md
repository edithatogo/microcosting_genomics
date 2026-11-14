# Microcosting Genomics Analysis Toolkit

[![Hosted main CI](https://github.com/edithatogo/microcosting_genomics/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/edithatogo/microcosting_genomics/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/edithatogo/microcosting_genomics/branch/main/graph/badge.svg)](https://codecov.io/gh/edithatogo/microcosting_genomics)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Python 3.15.1](https://img.shields.io/badge/python-3.15.1-blue)](pyproject.toml)


University of Melbourne PhD (Economics of Rare Disease Genomics) - Phase 1 Microcosting Genomics

## Qualification status

The Polars implementation includes a replay against the original workbook. The replay covers the selected detailed-table unit costs. See the [workbook catalogue](docs/table_overview.md) for the worksheet inventory and the scope of the evidence.

Keep original workbooks, datasets, generated research outputs, AI artefacts and private receipts local. Review the complete outgoing history before pushing source changes.

The T1 scenario builder accepts historical manifests through `--manifest-dir`. The repository's test fixtures use synthetic timing inputs to exercise the same formula selection and source checks.

## Overview

This project re-implements complex microcosting calculations from Excel workbooks into Python for rare disease genomics research. It enables programmatic validation, testing, and extension of economic models with enhanced transparency, reproducibility, and analytical capabilities.

The toolkit includes these components:
- Parsing and executing Excel formulas programmatically
- Validating calculations against ground truth datasets
- Performing deterministic and probabilistic sensitivity analyses
- Generating publication-ready reports in multiple formats
- Extending the model with plugins and custom analyses

## Repository Structure

```
microcosting_genomics/
├── src/genomics_microcosting/     # Core Python package
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

The Python sources live under the `src/` directory. Sync the locked development group for an editable installation and test tools:

```bash
uv sync --locked --python 3.15.1 --group dev
```

This installs the locked runtime and development tools without changing the lock. Verify `.venv/bin/python --version` reports 3.15.1 before tests. Preserve active environments until their running operations finish.

## Quick Start

1. Clone this repository
2. Install dependencies: `uv sync --locked --python 3.15.1 --group dev`
3. Place the Excel workbook in the `data/` directory
4. Prepare data files: `.venv/bin/prepare-data`
5. Run validation: `.venv/bin/validate-engine`

## Data Preparation

All input files used by the helper scripts live in the `data/` directory. The Excel workbook referenced in `config.yaml` is required by most helper scripts.

After copying the workbook to the `data/` directory, run:

```bash
.venv/bin/prepare-data
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

The installed package includes the same default configuration. A checkout or
working-directory configuration takes precedence, and an explicit path can be
passed to `load_config`. The referenced study workbooks are separate inputs and
are not included in the distribution.

When installed, `DataManager` uses `data/` and `publication/` under the current
working directory by default. Pass `data_dir` explicitly to select another input
and prepared-data location. An editable checkout retains its project-root defaults.

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

Use existing qualified prepared inputs for workbook tests. Preserve immutable ground truth;
do not regenerate it to obtain a passing comparison. During edits, select affected tests:

```bash
uv sync --locked --python 3.15.1 --group dev
.venv/bin/python tools/select_tests.py tests/test_cost_properties.py
```

At a coherent integration milestone, run the full coverage gate:

```bash
.venv/bin/python -m pytest --disable-socket --allow-unix-socket --timeout=120 --cov=src --cov-fail-under=30
```

## Generating Reports

The project includes enhanced reporting capabilities that can generate reports in multiple formats:

1. **Markdown reports** - Basic text-based reports
2. **HTML reports** - Interactive web-based reports with enhanced formatting
3. **PDF reports** - Printable documents (requires weasyprint)
4. **JSON reports** - Machine-readable data summaries

To generate all report formats, run:

```bash
.venv/bin/python scripts/enhanced_reporting.py
```

## Web Interface

The project includes a web interface for exploring data and visualizations:

```bash
.venv/bin/python scripts/run_web.py
```

Access the application at: http://127.0.0.1:5000

## Pre-commit Hooks

Install the Git hooks so that formatting and linting run automatically on each commit:

```bash
.venv/bin/pre-commit install
```

You can run all hooks manually with:

```bash
.venv/bin/pre-commit run --all-files
```

## Requirements

Python 3.15.1 is required. Verify the selected repository-local interpreter with `.venv/bin/python --version`. Runtime dependencies are declared in `pyproject.toml` and include:

- `polars` and `pyarrow` - Native dataframes and typed Parquet interchange
- `openpyxl` and `defusedxml` - Excel input with XML entity rejection
- `numpy` and `scipy` - Numeric calculations and legacy statistical consumers
- `numpy-financial` - Financial calculations
- `pydantic` and `pandera[polars]` - Configuration and native table contracts
- `PyYAML` - Configuration parsing
- `flask` - Web interface

Matplotlib/Plotly belong to the `visualization` extra; WeasyPrint/Jinja2/ReportLab belong to
`reporting`, and cryptography belongs to `security`. Development dependencies are
consolidated in the uv `dev` group:

- `bandit` - Security checks
- `basedpyright` - Strict typing
- `pre-commit` - Git hooks
- `pytest` - Testing framework
- `ruff` - Linting, import sorting and formatting
- `hypothesis` - Generated property cases
- `pytest-gremlins` - Explicitly targeted mutation testing
- `pytest-cov`, `pytest-timeout`, `pytest-socket`, `pytest-env` - Coverage, bounded execution, network isolation and test environment
- `vulture` - Review of high-confidence unused-code findings

Install all requirements with:

```bash
uv sync --locked --python 3.15.1 --group dev
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

This project is licensed under the Apache License, Version 2.0 - see the [LICENSE](LICENSE) file for details.

## Development checks and local hooks

After syncing the locked development group, install the repository hooks:

```sh
.venv/bin/pre-commit install
.venv/bin/python tools/select_tests.py tests/test_cost_properties.py
```

The test hook selects changed test files and reverse import consumers for source changes. Shared fixtures, lock/manifest changes, unknown source impact and package initialization require the full suite. Import selection does not prove dynamic plugin coverage: use explicit integration selectors and full milestones when dynamic behavior changes. Normal pytest caching remains enabled; failure-only reruns use `--lf --last-failed-no-failures=none`. An empty failure cache is not verification. No retries are configured. CI retains full integration, coverage and security gates.

CI runs the hook checks followed by one complete coverage run, avoiding a second
pytest execution inside pre-commit. Library diagnostics use module logging;
application entry points configure console output. The package gate builds the
wheel from its sdist and checks source bytes, complete licence, version metadata,
typing marker and the distribution path allowlist using `tools/check_package.py`.

Run Vulture for review with `.venv/bin/vulture src --min-confidence 100`; findings are not permission to remove public arguments or plugin entry points. Property and mutation evidence must identify actual targets and results. Do not confuse installed plugins, line coverage or badges with scientific acceptance.

## Citation and licensing

Use [CITATION.cff](CITATION.cff) to cite the software. It does not supply or replace a study publication citation. Project-owned code uses the complete [Apache-2.0 licence](LICENSE). Preserve upstream notices and licences for dependencies; the code licence does not grant redistribution rights over workbooks, datasets, research manuscripts or private evidence. Hosted badges report the linked service's state and do not certify this unpublished branch.

Package versions are derived from Git metadata by Hatchling/hatch-vcs at build time;
`genomics_microcosting.__version__` reads installed distribution metadata. Editable
installs refresh that metadata when synchronized. Builds without SCM or archive
version metadata use the documented `0.2.0` fallback; no release tag is created by
setup. Distribution version identity is not scientific or hosted acceptance.

Development dependencies have one authoritative uv `dev` group. Optional
`visualization` and `reporting` extras describe separate consumers; the former
pip `[dev]` extra has been retired. SciPy remains required while the root-level
legacy analysis runner still imports it; pandas has been removed from the runtime/development environment and test modules.
Legacy scripts still require migration and must not be treated as qualified native entry points.

For credential-verification and encrypted-configuration contracts, including
explicit legacy migration boundaries, see [SECURITY.md](SECURITY.md). Install the
`security` extra for deployed configuration encryption; the development group
includes its backend for tests. The security module demonstration uses temporary
files and synthetic data, never an existing configuration destination.
