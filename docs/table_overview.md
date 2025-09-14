# Comprehensive Overview of Workbook Tables

The Excel file `Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm` contains 35 worksheets that support a comprehensive microcosting analysis for rare disease genomics testing. The `Detailed Table` sheet serves as the core of the model, containing every costed step with formulas that combine quantities and prices to generate final unit costs.

This document provides a complete overview of all extracted tables, their purposes, relationships, and data formats.

## Core Calculation Tables

### 1. Detailed Table (`detailed_table.csv/.parquet`)

**Purpose**: The primary sheet containing all process steps and calculations

**Key Columns**:

- Test, Category, Sub-Category, Step (identifiers)
- Estimates Quantity of Use per Test LL (quantities)
- Price (AUD $/unit) LL (unit prices)
- Unit Cost (AUD $/unit) LL (calculated outputs)

**Relationships**: References all supporting tables for input data

**Rows**: 1,336 process steps across all test types

### 2. Process (`process.csv/.parquet`)

**Purpose**: Defines the workflow steps for different test types

**Key Content**: Process definitions for WES, WGS, and panel testing

**Relationships**: Referenced by Detailed Table for step definitions

## Labor and Personnel Data

### 3. DSA - Labour Prices (`dsa__labour_prices.csv/.parquet`)

**Purpose**: Hourly salary rates for personnel categories across jurisdictions

**Key Columns**: Labor Type, Hourly Rate (AUD), Annual Salary (AUD)

**Relationships**: Provides baseline labor costs for Detailed Table calculations

**Usage**: VLOOKUP formulas in Detailed Table match on labor type and jurisdiction

### 4. Labour - Usage - VCGS (`labour__usage__vcgs.csv/.parquet`)

**Purpose**: Labor utilization data for VCGS (Victorian Clinical Genetics Service)

**Key Columns**: Labor Type, Hours per Test, Hourly Rate (AUD)

**Relationships**: Supplies labor usage quantities to Detailed Table

### 5. Labour - Costs - VCGS (`labour__costs__vcgs.csv/.parquet`)

**Purpose**: Total labor costs for VCGS operations

**Key Columns**: Labor Type, Annual Salary (AUD), FTE, Total Cost (AUD)

**Relationships**: Provides cost summaries for labor components

## Equipment and Infrastructure

### 6. Eq - Usage - VCGS (`eq__usage__vcgs.csv/.parquet`)

**Purpose**: Equipment utilization data for VCGS

**Key Columns**: Equipment Name, Usage Hours per Month, Maintenance Cost (AUD)

**Relationships**: Supplies equipment usage data to Detailed Table

### 7. Eq - Costs and Usage - VCGS (`eq__costs_and_usage__vcgs.csv/.parquet`)

**Purpose**: Equipment cost and utilization combined data

**Key Columns**: Equipment Name, Purchase Cost (AUD), Useful Life (Years), Annualized Cost (AUD)

**Relationships**: Provides equipment cost calculations for Detailed Table

## Consumables and Materials

### 8. Cons - Costs and Util - VCGS (`cons___costs_and_util__vcgs.csv/.parquet`)

**Purpose**: Consumables costs and utilization for VCGS

**Key Columns**: Consumable Name, Usage per Test, Cost per Unit (AUD)

**Relationships**: Supplies consumables data to Detailed Table calculations

### 9. DSA - Consumable Discounts (`dsa___consumable_discounts.csv/.parquet`)

**Purpose**: Discount rates for consumables in sensitivity analysis scenarios

**Key Columns**: Consumable Type, Discount Rate (%), Scenario

**Relationships**: Applied to baseline consumable prices in Detailed Table

### 10. DSA - Cons Discounts (USD) (`dsa___cons_discounts_usd.csv/.parquet`)

**Purpose**: USD-based consumable discount rates

**Key Content**: Same as above but in USD currency

**Relationships**: Alternative currency version for international comparisons

## Budget Impact Analysis

### 11. BI - Comp Use - VCGS (`bi__comp_use__vcgs.csv/.parquet`)

**Purpose**: Compute resource usage for budget impact analysis

**Key Columns**: Compute Type, Usage Rate, Cost per Unit (AUD)

**Relationships**: Supplies compute cost data for budget impact calculations

### 12. BI - Stor Use - VCGS (`bi__stor_use__vcgs.csv/.parquet`)

**Purpose**: Storage resource usage for budget impact analysis

**Key Columns**: Storage Type, Usage Rate, Cost per Unit (AUD)

**Relationships**: Supplies storage cost data for budget impact calculations

### 13. BI - Comp+Stor Costs - VCGS (`bi__compstor_costs__vcgs.csv/.parquet`)

**Purpose**: Combined compute and storage costs

**Key Columns**: Resource Type, Compute Cost (AUD), Storage Cost (AUD), Total Cost (AUD)

**Relationships**: Provides integrated infrastructure costs

## Deterministic Sensitivity Analysis (DSA)

### 14. DSA - Test Throughput (`dsa__test_throughput.csv/.parquet`)

**Purpose**: Test volume assumptions for sensitivity analysis

**Key Columns**: Test Type, Monthly Volume, Annual Volume

**Relationships**: Affects cost calculations based on economies of scale

### 15. DSA - Overheads (`dsa___overheads.csv/.parquet`)

**Purpose**: Overhead percentages for different scenarios

**Key Columns**: Scenario, Overhead Percentage

