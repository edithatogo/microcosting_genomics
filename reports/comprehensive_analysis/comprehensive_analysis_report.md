# Comprehensive Microcosting Analysis Report
Generated on: 2025-09-04 06:38:35

## Executive Summary
This comprehensive report integrates cost driver analysis, deterministic sensitivity analysis (DSA), probabilistic sensitivity analysis (PSA), value of information (VOI) analysis, budget impact analysis, and break-even analysis to provide a complete picture of the genomics microcosting model.

## Analysis Components
1. **Cost Driver Analysis**: Identifies key cost contributors by value and proportion
2. **Deterministic Sensitivity Analysis (DSA)**: Examines impact of parameter variation
3. **Probabilistic Sensitivity Analysis (PSA)**: Quantifies uncertainty using Monte Carlo simulation
4. **Value of Information (VOI) Analysis**: Assesses economic value of reducing uncertainty
5. **Budget Impact Analysis**: Evaluates cost implications of different testing volumes and scenarios
6. **Break-even Analysis**: Determines volume thresholds for cost recovery and minimum efficient scale

## Cost Driver Analysis
## Absolute Cost Drivers

Ranked by absolute value contribution:

| Category    | Sub-Category   |   Absolute_Value |   Percentage |
|:------------|:---------------|-----------------:|-------------:|
| Labour      | Sequencing     |             1200 |        37.5  |
| Equipment   | Library Prep   |              800 |        25    |
| Consumables | DNA Extraction |              600 |        18.75 |
| Compute     | Processing     |              400 |        12.5  |
| Storage     | Archival       |              200 |         6.25 |


## Proportional Cost Drivers

Ranked by percentage contribution:

| Category    | Sub-Category   |   Percentage |   Absolute_Value |
|:------------|:---------------|-------------:|-----------------:|
| Labour      | Sequencing     |        37.5  |             1200 |
| Equipment   | Library Prep   |        25    |              800 |
| Consumables | DNA Extraction |        18.75 |              600 |
| Compute     | Processing     |        12.5  |              400 |
| Storage     | Archival       |         6.25 |              200 |


## Cost Drivers by Model

### Panel

| Category    | Sub-Category   |   Absolute_Value |   Percentage |
|:------------|:---------------|-----------------:|-------------:|
| Labour      | Sequencing     |              400 |         44.4 |
| Equipment   | Library Prep   |              300 |         33.3 |
| Consumables | DNA Extraction |              200 |         22.3 |


### WES (P)

| Category    | Sub-Category   |   Absolute_Value |   Percentage |
|:------------|:---------------|-----------------:|-------------:|
| Labour      | Sequencing     |              400 |         44.4 |
| Equipment   | Library Prep   |              300 |         33.3 |
| Consumables | DNA Extraction |              200 |         22.3 |


### WES (T)

| Category    | Sub-Category   |   Absolute_Value |   Percentage |
|:------------|:---------------|-----------------:|-------------:|
| Labour      | Sequencing     |              400 |         44.4 |
| Equipment   | Library Prep   |              300 |         33.3 |
| Consumables | DNA Extraction |              200 |         22.3 |


### WGS

| Category    | Sub-Category   |   Absolute_Value |   Percentage |
|:------------|:---------------|-----------------:|-------------:|
| Labour      | Sequencing     |              400 |         44.4 |
| Equipment   | Library Prep   |              300 |         33.3 |
| Consumables | DNA Extraction |              200 |         22.3 |


### Equipment Utilization

| Category    | Sub-Category   |   Absolute_Value |   Percentage |
|:------------|:---------------|-----------------:|-------------:|
| Labour      | Sequencing     |              400 |         44.4 |
| Equipment   | Library Prep   |              300 |         33.3 |
| Consumables | DNA Extraction |              200 |         22.3 |



## Deterministic Sensitivity Analysis (DSA)
## Sensitivity Analysis Results

One-way sensitivity analysis results:

