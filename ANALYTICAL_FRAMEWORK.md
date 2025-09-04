# Analytical Framework for Genomics Microcosting Model

This document describes the systematic framework implemented for programmatically calculating key outcomes from the genomics microcosting model.

## Overview

The analytical framework provides a comprehensive set of tools for analyzing the genomics microcosting model, including:

1. **Cost Driver Analysis** - Identifies key cost contributors by value and proportion
2. **Deterministic Sensitivity Analysis (DSA)** - Examines impact of parameter variation
3. **Probabilistic Sensitivity Analysis (PSA)** - Quantifies uncertainty using Monte Carlo simulation
4. **Integrated Reporting** - Combines all analyses into comprehensive reports

## Implemented Modules

### Cost Driver Analysis (`cost_driver_analysis.py`)

This module identifies and quantifies cost drivers in the microcosting model:

- **Absolute Cost Drivers**: Ranks cost contributors by their absolute value contribution
- **Proportional Cost Drivers**: Ranks cost contributors by their percentage contribution
- **Model-Specific Analysis**: Analyzes cost drivers separately for each model (Panel, WES, WGS, etc.)
- **Reporting**: Generates comprehensive cost driver analysis reports

### Deterministic Sensitivity Analysis (DSA) (`dsa_analysis.py`)

This module performs deterministic sensitivity analysis by systematically varying key parameters:

- **Parameter Loading**: Loads DSA parameters from prepared sheets
- **One-Way Sensitivity**: Analyzes impact of varying single parameters
- **Tornado Charts**: Visualizes parameter impact with tornado diagrams
- **Reporting**: Generates comprehensive DSA reports

### Probabilistic Sensitivity Analysis (PSA) (`psa_analysis.py`)

This module performs probabilistic sensitivity analysis using Monte Carlo simulation:

- **Parameter Sampling**: Samples from specified probability distributions
- **Monte Carlo Simulation**: Runs simulations with sampled parameters
- **Outcome Calculation**: Calculates cost outcomes from simulation results
- **Confidence Intervals**: Computes percentile-based confidence intervals
- **Visualization**: Generates histograms of cost outcomes
- **Reporting**: Generates comprehensive PSA reports

### Comprehensive Reporting (`comprehensive_reporting.py`)

This module integrates all analytical components into comprehensive reports:

- **Executive Summary**: Provides overview of all analyses
- **Integrated Analysis**: Combines results from all modules
- **Methodology**: Documents analytical approaches
- **Conclusions**: Summarizes key findings
- **File Output**: Saves reports in multiple formats

## Usage

### Running Individual Analyses

```bash
# Cost Driver Analysis
python scripts/analyze_cost_drivers.py

# Deterministic Sensitivity Analysis
python scripts/analyze_dsa.py

# Probabilistic Sensitivity Analysis
python scripts/analyze_psa.py
```

### Running Comprehensive Analysis

```bash
# Generate comprehensive integrated report
python scripts/generate_comprehensive_report.py
```

## Output Files

All analysis results are saved to the `reports/` directory:

- `reports/cost_driver_analysis.md` - Cost driver analysis report
- `reports/dsa_analysis.md` - Deterministic sensitivity analysis report
- `reports/psa_analysis.md` - Probabilistic sensitivity analysis report
- `reports/voi_analysis.md` - Value of information analysis report
- `reports/budget_impact_analysis.md` - Budget impact analysis report
- `reports/break_even_analysis.md` - Break-even analysis report
- `reports/comprehensive_analysis/` - Directory containing all integrated reports

## Future Extensions

The framework is designed to be extensible for additional analyses:

1. **Cost-Effectiveness Analysis** - Diagnostic yield comparisons
2. **Benchmarking** - Comparison against published benchmarks

## Technical Architecture

The framework follows a modular design with clear separation of concerns:

- **Data Management**: Unified data access through `DataManager`
- **Analysis Modules**: Independent modules for each analytical approach
- **Reporting**: Integrated reporting that combines all analyses
- **Logging**: Comprehensive logging for debugging and audit trails
- **Error Handling**: Robust error handling and reporting

## Data Flow

1. **Data Preparation**: Raw Excel data is converted to Parquet format
2. **Analysis**: Each module loads required data and performs analysis
3. **Reporting**: Results are combined into comprehensive reports
4. **Output**: Reports are saved to the reports directory

## Validation

The framework includes validation mechanisms to ensure:

- Data consistency across all analytical modules
- Proper handling of missing or corrupted data
- Accurate calculation of cost outcomes
- Reliable generation of reports and visualizations