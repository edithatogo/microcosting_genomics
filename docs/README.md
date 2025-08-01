# unimelb-phd-phase-1 Documentation

This documentation provides an overview of the `unimelb-phd-phase-1` Python library, which is designed to reverse-engineer and replicate a complex Excel-based microcosting model.

## Modules

The library is organized into the following modules:

- **`calculation_engine.py`**: Contains the `CalculationEngine` class, which is responsible for parsing and executing Excel formulas.
- **`sheet_manager.py`**: Contains the `SheetManager` class, which handles loading and managing data from Excel sheets and Parquet files.
- **`formula_parser.py`**: Provides functions for parsing Excel formulas into a structured format.
- **`strategies.py`**: Implements the Strategy pattern for different types of Excel formulas (e.g., `SUM`, `IF`, `VLOOKUP`).
- **`config.py`**: Loads and manages the configuration from the `config.yaml` file.
- **`utils.py`**: Contains utility functions used throughout the library.

## Usage

To use the library, first create an instance of the `SheetManager` class, pointing it to the Excel workbook you want to analyze. Then, create an instance of the `CalculationEngine`, passing the `SheetManager` instance to it. You can then use the `run_engine` method of the `CalculationEngine` to execute the formulas on a specific sheet.

```python
from unimelb_phd_phase_1.sheet_manager import SheetManager
from unimelb_phd_phase_1.calculation_engine import CalculationEngine

# Create a SheetManager to handle data loading
sheet_manager = SheetManager("path/to/your/workbook.xlsx")

# Create a CalculationEngine with the SheetManager
engine = CalculationEngine(sheet_manager)

# Run the engine on a specific sheet
results_df, errors = engine.run_engine("Detailed Table")

# View the results
print(results_df)
```
