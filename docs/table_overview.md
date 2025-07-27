# Overview of Workbook Tables

The Excel file `Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx` contains several numbered worksheets.  The `1. Detailed Table` sheet is the core of the model: every costed step is listed here and formulas combine quantities and prices to generate the final unit costs.  The remaining sheets either provide inputs used by these formulas or summarise the outputs for sensitivity analyses.

## 1. Detailed Table
This sheet lists every process step alongside quantity and price information.  The "Unit Cost" columns are calculated here and serve as the primary outputs of the workbook.  Cells in this sheet pull data from the supplemental tables described below.

## 2. Labor Prices
Contains hourly salary rates for different personnel categories across jurisdictions.  The Detailed Table references these rates when filling labour price columns.

## 3. Estimates
Holds baseline quantity and price assumptions for each stage.  These values are looked up by the Detailed Table to populate its own quantity and price inputs.

## 4. DSA - Equipment Throughput
Provides alternative equipment utilisation factors for deterministic sensitivity analysis (DSA).  The DSA columns of the Detailed Table use these factors to adjust equipment costs.

## 5. DSA - Overheads
Lists overhead percentages used in DSA scenarios.  The Detailed Table multiplies base costs by these values when calculating overhead-inclusive unit costs.

## 6. DSA - Consumable Discounts
Supplies discount rates for consumables under DSA scenarios.  The Detailed Table references these discounts when computing DSA consumable costs.

## 7. DSA - Labor Prices
Contains alternative labour cost assumptions for sensitivity testing.  These figures feed into the Detailed Table when calculating DSA labour costs.

## 8. PSA
Summarises distribution parameters (e.g. means and percentiles) for probabilistic sensitivity analysis.  These statistics are derived from the Detailed Table outputs and used for further modelling.

