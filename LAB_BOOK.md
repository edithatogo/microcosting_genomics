# Lab Book: Microcosting Analysis

This document records the findings from the analysis of the microcosting Excel model.

## Phase 1: Data Extraction and Initial Analysis

### File Identification

- **Primary Data Source:** `data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx`
- **Primary Sheet:** `1. Detailed Table`

### Spreadsheet Structure

The `1. Detailed Table` sheet has a multi-level header.
- The first row appears to be the main category of the columns (e.g. `Test`, `Category`, `Quantity of Use per Test`, `Price (AUD $/unit)`).
- The second row is a sub-category (e.g. `LL`, `Estimate`, `UL`).

The first few columns identify the row's context:
- `Test`: The overall process being costed (e.g., `Panel`, `WES`).
- `Category`: The cost category (e.g., `Labour`, `Consumables`).
- `Sub-Category`: A more detailed cost category.
- `Step`: The specific action or item being costed.

The sheet contains columns for:
- `Quantity of Use per Test`: How much of something is used for a test.
- `Price (AUD $/unit)`: The cost of one unit.
- `Unit Cost (AUD $/unit)`: The calculated cost for the test.

Each of these has sub-columns for `LL` (Lower Limit), `Estimate`, and `UL` (Upper Limit).

### Column Categorization

- **Input Columns:**
    - `Quantity of Use per Test` (LL, Estimate, UL) - for some rows these will be inputs.
    - `Price (AUD $/unit)` (LL, Estimate, UL) - for some rows these will be inputs.
- **Calculation Columns:**
    - `Quantity of Use per Test` (LL, Estimate, UL) - for some rows these will be calculated.
    - `Price (AUD $/unit)` (LL, Estimate, UL) - for some rows these will be calculated.
    - `Unit Cost (AUD $/unit)` (LL, Estimate, UL) - these are likely always calculated.
- **Output Columns:**
    - `Unit Cost (AUD $/unit)` (LL, Estimate, UL) - these are the primary outputs of the microcosting model.

## Phase 2: Formula Parsing and Pattern Recognition

### Identified Formulas

- **Reference:** A formula that references a single cell.
  - e.g., `='3. Estimates'!F5`
  - e.g., `='[1]Labour - Usage - VCGS'!$AA49`
- **Multiplication:** A formula that multiplies two or more values.
  - e.g., `='1. Detailed Table'!E3*'1. Detailed Table'!I3`
  - e.g., `=E744*I744`
  - e.g., `=E744*I744*3`
- **Sum:** A formula that sums a range of cells or a list of cells.
  - e.g., `=SUM(M3:M6)`
  - e.g., `=SUM(M744,M748,M752)`
- **VLOOKUP:** A formula that performs a vertical lookup.
  - e.g., `=VLOOKUP(C12,'3. Estimates'!$A$4:$G$13,7,FALSE)`
- **IFERROR:** A formula that returns a specified value if a formula evaluates to an error.
  - e.g., `=IFERROR(VLOOKUP(C12,'3. Estimates'!$A$4:$G$13,7,FALSE),0)`
- **IF:** A formula that performs a conditional test.
  - e.g., `=IF(E770=0,0,E770*I770)`

### Calculation Patterns

- **Direct Multiplication:** The most common pattern is a simple multiplication of two cells on the same row, with or without sheet names.
- **Multiplication with a constant:** Some calculations involve multiplying by a hard-coded number (e.g., 3 for a "trio").
- **Cross-Sheet References:** Calculations often involve references to other sheets, such as `2. Labor Prices` and `3. Estimates`.
- **Summation:** Some cells are the sum of a range of cells above them, or a list of individual cells.
- **Conditional Logic:** `IF` and `IFERROR` are used to handle different scenarios and prevent errors.
- **Lookups:** `VLOOKUP` is used to find data in other tables.

### Semantic Meanings

(To be filled in)

## Phase 4: Abstraction and Code Refactoring

### Calculation Engine Development

- The `CalculationEngine` class has been implemented in `unimelb_phd_phase_1/calculation_engine.py`.
- It can load Excel workbooks and access cell values and formulas.
- The `_load_sheet` method correctly handles multi-level headers and loads data into pandas DataFrames.
- The `cell_to_coords` and `coords_to_cell` helper functions have been moved to `unimelb_phd_phase_1/utils.py` to resolve a circular dependency.
- The `execute_formula` method uses a Strategy design pattern to delegate calculations to different strategy classes based on the formula type.
- The following strategies have been implemented in `unimelb_phd_phase_1/strategies.py`:
    - `LiteralStrategy`
    - `ReferenceStrategy`
    - `MultiplicationStrategy`
    - `SumRangeStrategy`
    - `SumCellsStrategy`
    - `IfStrategy` (placeholder)
- All unit tests in `tests/test_calculation_engine.py` are passing, confirming the core functionality.

### Next Steps

- Implement the `IfStrategy`, `IfErrorStrategy`, and `VLookupStrategy`.
- Refactor the `CalculationEngine` to improve modularity and testability.
- Create a validation script to compare the Python-calculated results with the original Excel outputs.