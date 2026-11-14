# Copilot Instructions for Microcosting Genomics Repository

## Repository Overview

This repository implements a Python-based calculation engine that reverse-engineers complex Excel formulas from a microcosting model for genomic testing in rare diseases. The project is part of a University of Melbourne PhD economics research program. The main goal is to recreate Excel calculations in Python for transparency, maintainability, and validation.

**Key Facts:**
- **Language:** Python 3.15.1
- **Project Type:** Research analysis tool with Excel formula parsing
- **Size:** ~100 files, primary focus on `src/genomics_microcosting/` package
- **Main Components:** Calculation engine, formula parser, strategy pattern implementations
- **External Dependencies:** Workbook inputs, Polars and openpyxl

## Build and Development Setup

### Essential Installation Steps (ALWAYS Required)

```bash
uv sync --locked --python 3.15.1
.venv/bin/python --version
.venv/bin/pre-commit install
```

Use the locked environment for all development commands.

### Data Preparation (Required for validation scripts)

Use the workbook configured in `config.yaml` and keep generated outputs in a separate directory.

```bash
# Extract data from Excel workbooks and create parquet files
MICROCOSTING_OUTPUT_DIR=.private-runs/prepared .venv/bin/python prepare_data.py
```

This command:
- Reads the Excel workbook specified in `config.yaml`
- Writes generated tables to `.private-runs/prepared`
- Use the existing prepared inputs for workbook comparisons

### Testing

```bash
# Run all tests using the checkout's test inputs
.venv/bin/pytest

# Run with verbose output
.venv/bin/pytest -v

# Run specific test file
.venv/bin/pytest tests/test_calculation_engine.py
```

### Quality checks

```bash
.venv/bin/ruff check src
.venv/bin/ruff format --check src
.venv/bin/basedpyright
.venv/bin/bandit -r src
.venv/bin/pre-commit run --all-files
```

## Project Architecture

### Core Directory Structure

```
src/genomics_microcosting/     # Main Python package
├── calculation_engine.py    # Main calculation engine class
├── formula_parser.py        # Excel formula parsing logic  
├── strategies.py           # Strategy pattern implementations for formula types
├── sheet_manager.py        # Excel sheet data management
├── excel_utils.py          # Excel file utilities
└── config.py              # Configuration loading

tests/                      # Test suite (pytest)
data/                       # Excel files and extracted data
├── prepared/              # Generated parquet files (from prepare_data.py)
└── *.xlsm                 # Excel workbooks (not in repo)

config.yaml                 # Workbook and sheet configuration
scripts/                    # Analysis and validation scripts
```

### Key Architecture Components

1. **CalculationEngine** (`calculation_engine.py`): Core class that executes Excel formulas using a recursive tree-walking interpreter with memoization
2. **Formula Parser** (`formula_parser.py`): Parses Excel formula syntax into Python objects
3. **Strategy Pattern** (`strategies.py`): Separate classes for different formula types (SUM, VLOOKUP, IF, PMT, etc.)
4. **SheetManager** (`sheet_manager.py`): Handles loading and accessing Excel sheet data

### Configuration

`config.yaml` defines:
- Workbook locations and sheet names
- Multi-level header configurations  
- Data parsing parameters

Default workbook: Uses `validation` workbook from config.

## GitHub Workflows and CI

### CI Pipeline (`.github/workflows/ci.yml`)

The workflow runs on pushes and pull requests to main and on published releases.
It installs locked dependencies under Python 3.15.1 and runs the full suite with
coverage through pre-commit. Other jobs check Ruff, strict typing, Bandit,
workbook replay and distribution contents.

### Pre-commit Hooks (`.pre-commit-config.yaml`)

- **ruff**: Linting and formatting
- **pytest**: Run test suite on commit

Resolve pre-commit setup errors before committing.

## Common Development Tasks

### Making Code Changes

1. **Always** run `uv sync --locked --python 3.15.1` first
2. Make your changes
3. Run `.venv/bin/ruff check src` to check linting
4. Run `.venv/bin/pytest` to ensure tests pass
5. If working with validation: run `.venv/bin/python prepare_data.py` first

### Adding New Formula Support

1. Add parsing logic in `formula_parser.py`
2. Create new strategy class in `strategies.py`
3. Register strategy in `CalculationEngine.__init__`
4. Add tests in `tests/test_calculation_engine.py`

### Working with Excel Data

- Excel workbooks go in `data/` directory
- Modify `config.yaml` to reference new workbooks
- Run `.venv/bin/python prepare_data.py` after adding new data
- Use `SheetManager` class to access sheet data programmatically

### Validation and Analysis Scripts

```bash
# Validate engine against Excel outputs (may take several minutes)
.venv/bin/python validate_engine.py

# Analyze formula patterns
.venv/bin/python analyze_formula_patterns.py
```

**Note:** `validate_engine.py` can take 2+ minutes to complete as it processes all formulas. The `setup_calculation_engine.py` script has dependency issues - use validation scripts directly instead.

## File Dependencies and Relationships

### Critical Files for Code Changes
- `src/genomics_microcosting/calculation_engine.py` - Main engine logic
- `src/genomics_microcosting/strategies.py` - Formula implementations
- `tests/test_calculation_engine.py` - Core functionality tests
- `config.yaml` - Data source configuration

### Files You Can Usually Ignore
- `notebooks/` - Jupyter notebooks with analysis (contain syntax errors)
- `manuscripts/` - Research documentation
- `debug_*.txt`, `session.txt` - Debug output files
- Root-level analysis scripts (unless doing data analysis)

## Troubleshooting

### Common Build Issues

**Problem:** Tests fail with missing data  
**Solution:** Run `.venv/bin/python prepare_data.py` to generate required parquet files

**Problem:** Pre-commit hooks fail to install  
**Solution:** Run linting commands manually: `.venv/bin/ruff check src`

**Problem:** Import errors  
**Solution:** Ensure you ran `uv sync --locked --python 3.15.1` in editable mode

### Performance Notes

- Test suite: ~60 seconds
- `prepare_data.py`: ~10-30 seconds depending on data size
- Linting: ~5-10 seconds

## Trust These Instructions

These instructions are comprehensive and tested. Only search for additional information if:
- The specific commands documented here fail or produce unexpected results
- You need to work with parts of the codebase not covered in this overview
- The repository structure has changed significantly from what's described here

All documented commands have been validated to work correctly as of the last update.
