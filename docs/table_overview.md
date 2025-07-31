# Overview of Workbook Tables

The Excel file `Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm` contains several numbered worksheets.  The `1. Detailed Table` sheet is the core of the model: every costed step is listed here and formulas combine quantities and prices to generate the final unit costs.  All other sheets either supply the raw inputs referenced by these formulas or summarise the results for various sensitivity analyses.

The sections below describe how each supporting table feeds data back into the Detailed Table.  Understanding this flow of information is essential for replicating the calculations outside of Excel.

## 1. Detailed Table
Lists every process step alongside quantity and price information.  The `Unit Cost` columns are calculated here and serve as the primary outputs of the workbook.  Formulas in this sheet draw values from all of the supporting tables below so that each modelled activity has the correct quantities, prices and sensitivity adjustments.

## 2. Labor Prices
Contains hourly salary rates for each personnel category across all jurisdictions.  Cells in the Detailed Table use lookups to this sheet when filling the labour price columns.

## 3. Estimates
Stores baseline quantity and price assumptions for consumables, equipment and labour.  Each row in the Detailed Table references these defaults to populate its `Quantity` and `Price` input columns.

## 4. DSA - Equipment Throughput
Lists alternative equipment utilisation factors for deterministic sensitivity analysis (DSA).  For each DSA scenario the Detailed Table multiplies equipment costs by the throughput factor from this sheet.

## 5. DSA - Overheads
Specifies overhead percentages for each scenario.  The Detailed Table applies these percentages to total base costs when calculating overhead-inclusive unit costs.

## 6. DSA - Consumable Discounts
Provides discount rates for consumables in DSA scenarios.  The Detailed Table applies these rates to consumable prices in the DSA columns.

## 7. DSA - Labor Prices
Supplies alternative labour rates for sensitivity testing.  When a DSA scenario is active the Detailed Table looks up these rates instead of the standard Labour Prices table.

## 8. PSA
Summarises distribution parameters (e.g. means and percentiles) for probabilistic sensitivity analysis.  The values are derived from the Detailed Table outputs and do not feed back into the calculations.

