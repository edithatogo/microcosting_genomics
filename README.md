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

## Purpose
This project re-implements the microcosting calculations from the original Excel
workbook in Python.  A calculation engine parses the Excel formulas and
recreates the results so they can be tested and validated programmatically.

## Requirements
Python 3.8 or later is required. Runtime dependencies are declared in
`pyproject.toml` and include:

- `pandas`
- `openpyxl`

The test suite relies on `pytest`.

Install the dependencies with:

```bash
pip install -e .
pip install pytest
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
With `ground_truth.parquet` prepared you can compare the engine's output to the
expected values:

```bash
python validate_engine.py
```

The script runs the calculation engine on the detailed table, compares the
results to the ground truth and prints a summary of any differences.
