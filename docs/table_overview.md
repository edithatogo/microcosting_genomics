# Overview of Workbook Tables

The Excel file `Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm` contains several numbered worksheets.  The `1. Detailed Table` sheet is the core of the model: every costed step is listed here and formulas combine quantities and prices to generate the final unit costs.  All other sheets either supply the raw inputs referenced by these formulas or summarise the results for various sensitivity analyses.

The sections below describe how each supporting table feeds data back into the Detailed Table.  Understanding this flow of information is essential for replicating the calculations outside of Excel.

## 1. Detailed Table
Lists every process step alongside quantity and price information.  The `Unit Cost` columns are calculated here and serve as the primary outputs of the workbook.  Formulas in this sheet draw values from all of the supporting tables below so that each modelled activity has the correct quantities, prices and sensitivity adjustments.

## 2. Labor Prices
Contains hourly salary rates for each personnel category across all jurisdictions.  
The Detailed Table combines the staff role and jurisdiction columns to look up the
correct hourly rate from this sheet.  These values populate the labour price
fields before any scenario-specific adjustments are applied.

## 3. Estimates
Stores the default quantities and prices for consumables, equipment and labour.
Rows in the Detailed Table link back to this sheet using an identifier so that
each activity starts with a consistent baseline `Quantity` and `Price` before
other factors are incorporated.

## 4. DSA - Equipment Throughput
Lists alternative equipment utilisation factors for deterministic sensitivity
analysis (DSA).  For every scenario the Detailed Table multiplies equipment
costs by the throughput factor from this sheet to explore how utilisation levels
affect per-test costs.

## 5. DSA - Overheads
Specifies overhead percentages for each DSA scenario.  After totalling labour
and consumable costs the Detailed Table multiplies by these values to report
overhead-inclusive unit costs.

## 6. DSA - Consumable Discounts
Provides discount rates for consumables in DSA scenarios.  Consumable rows in
the Detailed Table multiply their baseline price by `(1 - discount)` from this
sheet when populating the scenario columns.

## 7. DSA - Labor Prices
Supplies alternative labour rates used during sensitivity testing.  When a DSA
scenario is active the Detailed Table references this sheet rather than `2. Labor
Prices` so that scenario-specific labour costs are used in the calculations.

## 8. PSA
Summarises distribution parameters (e.g. means and percentiles) for probabilistic sensitivity analysis.  The values are derived from the Detailed Table outputs and do not feed back into the calculations.