| parameter            |   baseline |   low_value |   high_value |   low_change_pct |   high_change_pct |   low_impact |   high_impact |   max_impact |
|:---------------------|-----------:|------------:|-------------:|-----------------:|------------------:|-------------:|--------------:|-------------:|
| dsa__labour_prices   |        100 |          80 |          120 |              -20 |                20 |           20 |            20 |           20 |
| dsa__test_throughput |        100 |          80 |          120 |              -20 |                20 |           20 |            20 |           20 |

## Key Findings

- Parameters are ranked by their maximum impact on cost outcomes

- Higher impact parameters should be prioritized for data quality improvements

- Tornado chart visualization highlights the most influential parameters


## Probabilistic Sensitivity Analysis (PSA)
## Simulation Details

- Monte Carlo iterations: 1000

- Parameters analyzed: 3

## Parameter Distributions

- labour_cost: normal distribution with parameters {'mean': 800, 'std': 100, 'size': 1000}

- equipment_cost: triangular distribution with parameters {'left': 400, 'mode': 600, 'right': 1000, 'size': 1000}

- consumable_cost: uniform distribution with parameters {'low': 200, 'high': 400, 'size': 1000}


## Cost Outcomes Statistics

- Mean cost: $1964.19

- Standard deviation: $163.90

- Minimum cost: $1526.89

- Maximum cost: $2456.22


## Confidence Intervals

- 2.5% percentile: $1640.26

- 25% percentile: $1844.57

- 50% percentile: $1960.53

- 75% percentile: $2085.15

- 97.5% percentile: $2282.96


## Key Findings

- Monte Carlo simulation quantifies uncertainty in cost outcomes

- Confidence intervals provide range of likely cost values

- Histogram visualization shows distribution of cost outcomes

- Results can inform decision-making under uncertainty


## Value of Information (VOI) Analysis
## Expected Value of Perfect Information (EVPI)

EVPI represents the maximum amount decision makers would be willing to pay to eliminate all uncertainty in the decision.

- EVPI: $83.25

- EVPI as percentage of mean cost: 4.23%

- Mean cost: $1968.19

- Standard deviation of cost: $166.51


## Expected Value of Partial Perfect Information (EVPPI)

EVPPI represents the value of eliminating uncertainty for specific parameter groups.

### Labor Parameters

- EVPPI: $3123.49

- EVPPI as percentage of total variance: 37.55%

- Parameters: labour_cost

### Equipment Parameters

- EVPPI: $4674.39

- EVPPI as percentage of total variance: 56.20%

- Parameters: equipment_cost

### Consumables Parameters

- EVPPI: $1041.04

- EVPPI as percentage of total variance: 12.52%

- Parameters: consumable_cost


## Cost-Effectiveness Analysis

### Net Benefit Curve

- Mean cost: $1968.19

- Mean effectiveness: 0.7976

- Net benefit curve generated across willingness-to-pay range


### Cost-Effectiveness Acceptability Curve (CEAC)

- Mean cost: $1968.19

- Mean effectiveness: 0.7976

- CEAC shows probability of cost-effectiveness across willingness-to-pay range


## Key Findings

- EVPI quantifies the maximum value of eliminating all uncertainty

- EVPPI identifies which parameter groups contribute most to decision uncertainty

- Net benefit curves help identify optimal decision strategies

- CEAC shows probability of cost-effectiveness at different willingness-to-pay thresholds

- Results can inform research prioritization and data collection investments


## Budget Impact Analysis
## Volume Sensitivity Analysis

Analysis of cost implications with varying test volumes:

|   Volume |   Total_Cost |   Volume_Change_Pct |   Cost_Change_Pct |   Cost_Per_Test |
|---------:|-------------:|--------------------:|------------------:|----------------:|
|      500 |      1e+06   |                 -50 |               -50 |            2000 |
|      750 |      1.5e+06 |                 -25 |               -25 |            2000 |
|     1000 |      2e+06   |                   0 |                 0 |            2000 |
|     1250 |      2.5e+06 |                  25 |                25 |            2000 |
|     1500 |      3e+06   |                  50 |                50 |            2000 |


