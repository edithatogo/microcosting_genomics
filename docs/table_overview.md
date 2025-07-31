# Overview of Workbook Tables

The Excel file `Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm` contains several numbered worksheets.  The `1. Detailed Table` sheet is the core of the model: every costed step is listed here and formulas combine quantities and prices to generate the final unit costs.  All other sheets either supply the raw inputs referenced by these formulas or summarise the results for various sensitivity analyses.

The sections below describe how each supporting table feeds data back into the
Detailed Table. Understanding this flow of information is essential for
replicating the calculations outside of Excel.

## 1. Detailed Table
Lists every process step alongside quantity and price information.  The
`Unit Cost` columns are calculated here and serve as the primary outputs of the
workbook.  Formulas in this sheet draw values from all of the supporting tables
below so that each modelled activity has the correct quantities, prices and
sensitivity adjustments.  Lookups and references in this table pull baseline
values from the tables described in the following sections and then apply the
appropriate scenario modifiers.

## 2. Labor Prices
Contains hourly salary rates for each personnel category across all
jurisdictions.  The Detailed Table matches on both staff role and jurisdiction
to retrieve the base hourly cost using lookup formulas.  That rate fills the
`Price (AUD $/unit)` column for labour rows before any
scenario-specific adjustments are applied.

## 3. Estimates
Stores the default quantities and prices for consumables, equipment and
labour.  Each row in the Detailed Table includes an identifier that points back
to this sheet.  Lookup formulas pull the baseline `Quantity` and `Price`
for that item, ensuring every activity starts from a consistent set of inputs
before other scenario factors are incorporated.

## 4. DSA - Equipment Throughput
Lists alternative equipment utilisation factors for deterministic sensitivity
analysis (DSA).  Equipment rows in the Detailed Table reference the throughput
factor for the active scenario and multiply their baseline cost by this value.
This allows the model to explore how different utilisation levels affect
per-test costs.

## 5. DSA - Overheads
Specifies overhead percentages for each DSA scenario.  Once labour and
consumable costs are summed for a row, the Detailed Table multiplies that total
by the overhead percentage looked up from this sheet.  The result is the
overhead-inclusive unit cost reported for each scenario.

## 6. DSA - Consumable Discounts
Provides discount rates for consumables in DSA scenarios.  Consumable rows in
the Detailed Table look up the appropriate discount for the active scenario and
multiply their baseline price by `(1 - discount)` before quantity is applied.

## 7. DSA - Labor Prices
Supplies alternative labour rates used during sensitivity testing.  When a DSA
scenario is active the Detailed Table looks up the hourly rate from this sheet
instead of `2. Labor Prices` so that scenario-specific wage assumptions are
applied to all labour cost calculations.

## 8. PSA
Summarises distribution parameters (e.g. means and percentiles) for
probabilistic sensitivity analysis.  The figures in this sheet are calculated
from the Detailed Table outputs and therefore do not feed back into the
calculations.