**Relationships**: Applied to total costs in Detailed Table calculations

### 16. DSA - Overheads (USD) (`dsa___overheads_usd.csv/.parquet`)

**Purpose**: USD-based overhead rates

**Key Content**: Same as above but in USD currency

### 17. DSA - Summary (`dsa___summary.csv/.parquet`)

**Purpose**: Summary results of deterministic sensitivity analysis

**Key Content**: Aggregated results across all DSA scenarios

**Relationships**: Output table - summarizes Detailed Table results

### 18. DSA - Summary (2) (`dsa___summary_2.csv/.parquet`)

**Purpose**: Alternative summary format for DSA results

**Key Content**: Different aggregation of DSA scenario results

### 19. DSA - Summary - Stats (`dsa___summary___stats.csv/.parquet`)

**Purpose**: Statistical summary of DSA results

**Key Content**: Mean, standard deviation, min/max across scenarios

### 20. DSA - Differences (`dsa___differences.csv/.parquet`)

**Purpose**: Difference analysis between DSA scenarios

**Key Content**: Scenario comparison results

### 21. DSA - Tornado Charts Data

**Purpose**: Data for tornado diagram visualizations

- `dsa___tornado_index_0.csv/.parquet` - Base case tornado data
- `dsa___tornado_index_actual.csv/.parquet` - Actual case tornado data
- `dsa___tornado_actual.csv/.parquet` - Actual scenario tornado data

**Relationships**: Used for sensitivity analysis visualizations

## Summary and Reporting Tables

### 22. Summary Table (`summary_table.csv/.parquet`)

**Purpose**: High-level summary of all test costs

**Key Content**: Aggregated costs by test type and category

**Relationships**: Summarizes Detailed Table results

### 23. At a Glance (`at_a_glance.csv/.parquet`)

**Purpose**: Executive summary of key cost metrics

**Key Content**: Top-level cost summaries and KPIs

### 24. Summary Table Ordered (`summary_table_ordered.csv/.parquet`)

**Purpose**: Ordered version of summary table for reporting

**Key Content**: Summary data sorted by cost or other criteria

### 25. Summary Table 2 (`summary_table_2.csv/.parquet`)

**Purpose**: Alternative summary format

**Key Content**: Different aggregation of summary data

### 26. Summary 20230812 (`summary_20230812.csv/.parquet`)

**Purpose**: Dated summary snapshot

**Key Content**: Summary as of August 12, 2023

## Process-Specific Tables

### 27. Process - WES+Panel - VCGS (`process___wespanel___vcgs.csv/.parquet`)

**Purpose**: Detailed process steps for WES (Whole Exome Sequencing) + Panel testing

**Key Content**: Step-by-step process definition for combined testing

### 28. Process - WGS - VCGS (`process___wgs___vcgs.csv/.parquet`)

**Purpose**: Detailed process steps for WGS (Whole Genome Sequencing) testing

**Key Content**: Step-by-step process definition for WGS testing

## Category-Based Summaries

### 29. Summ Tab by Cat (`summ_tab_by_cat.csv/.parquet`)

**Purpose**: Summary table organized by test category

**Key Content**: Costs grouped by test category

### 30. Summ Tab by Stage (`summ_tab_by_stage.csv/.parquet`)

**Purpose**: Summary table organized by testing stage

**Key Content**: Costs grouped by process stage

### 31. Summ Table for Graph (`summ_table_for_graph.csv/.parquet`)

**Purpose**: Summary data formatted for graphing and visualization

**Key Content**: Data structured for chart generation

## Utility Tables

### 32. Sheet1 (`sheet1.csv/.parquet`)

**Purpose**: Utility worksheet for calculations or temporary data

**Key Content**: Working data or intermediate calculations

### 33. Sheet2 (`sheet2.csv/.parquet`)

**Purpose**: Additional utility worksheet

**Key Content**: Working data or intermediate calculations

## Data Dependencies and Flow

### Primary Data Flow

```text
Supporting Tables → Detailed Table → Summary Tables → Reporting
```

### Key Relationships

- **Detailed Table** is the central hub referencing all other tables
- **Labor tables** provide personnel cost data
- **Equipment tables** provide infrastructure cost data
- **Consumables tables** provide material cost data
- **DSA tables** provide scenario-specific adjustments
- **Summary tables** aggregate results for reporting

### Calculation Dependencies

1. **Baseline Values**: Labor, equipment, and consumables tables provide base costs
2. **Scenario Adjustments**: DSA tables modify baseline values for sensitivity analysis
3. **Process Definitions**: Process tables define workflow steps
4. **Cost Calculations**: Detailed Table combines all inputs to calculate final unit costs
5. **Reporting**: Summary tables aggregate results for different audiences

## Data Formats and Access

All tables are available in both formats:

- **CSV**: Human-readable format for external analysis and publication
- **Parquet**: Optimized binary format for programmatic access

### File Locations

- **CSV files**: `data/prepared/*.csv`
- **Parquet files**: `data/prepared/*.parquet`
- **Ground truth**: `data/prepared/ground_truth.parquet`

### Data Quality Notes

- All tables have been processed to handle multi-level headers
- Numeric columns are properly typed
- Missing values are handled consistently
- Column names follow snake_case convention for programmatic access

This comprehensive dataset enables complete replication of the Excel microcosting model in Python, supporting both validation and extension of the original analysis.