## Time Horizon Analysis

Projection of costs over multiple time periods:

|   Year |   Volume |   Cost_Per_Test |   Total_Cost |
|-------:|---------:|----------------:|-------------:|
|      1 |     1000 |         2000    |  2e+06       |
|      2 |     1050 |         1960    |  2.058e+06   |
|      3 |     1102 |         1920.8  |  2.11768e+06 |
|      4 |     1158 |         1882.38 |  2.17909e+06 |
|      5 |     1216 |         1844.74 |  2.24229e+06 |


## Scenario Analysis

Comparison of different testing scenarios:

| Scenario          |   Volume |   Cost_Per_Test |   Total_Cost |
|:------------------|---------:|----------------:|-------------:|
| Current Practice  |     1000 |            2000 |     2e+06    |
| High Volume       |     1500 |            1800 |     2.7e+06  |
| New Technology    |     1200 |            2200 |     2.64e+06 |
| Optimized Process |     1100 |            1700 |     1.87e+06 |


## Economies of Scale Analysis

Cost per test at different volume levels:

|   Volume |   Fixed_Costs |   Variable_Costs |   Total_Costs |   Cost_Per_Test |
|---------:|--------------:|-----------------:|--------------:|----------------:|
|      500 |        500000 |   750000         |     1.25e+06  |         2500    |
|      750 |        500000 |        1.125e+06 |     1.625e+06 |         2166.67 |
|     1000 |        500000 |        1.5e+06   |     2e+06     |         2000    |
|     1250 |        500000 |        1.875e+06 |     2.375e+06 |         1900    |
|     1500 |        500000 |        2.25e+06  |     2.75e+06  |         1833.33 |


## Key Findings

- Volume changes have a direct linear impact on total costs in this simplified model

- Time horizon analysis shows how costs evolve with growth and efficiency improvements

- Scenario analysis enables comparison of different strategic options

- Economies of scale reduce cost per test as volume increases

- Results can inform budget planning and strategic decision-making


## Break-even Analysis
## Break-even Volume Calculation

For a typical scenario with:

- Fixed costs: $500,000

- Price per test: $2,500

- Variable cost per test: $1,500


Break-even volume: 500 tests


## Contribution Margin Analysis

Contribution margin per test: $1000.00

Contribution margin ratio: 40.00%


## Sensitivity Analysis

Break-even analysis with varying variable costs and volumes:

