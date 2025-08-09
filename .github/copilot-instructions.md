# Copilot Instructions for Microcosting Genomics Repository

## Repository Overview

This repository implements a Python-based calculation engine that reverse-engineers complex Excel formulas from a microcosting model for genomic testing in rare diseases. The project is part of a University of Melbourne PhD economics research program. The main goal is to recreate Excel calculations in Python for transparency, maintainability, and validation.

**Key Facts:**
- **Language:** Python 3.8+ (tested on 3.11+)
- **Project Type:** Research analysis tool with Excel formula parsing
- **Size:** ~100 files, primary focus on `src/unimelb_phd_phase_1/` package
- **Main Components:** Calculation engine, formula parser, strategy pattern implementations
- **External Dependencies:** Excel workbook files (not in repo), pandas, openpyxl

## Build and Development Setup

### Essential Installation Steps (ALWAYS Required)

```bash
# 1. Install the package in editable mode with dev dependencies
pip install -e .[dev]

# 2. Set up pre-commit hooks (optional but recommended)
pre-commit install
```

**Critical:** Always run `pip install -e .[dev]` before any development work. This installs both runtime dependencies (pandas, openpyxl, numpy-financial, PyYAML, scipy) and development tools (pytest, ruff, black, isort, pre-commit, bandit).

### Data Preparation (Required for validation scripts)

The project works with Excel workbooks that are NOT included in the repository. For full functionality:

```bash
# Extract data from Excel workbooks and create parquet files
python prepare_data.py
```

This command:
- Reads Excel workbooks specified in `config.yaml` 
- Creates parquet files in `data/prepared/`: `detailed_table.parquet`, `dsa__labour_prices.parquet`, `dsa__test_throughput.parquet`
- **Must be run** before validation scripts or tests that depend on real data

### Testing

```bash
# Run all tests (works without Excel data)
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_calculation_engine.py
```

**Test Status:** 93 tests pass, 1 skipped. Tests run in ~60 seconds and work without Excel workbook data.

### Linting and Code Quality

```bash
# Run ruff linting (exclude problematic notebooks)
ruff check . --exclude="notebooks/*"

# Format code (also exclude notebooks)
ruff format . --exclude="notebooks/*"
black .
isort .

# Run security checks
bandit -c pyproject.toml -r .

# Run all pre-commit hooks manually
pre-commit run --all-files
```

**Known Issue:** Jupyter notebooks contain syntax errors. Always exclude `notebooks/*` when running ruff commands.

### Alternative Build Tool

The project includes a `justfile` for task automation, but `just` is not commonly installed. Use the manual commands above instead.

## Project Architecture

### Core Directory Structure

```
src/unimelb_phd_phase_1/     # Main Python package
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

**Triggers:** Push to main, pull requests to main  
**Python Version:** 3.11  
**Steps:**
1. Install dependencies with `pip install -e .[dev]`
2. Run pre-commit hooks with `pre-commit run --all-files --color=always`
3. Run tests with `pytest -q`

**Timing:** Full CI run takes ~2-3 minutes

### Pre-commit Hooks (`.pre-commit-config.yaml`)

- **ruff**: Linting and formatting
- **pytest**: Run test suite on commit

**Important:** Pre-commit setup may fail due to network timeouts. If this happens, run linting commands manually.

## Common Development Tasks

### Making Code Changes

1. **Always** run `pip install -e .[dev]` first
2. Make your changes
3. Run `ruff check . --exclude="notebooks/*"` to check linting
4. Run `pytest` to ensure tests pass
5. If working with validation: run `python prepare_data.py` first

### Adding New Formula Support

1. Add parsing logic in `formula_parser.py`
2. Create new strategy class in `strategies.py`
3. Register strategy in `CalculationEngine.__init__`
4. Add tests in `tests/test_calculation_engine.py`

### Working with Excel Data

- Excel workbooks go in `data/` directory
- Modify `config.yaml` to reference new workbooks
- Run `python prepare_data.py` after adding new data
- Use `SheetManager` class to access sheet data programmatically

### Validation and Analysis Scripts

```bash
# Validate engine against Excel outputs (may take several minutes)
python validate_engine.py

# Analyze formula patterns
python analyze_formula_patterns.py
```

**Note:** `validate_engine.py` can take 2+ minutes to complete as it processes all formulas. The `setup_calculation_engine.py` script has dependency issues - use validation scripts directly instead.

## File Dependencies and Relationships

### Critical Files for Code Changes
- `src/unimelb_phd_phase_1/calculation_engine.py` - Main engine logic
- `src/unimelb_phd_phase_1/strategies.py` - Formula implementations
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
**Solution:** Run `python prepare_data.py` to generate required parquet files

**Problem:** Pre-commit hooks fail to install  
**Solution:** Run linting commands manually: `ruff check . --exclude="notebooks/*"`

**Problem:** Import errors  
**Solution:** Ensure you ran `pip install -e .[dev]` in editable mode

**Problem:** pandas FutureWarnings  
**Solution:** These are expected warnings from `prepare_data.py`, not errors

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