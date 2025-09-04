# Calculation Engine Documentation

The Calculation Engine is the core component of the microcosting analysis toolkit, responsible for parsing and executing Excel formulas programmatically.

## Overview

The calculation engine provides a Python-based implementation of Excel formula evaluation, enabling programmatic validation and testing of economic calculations. It uses a strategy pattern to handle different types of formulas and operations.

## Architecture

The calculation engine follows a modular architecture with the following key components:

### Core Classes

1. **CalculationEngine** - Main engine class that orchestrates formula parsing and execution
2. **FormulaParser** - Parses Excel formulas into structured representations
3. **Strategy Classes** - Implement specific formula operations (SUM, IF, VLOOKUP, etc.)
4. **SheetManager** - Manages loading and accessing data from Excel sheets and Parquet files

### Design Patterns

- **Strategy Pattern**: Different calculation approaches are implemented as strategies in `strategies.py`
- **Factory Pattern**: Appropriate calculation strategies are created based on formula types
- **Observer Pattern**: Used for tracking and reporting calculation differences
- **Parser Pattern**: Excel formulas are interpreted using a dedicated parser

## Key Features

### Formula Parsing
The engine can parse a subset of Excel formulas including:
- Numeric and string literals
- Cell references (with cross-sheet support)
- Common Excel functions (SUM, IF, VLOOKUP, PMT, etc.)
- Arithmetic operations (addition, multiplication, division)
- Nested formula structures

### Cross-Sheet References
Support for references between sheets using syntax like:
- `'Sheet Name'!A1` - Reference to cell A1 in "Sheet Name"
- Cross-sheet formulas are properly resolved and executed

### Memoization
The engine implements memoization to avoid redundant calculations and improve performance:
- Previously calculated results are cached
- Circular reference detection prevents infinite recursion

### Error Handling
Comprehensive error handling with:
- Detailed error reporting for formula parsing issues
- Graceful handling of missing data or invalid references
- Logging of calculation errors for debugging

## Usage

### Basic Usage

```python
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.sheet_manager import SheetManager

# Initialize components
sheet_manager = SheetManager()
engine = CalculationEngine(sheet_manager)

# Run calculations on a specific sheet
results_df, errors = engine.run_engine("Detailed Table")

# Process results
if errors:
    print(f"Encountered {len(errors)} errors during calculation")
else:
    print("Calculation completed successfully")
```

### Advanced Usage

```python
# Get a specific cell value
cell_value = engine.get_cell_value("Detailed Table", "A1")

# Get a cell formula
cell_formula = engine.get_cell_formula("Detailed Table", "B2")

# Execute a specific formula
result = engine.execute_formula("=A1+B1", "Detailed Table", "C1")
```

## Performance Considerations

### Optimization Techniques
1. **Memoization**: Cached results prevent redundant calculations
2. **Batch Processing**: Formulas are processed in batches for efficiency
3. **Lazy Loading**: Data is loaded only when needed
4. **Efficient Data Structures**: Pandas DataFrames for data manipulation

### Memory Management
- Results are stored in memory-efficient DataFrames
- Large datasets are processed in chunks when possible
- Unused data is garbage collected appropriately

## Extensibility

### Adding New Formula Types
To add support for new Excel functions:

1. Create a new strategy class in `strategies.py`
2. Implement the `execute` method for the new formula type
3. Register the strategy in the `CalculationEngine` strategy map
4. Add parsing logic to `formula_parser.py` if needed

### Custom Strategies
Custom calculation strategies can be implemented by extending the base strategy classes and registering them with the engine.

## Testing

The calculation engine includes comprehensive tests covering:
- Formula parsing accuracy
- Calculation correctness
- Cross-sheet reference handling
- Error condition handling
- Performance benchmarks

Run tests with:
```bash
python -m pytest tests/test_calculation_engine.py
```

## API Reference

### CalculationEngine Class

#### `__init__(sheet_manager, verbose=False)`
Initialize the calculation engine.

**Parameters:**
- `sheet_manager` (SheetManager): Sheet manager instance for data access
- `verbose` (bool): Enable verbose logging

#### `get_cell_value(sheet_name, cell_ref)`
Get the value of a cell from a sheet.

**Parameters:**
- `sheet_name` (str): Name of the sheet
- `cell_ref` (str): Cell reference (e.g., "A1")

**Returns:**
- Cell value or None if not found

#### `get_cell_formula(sheet_name, cell_ref)`
Get the formula of a cell from a sheet.

**Parameters:**
- `sheet_name` (str): Name of the sheet
- `cell_ref` (str): Cell reference (e.g., "A1")

**Returns:**
- Formula string or None if not found

#### `execute_formula(formula_or_parsed, sheet_name, cell_ref)`
Execute a formula and return the result.

**Parameters:**
- `formula_or_parsed` (str or dict): Formula string or parsed formula
- `sheet_name` (str): Name of the sheet containing the formula
- `cell_ref` (str): Cell reference (e.g., "A1")

**Returns:**
- Formula execution result

#### `run_engine(sheet_name=None, fail_on_error=True)`
Run the calculation engine on the specified sheet.

**Parameters:**
- `sheet_name` (str): Name of the sheet to process
- `fail_on_error` (bool): Whether to raise exceptions on errors

**Returns:**
- Tuple of (results DataFrame, errors list)

### FormulaParser Functions

#### `parse_formula(formula)`
Parse an Excel formula into a structured representation.

**Parameters:**
- `formula` (str): Formula string to parse

**Returns:**
- Dictionary representing the parsed formula