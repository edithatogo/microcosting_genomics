# Overview of Workbook Tables

The Excel file `Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm` contains several numbered worksheets.  The `1. Detailed Table` sheet is the core of the model: every costed step is listed here and formulas combine quantities and prices to generate the final unit costs.  All other sheets either supply the raw inputs referenced by these formulas or summarise the results for various sensitivity analyses.

## 1. Detailed Table
Lists every process step alongside quantity and price information.  The `Unit Cost` columns are calculated here and serve as the primary outputs of the workbook.  Formulas in this sheet draw values from all of the supporting tables below so that each modelled activity has the correct quantities, prices and sensitivity adjustments.

## 2. Labor Prices
Contains hourly salary rates for different personnel categories across jurisdictions.  The Detailed Table references these rates when filling labour price columns.
The table lists personnel categories and jurisdiction-specific hourly rates. Formulas in `1. Detailed Table` look up these rates to populate the labour price columns.

## 3. Estimates
Holds baseline quantity and price assumptions for each stage.  These values are looked up by the Detailed Table to populate its own quantity and price inputs.
These defaults supply the starting values for consumables and equipment. Cells in `1. Detailed Table` reference them to populate the `Quantity` and `Price` input columns.

## 4. DSA - Equipment Throughput
Provides alternative equipment utilisation factors for deterministic sensitivity analysis (DSA).  The DSA columns of the Detailed Table use these factors to adjust equipment costs.
For each DSA scenario the Detailed Table multiplies equipment costs by the corresponding throughput factor from this sheet.

## 5. DSA - Overheads
Lists overhead percentages used in DSA scenarios.  The Detailed Table multiplies base costs by these values when calculating overhead-inclusive unit costs.
The overhead percentage from this sheet is applied to total base costs to model institution-specific mark-ups.

## 6. DSA - Consumable Discounts
Supplies discount rates for consumables under DSA scenarios.  The Detailed Table references these discounts when computing DSA consumable costs.
These discount rates are applied to consumable prices in the DSA columns.

## 7. DSA - Labor Prices
Contains alternative labour cost assumptions for sensitivity testing.  These figures feed into the Detailed Table when calculating DSA labour costs.
The DSA labour columns look up these alternative rates in place of the standard table.

## 8. PSA
Summarises distribution parameters (e.g. means and percentiles) for probabilistic sensitivity analysis.  These statistics are derived from the Detailed Table outputs and used for further modelling.
This sheet summarises results from the Detailed Table for probabilistic modelling and does not feed back into the calculations.