|   Variable_Cost_Per_Test |   Volume |        Revenue |   Variable_Costs |   Fixed_Costs |     Total_Costs |          Profit |   Break_Even_Volume |
|-------------------------:|---------:|---------------:|-----------------:|--------------:|----------------:|----------------:|--------------------:|
|                     1200 |      250 | 625000         |  300000          |        500000 | 800000          | -175000         |             384.615 |
|                     1200 |      500 |      1.25e+06  |  600000          |        500000 |      1.1e+06    |  150000         |             384.615 |
|                     1200 |      750 |      1.875e+06 |  900000          |        500000 |      1.4e+06    |  475000         |             384.615 |
|                     1200 |     1000 |      2.5e+06   |       1.2e+06    |        500000 |      1.7e+06    |  800000         |             384.615 |
|                     1200 |     1250 |      3.125e+06 |       1.5e+06    |        500000 |      2e+06      |       1.125e+06 |             384.615 |
|                     1350 |      250 | 625000         |  337500          |        500000 | 837500          | -212500         |             434.783 |
|                     1350 |      500 |      1.25e+06  |  675000          |        500000 |      1.175e+06  |   75000         |             434.783 |
|                     1350 |      750 |      1.875e+06 |       1.0125e+06 |        500000 |      1.5125e+06 |  362500         |             434.783 |
|                     1350 |     1000 |      2.5e+06   |       1.35e+06   |        500000 |      1.85e+06   |  650000         |             434.783 |
|                     1350 |     1250 |      3.125e+06 |       1.6875e+06 |        500000 |      2.1875e+06 |  937500         |             434.783 |
|                     1500 |      250 | 625000         |  375000          |        500000 | 875000          | -250000         |             500     |
|                     1500 |      500 |      1.25e+06  |  750000          |        500000 |      1.25e+06   |       0         |             500     |
|                     1500 |      750 |      1.875e+06 |       1.125e+06  |        500000 |      1.625e+06  |  250000         |             500     |
|                     1500 |     1000 |      2.5e+06   |       1.5e+06    |        500000 |      2e+06      |  500000         |             500     |
|                     1500 |     1250 |      3.125e+06 |       1.875e+06  |        500000 |      2.375e+06  |  750000         |             500     |
|                     1650 |      250 | 625000         |  412500          |        500000 | 912500          | -287500         |             588.235 |
|                     1650 |      500 |      1.25e+06  |  825000          |        500000 |      1.325e+06  |  -75000         |             588.235 |
|                     1650 |      750 |      1.875e+06 |       1.2375e+06 |        500000 |      1.7375e+06 |  137500         |             588.235 |
|                     1650 |     1000 |      2.5e+06   |       1.65e+06   |        500000 |      2.15e+06   |  350000         |             588.235 |
|                     1650 |     1250 |      3.125e+06 |       2.0625e+06 |        500000 |      2.5625e+06 |  562500         |             588.235 |
|                     1800 |      250 | 625000         |  450000          |        500000 | 950000          | -325000         |             714.286 |
|                     1800 |      500 |      1.25e+06  |  900000          |        500000 |      1.4e+06    | -150000         |             714.286 |
|                     1800 |      750 |      1.875e+06 |       1.35e+06   |        500000 |      1.85e+06   |   25000         |             714.286 |
|                     1800 |     1000 |      2.5e+06   |       1.8e+06    |        500000 |      2.3e+06    |  200000         |             714.286 |
|                     1800 |     1250 |      3.125e+06 |       2.25e+06   |        500000 |      2.75e+06   |  375000         |             714.286 |



## Minimum Efficient Scale

Minimum efficient volume: 6667 tests

Break-even volume: 500 tests

Cost per test at efficiency: $1575.00


## Service Line Analysis

Break-even analysis by service line:

| Service_Line   |   Fixed_Costs |   Price_Per_Test |   Variable_Cost_Per_Test |   Break_Even_Volume |   Contribution_Margin_Per_Test |   Contribution_Margin_Ratio |   Minimum_Efficient_Volume |
|:---------------|--------------:|-----------------:|-------------------------:|--------------------:|-------------------------------:|----------------------------:|---------------------------:|
| Panel Testing  |        200000 |             1800 |                     1000 |             250     |                            800 |                     44.4444 |                    4000    |
| WES Testing    |        400000 |             3000 |                     1800 |             333.333 |                           1200 |                     40      |                    4444.44 |
| WGS Testing    |        600000 |             4500 |                     2500 |             300     |                           2000 |                     44.4444 |                    4800    |


## Key Findings

- Break-even volume identifies the minimum number of tests needed to cover costs

- Contribution margin analysis shows profitability per test

- Sensitivity analysis reveals how changes in costs affect break-even points

- Minimum efficient scale identifies the volume where costs are minimized

- Service line analysis enables comparison across different testing types

- Results can inform pricing strategies and volume planning


## Methodology
All analyses were conducted using a systematic framework that:
- Processes all input data sheets consistently using the DataManager
- Executes Excel formula translations programmatically
- Maintains data integrity through validation checks
- Supports scenario modeling through advanced analytical modules

## Conclusions
This integrated analysis provides comprehensive insights into:
- Key cost drivers by value and proportion across all models
- Model robustness through deterministic sensitivity analysis
- Uncertainty quantification through probabilistic sensitivity analysis
- Economic value of reducing uncertainty through value of information analysis
- Budget implications of different testing volumes and scenarios
- Volume thresholds for cost recovery and minimum efficient scale
- Informed decision-making for genomics testing implementation
