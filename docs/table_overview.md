# Overview of Workbook Tables

The Excel file `Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm` contains several numbered worksheets.  The `1. Detailed Table` sheet is the core of the model: every costed step is listed here and formulas combine quantities and prices to generate the final unit costs.  All other sheets either supply the raw inputs referenced by these formulas or summarise the results for various sensitivity analyses.

## 1. Detailed Table
Lists every process step alongside quantity and price information.  The `Unit Cost` columns are calculated here and serve as the primary outputs of the workbook.  Formulas in this sheet draw values from all of the supporting tables below so that each modelled activity has the correct quantities, prices and sensitivity adjustments.

## 2. Labor Prices
Contains hourly salary rates for each personnel category across jurisdictions.  The Detailed Table uses `VLOOKUP` formulas against this sheet to populate labour price columns for the base case calculations.

## 3. Estimates
Stores the baseline quantity and price assumptions for every stage of the workflow.  These inputs are pulled into the Detailed Table to fill the `Quantity of Use` and `Price` columns used in the core unit‑cost calculations.

## 4. DSA - Equipment Throughput
Provides alternative equipment utilisation factors for deterministic sensitivity analysis (DSA).  The DSA columns of the Detailed Table multiply the base equipment costs by these factors to reflect different utilisation scenarios.

## 5. DSA - Overheads
Lists overhead percentages used in DSA scenarios.  The Detailed Table applies these percentages to the baseline unit costs when computing overhead‑inclusive results.

## 6. DSA - Consumable Discounts
Supplies discount rates for consumables in each scenario.  The DSA formulas on the Detailed Table multiply baseline consumable prices by these discounts.

## 7. DSA - Labor Prices
Contains alternative labour cost assumptions used for sensitivity testing.  The DSA labour cost columns in the Detailed Table look up these rates instead of the base values from the `2. Labor Prices` sheet.

## 8. PSA
Summarises distribution parameters (for example means and percentiles) required for probabilistic sensitivity analysis.  These statistics are derived from the Detailed Table outputs and then fed into downstream modelling tools.

