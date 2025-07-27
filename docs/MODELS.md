# Microcosting Models

The `1. Detailed Table` sheet in the original Excel workbook actually contains five
independent models. The "Test" column identifies which model each row belongs to.

The models are:

1. **Panel**
2. **WES (P)** – Whole exome sequencing for population testing
3. **WES (T)** – Whole exome sequencing for targeted testing
4. **WGS (P)** – Whole genome sequencing for population testing
5. **WGS (T)** – Whole genome sequencing for targeted testing

All models share the same column layout. The key input and output columns are
listed below using the labels from the multi-level header.

## Input Columns

- `Quantity of Use per Test` – sub-columns `LL`, `Estimate`, `UL`, `Source`
- `Price (AUD $/unit)` – sub-columns `LL`, `Estimate`, `UL`, `Source`

## Output Columns

- `Unit Cost (AUD $/unit)` – sub-columns `LL`, `Estimate`, `UL`
- `DSA` (deterministic sensitivity analysis) columns for each region:
  - `SA` – `LL`, `Estimate`, `UL`
  - `NSW` – `LL`, `Estimate`, `UL`
  - `QLD` – `LL`, `Estimate`, `UL`
  - `WA` – `LL`, `Estimate`, `UL`

## Recurring Formula Patterns

The formulas used to populate the calculated columns repeat across all models:

- **Row multiplication** – `Unit Cost` cells usually multiply a quantity by its
  corresponding price on the same row.
- **Cross-sheet lookups** – Many inputs reference other sheets to pull labour
  usage, labour prices or baseline estimates.
- **Summation rows** – Totals within a category use simple `SUM(range)`
  formulas.
- **Multiplication by constants** – Some rows multiply by fixed numbers (e.g. 3
  for "trio" tests).

Recognising these patterns will help refactor the calculation engine into a set
of reusable operations.
