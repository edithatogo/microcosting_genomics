# Model Validation: Five Distinct Models in Detailed Table

## Overview

This document validates that the genomics microcosting model contains five distinct models reflected in the original "Detailed Table". Through analysis of the Excel workbook structure and process definitions, we can identify these five separate models that share common steps and categories but represent distinct analytical approaches.

## Five Distinct Models Identified

### 1. Panel Model
The Panel model represents a targeted sequencing approach focusing on specific genes or genomic regions. This model includes:
- Specimen Collection through Report Writing stages
- Specific steps tailored for panel-based analysis
- Distinct resource requirements for targeted sequencing

### 2. Whole Exome Sequencing (WES) Model
The WES model covers comprehensive sequencing of all protein-coding regions. Key characteristics include:
- All stages from Specimen Collection to Report Writing
- Specialized library preparation steps for exome capture
- Unique equipment and consumable requirements for whole exome analysis

### 3. Whole Genome Sequencing (WGS) Model
The WGS model encompasses sequencing of the entire genome. This model features:
- Complete workflow from specimen handling to reporting
- Specific steps for whole genome library preparation
- Different computational and equipment requirements compared to panel and WES

### 4. Bioinformatics Compute Model
A specialized model focused on computational infrastructure and processing requirements:
- Dedicated compute resources for data processing
- Specific software and hardware requirements
- Separate costing for computational infrastructure

### 5. Equipment Utilization Model
A cross-cutting model that focuses on equipment usage across different sequencing approaches:
- Shared equipment across panel, WES, and WGS workflows
- Different utilization rates and costing approaches
- Maintenance and operational costs for laboratory instruments

## Shared Steps and Categories

All five models utilize the same core process steps:

1. **Specimen Collection**
   - Registration
   - Name Check
   - Venepuncture
   - Completion of forms

2. **Specimen Receipt**
   - Unpacking/Triaging
   - Rapid Registration
   - Data Entry / Data Review
   - Referrer Liaison

3. **DNA Extraction**
   - gDNA Extraction
   - gDNA QC

4. **Library Preparation**
   - dsDNA HS Quantification
   - ES Capture Kit (specific to WES)
   - HS DNA QC
   - Fragment Analysis QC

5. **Sequencing**
   - Pooling
   - Sequencing operations

6. **Bioinformatics**
   - Processing
   - Storage - Network
   - Demultiplexing
   - QC Troubleshooting
   - Manual handling

7. **Variant Filtering**
   - Filtration of primary variants

8. **Interpretation**
   - Variant prioritization and curation meetings

9. **Report Writing**
   - Report writing
   - Initial report checking
   - Management in LIS
   - Final report checking

## Model-Specific Variations

While sharing the same steps and categories, each model applies different:
- Quantity assumptions per test
- Equipment utilization rates
- Consumable requirements
- Labor distribution
- Computational resource needs

## Validation Evidence

Analysis of the "Detailed Table" confirms the presence of these five models through:
1. Distinct column groupings for each model's cost calculations
2. Model-specific quantity and price assumptions
3. Separate equipment utilization factors
4. Unique consumable requirements per model
5. Different labor distribution patterns

This structure allows for comprehensive cost analysis across multiple sequencing approaches while maintaining consistency in process definitions and categories.

## Systematic Framework for Key Outcome Calculations

Building upon the five distinct models, a systematic framework has been established to programmatically calculate key outcomes from the inputs and model. This framework encompasses multiple analytical approaches to provide comprehensive insights into cost drivers, sensitivity analysis, and economic evaluation.

### Core Calculation Engine

The foundation of the framework is a robust calculation engine that:
- Processes all input data sheets consistently using the DataManager
- Executes Excel formula translations programmatically
- Maintains data integrity through validation checks
- Supports scenario modeling through the ScenarioManager

### Cost Driver Analysis

The framework systematically identifies and quantifies cost drivers through:

1. **Absolute Value Analysis**
   - Calculates total costs for each process step across all models
   - Ranks steps by their contribution to overall costs
   - Identifies high-cost activities that warrant attention

2. **Proportional Analysis**
   - Determines percentage contribution of each step to total costs
   - Compares cost distributions across the five models
   - Highlights model-specific cost patterns

3. **Category-Level Analysis**
   - Aggregates costs by major categories (Labor, Equipment, Consumables, etc.)
   - Tracks category-level trends and variations
   - Enables targeted cost optimization strategies

