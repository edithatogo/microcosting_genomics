# unimelb-phd-phase_1
University of Melbourne PhD (Economics of Rare Disease Genomics) - Phase 1 Microcosting Genomics

## Data Directory

All input files used by the helper scripts live in the `data/` directory at the
root of the repository. Each script resolves this path dynamically using a
snippet similar to:

```python
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
```

The processed and extracted files referenced in the notebooks and scripts should
be placed inside this directory.

The canonical source workbook is `Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm`.

## Purpose
This project re-implements the microcosting calculations from the original Excel
workbook in Python.  A calculation engine parses the Excel formulas and
recreates the results so they can be tested and validated programmatically.

## Requirements
Python 3.8 or later is required. Runtime dependencies are declared in
`pyproject.toml` and include:

- `pandas`
- `openpyxl`

The test suite and developer utilities rely on additional optional
dependencies.

Install all requirements with:

```bash
pip install -e .[dev]
```

If you have `just` installed you can instead run `just install`.

## Setup
1. Clone this repository.
2. Install the required packages as shown above.
3. Prepare the ground truth dataset used for validation:

```bash
python prepare_data.py
```

This command reads the `1. Detailed Table` sheet from the Excel workbook in the
`data/` directory and writes the cleaned data to
`data/prepared/ground_truth.parquet`.

## Running tests
Execute the test suite from the repository root with:

```bash
pytest
```

or use `just test` if `just` is available.

## Running the calculation engine
The engine can be initialised and inspected via the helper script:

```bash
python setup_calculation_engine.py
```

This loads the workbook and returns a `CalculationEngine` instance ready for
use.

## Validation
With the prepared parquet files you can verify the engine against every table:
Before tackling the full detailed table you can verify the simpler reference
tables. Run:

```bash
python validate_simple_tables.py
```

This script loads the "2. Labor Prices" and "3. Estimates" sheets, computes the
formulas with `CalculationEngine` and compares the results to the corresponding
parquet files.

With `ground_truth.parquet` prepared you can compare the engine's output to the
expected values:

```bash
python validate_engine.py
```

For each table the script reports how many cells were compared, how many
differences were detected and summary error statistics. Rows with differences
larger than `1e-4` are printed with their expected and calculated values so you
can quickly spot any mismatches.