### Deterministic Sensitivity Analysis (DSA)

The DSA framework evaluates model robustness by systematically varying key parameters:

1. **Parameter Identification**
   - Equipment utilization rates
   - Labor pricing variations
   - Consumable discount scenarios
   - Test throughput changes
   - Overhead percentage adjustments

2. **Analysis Implementation**
   - Uses AdvancedScenarioManager for systematic parameter variation
   - Calculates one-way sensitivity for each parameter
   - Generates tornado diagrams for visual impact assessment
   - Identifies most influential parameters on cost outcomes

3. **Reporting Outputs**
   - Tornado charts showing parameter impact
   - Sensitivity matrices for multi-parameter analysis
   - Threshold analysis for critical parameters
   - Scenario comparison reports

### Probabilistic Sensitivity Analysis (PSA)

The PSA framework quantifies uncertainty through Monte Carlo simulation:

1. **Distribution Modeling**
   - Assigns probability distributions to key parameters
   - Incorporates empirical data where available
   - Uses triangular or beta distributions for expert estimates
   - Accounts for parameter correlations

2. **Simulation Execution**
   - Performs Monte Carlo iterations (default: 1,000 runs)
   - Tracks outcome distributions for cost metrics
   - Calculates confidence intervals for results
   - Identifies stochastic dominance patterns

3. **Analysis Outputs**
   - Cost distribution histograms
   - Cumulative distribution functions
   - Probabilistic sensitivity measures
   - Value-at-risk calculations

### Value of Information Analysis

The framework includes methods to assess the economic value of reducing uncertainty:

1. **Expected Value of Perfect Information (EVPI)**
   - Calculates potential benefits of eliminating all uncertainty
   - Determines maximum acceptable cost for additional research
   - Identifies scenarios where uncertainty has greatest impact

2. **Expected Value of Partial Perfect Information (EVPPI)**
   - Evaluates value of perfect information for specific parameters
   - Prioritizes research investments by parameter importance
   - Guides targeted data collection efforts

3. **Expected Net Benefit Curves**
   - Plots net benefit against willingness-to-pay thresholds
   - Identifies optimal decision strategies under uncertainty
   - Calculates probability of cost-effectiveness

### Budget Impact Analysis

The framework supports comprehensive budget impact evaluation:

1. **Volume Sensitivity Analysis**
   - Models cost implications of test volume changes
   - Evaluates economies of scale effects
   - Assesses capacity utilization impacts

2. **Time Horizon Analysis**
   - Projects costs over multiple time periods
   - Accounts for learning curve effects
   - Incorporates technology obsolescence

3. **Comparative Scenario Modeling**
   - Evaluates cost implications of adopting new technologies
   - Assesses impact of process improvements
   - Models alternative service delivery models

### Additional Analytical Outputs

The framework also generates several other relevant outputs:

1. **Break-even Analysis**
   - Determines volume thresholds for cost recovery
   - Calculates contribution margins by service line
   - Identifies minimum efficient scale

2. **Cost-Effectiveness Analysis**
   - Compares cost per diagnostic yield across models
   - Evaluates technical efficiency metrics
   - Assesses productivity improvements

3. **Benchmarking Reports**
   - Compares results against published benchmarks
   - Identifies performance gaps and opportunities
   - Tracks performance over time

4. **Visualization Tools**
   - Interactive dashboards for data exploration
   - Comparative charts across scenarios
   - Heat maps for sensitivity analysis

### Implementation Architecture

The framework is implemented through a modular architecture that ensures:

1. **Data Consistency**
   - Unified DataManager for all data operations
   - Standardized data formats across all analyses
   - Automated validation of inputs and outputs

2. **Computational Efficiency**
   - Caching mechanisms for repeated calculations
   - Parallel processing for Monte Carlo simulations
   - Memory optimization for large datasets

3. **Extensibility**
   - Plugin architecture for custom analyses
   - Standardized interfaces for new modules
   - Configuration-driven analysis parameters

4. **Reporting Integration**
   - Automated report generation in multiple formats
   - BMJ Open compliant documentation
   - Publication-ready visualizations

This systematic framework ensures comprehensive analysis of the genomics microcosting model while maintaining the flexibility to adapt to evolving research needs and stakeholder requirements.