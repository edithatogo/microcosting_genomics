# Scenario Analysis Documentation

The Scenario Analysis system provides comprehensive tools for performing deterministic and probabilistic sensitivity analyses on microcosting data.

## Overview

The scenario analysis system enables researchers to explore how changes in key parameters affect the results of microcosting calculations. It supports both deterministic sensitivity analysis (DSA) and probabilistic sensitivity analysis (PSA) with customizable scenarios.

## Architecture

The scenario analysis system follows a modular architecture with the following key components:

### Core Classes

1. **AdvancedScenarioAnalyzer** - Main class for scenario analysis operations
2. **DeterministicAnalyzer** - Handles deterministic sensitivity analysis
3. **ProbabilisticAnalyzer** - Handles probabilistic sensitivity analysis
4. **ScenarioManager** - Manages scenario definitions and execution

### Design Principles

- **Standardization**: Consistent approach to all sensitivity analyses
- **Flexibility**: Support for custom scenarios and parameters
- **Extensibility**: Modular design for adding new analysis types
- **Reproducibility**: Documented and repeatable analysis workflows

## Key Features

### Deterministic Sensitivity Analysis (DSA)
Support for systematic variation of key parameters:

```python
from unimelb_phd_phase_1.advanced_scenario_modeling import AdvancedScenarioAnalyzer

# Initialize analyzer
analyzer = AdvancedScenarioAnalyzer()

# Perform DSA
dsa_results = analyzer.perform_deterministic_analysis(
    baseline_data=baseline_df,
    parameters=dsa_parameters
)
```

Key DSA capabilities:
- Parameter variation analysis
- Regional sensitivity testing
- Equipment utilization scenarios
- Labor rate variations
- Overhead percentage changes

### Probabilistic Sensitivity Analysis (PSA)
Support for Monte Carlo simulation and probabilistic modeling:

```python
# Perform PSA
psa_results = analyzer.perform_probabilistic_analysis(
    baseline_data=baseline_df,
    parameters=psa_parameters,
    simulation_count=1000
)
```

Key PSA capabilities:
- Monte Carlo simulation
- Distribution parameter estimation
- Uncertainty quantification
- Confidence interval calculation
- Sensitivity index computation

### Custom Scenario Modeling
Support for user-defined scenarios:

```python
# Define custom scenario
custom_scenario = {
    "name": "High_volume_scenario",
    "description": "Analysis with 2x test volume",
    "parameters": {
        "test_volume_multiplier": 2.0
    }
}

# Perform custom analysis
custom_results = analyzer.perform_custom_scenario(
    baseline_data=baseline_df,
    scenario=custom_scenario
)
```

### Comparison and Visualization
Advanced comparison features:
- Side-by-side scenario comparisons
- Tornado charts for sensitivity visualization
- Distribution plots for PSA results
- Interactive dashboards

## Usage

### Basic Scenario Analysis

```python
from unimelb_phd_phase_1.advanced_scenario_modeling import AdvancedScenarioAnalyzer
from unimelb_phd_phase_1.data_manager import DataManager

# Initialize components
dm = DataManager()
analyzer = AdvancedScenarioAnalyzer()

# Load baseline data
baseline_df = dm.load_sheet("Detailed Table")

# Load DSA parameters
dsa_parameters = {
    "labor_rates": dm.load_sheet("DSA - Labor Prices"),
    "equipment_throughput": dm.load_sheet("DSA - Equipment Throughput"),
    "overheads": dm.load_sheet("DSA - Overheads"),
    "consumable_discounts": dm.load_sheet("DSA - Consumable Discounts")
}

# Perform DSA
dsa_results = analyzer.perform_deterministic_analysis(
    baseline_data=baseline_df,
    parameters=dsa_parameters
)

# Save results
dm.save_sheet("DSA_Results", dsa_results)
```

### Advanced Probabilistic Analysis

```python
# Load PSA parameters
psa_parameters = dm.load_sheet("PSA")

# Perform PSA with 5000 simulations
psa_results = analyzer.perform_probabilistic_analysis(
    baseline_data=baseline_df,
    parameters=psa_parameters,
    simulation_count=5000,
    random_seed=42
)

# Generate summary statistics
summary = analyzer.generate_psa_summary(psa_results)
print(f"Mean cost: {summary['mean_cost']}")
print(f"95% CI: {summary['confidence_interval_95']}")
```

### Custom Scenario Definition

```python
# Define multiple custom scenarios
scenarios = [
    {
        "name": "Optimistic",
        "description": "Best case scenario with reduced costs",
        "parameters": {
            "labor_cost_multiplier": 0.8,
            "equipment_cost_multiplier": 0.9,
            "consumable_cost_multiplier": 0.85
        }
    },
    {
        "name": "Pessimistic",
        "description": "Worst case scenario with increased costs",
        "parameters": {
            "labor_cost_multiplier": 1.2,
            "equipment_cost_multiplier": 1.1,
            "consumable_cost_multiplier": 1.15
        }
    }
]

# Perform all custom scenarios
for scenario in scenarios:
    results = analyzer.perform_custom_scenario(
        baseline_data=baseline_df,
        scenario=scenario
    )
    
    # Save individual results
    dm.save_sheet(f"Scenario_{scenario['name']}", results)
```

### Scenario Analysis Scripts

The system includes standardized scripts for scenario analysis:

```bash
# Perform all scenario analyses
python scripts/analyze_scenarios.py

# Run advanced scenario analysis
python scripts/run_advanced_scenario_analysis.py
```

## Analysis Types

### One-way Sensitivity Analysis
Examination of the effect of varying one parameter at a time:

```python
# Perform one-way sensitivity analysis
one_way_results = analyzer.perform_one_way_sensitivity(
    baseline_data=baseline_df,
    parameter_name="labor_rate",
    parameter_values=[0.8, 0.9, 1.0, 1.1, 1.2]
)
```

### Multi-way Sensitivity Analysis
Examination of the effect of varying multiple parameters simultaneously:

```python
# Perform multi-way sensitivity analysis
multi_way_results = analyzer.perform_multi_way_sensitivity(
    baseline_data=baseline_df,
    parameters={
        "labor_rate": [0.9, 1.0, 1.1],
        "equipment_utilization": [0.8, 1.0, 1.2]
    }
)
```

### Threshold Analysis
Determination of parameter values at which decisions change:

```python
# Perform threshold analysis
threshold_results = analyzer.perform_threshold_analysis(
    baseline_data=baseline_df,
    parameter_name="labor_rate",
    decision_function=custom_decision_function
)
```

## Visualization and Reporting

### Tornado Charts
Visualization of parameter sensitivity:

```python
# Generate tornado chart
tornado_fig = analyzer.generate_tornado_chart(dsa_results)
tornado_fig.show()
```

### Distribution Plots
Visualization of PSA results:

```python
# Generate distribution plot
dist_fig = analyzer.generate_distribution_plot(psa_results, "total_cost")
dist_fig.show()
```

### Sensitivity Indices
Calculation of sensitivity measures:

```python
# Calculate sensitivity indices
sensitivity_indices = analyzer.calculate_sensitivity_indices(
    psa_results,
    parameters=psa_parameters
)
```

## Performance Considerations

### Simulation Optimization
- Parallel processing for Monte Carlo simulations
- Memory-efficient result storage
- Progress tracking for long-running analyses

### Computational Efficiency
- Vectorized operations where possible
- Caching of intermediate results
- Early stopping for convergent simulations

### Resource Management
- Configurable simulation counts
- Memory usage monitoring
- Disk-based storage for large results

## Extensibility

### Adding New Analysis Types
To add support for new analysis types:

1. Create a new analyzer class extending the base analyzer
2. Implement the specific analysis logic
3. Register the analyzer with the scenario manager
4. Add command-line interface if needed

### Custom Decision Functions
Custom decision functions can be implemented for threshold analysis:

```python
def custom_decision_function(results):
    # Implement custom decision logic
    return decision_result
```

### New Visualization Types
Additional visualization types can be added by extending the visualization module:

```python
def generate_custom_chart(results):
    # Implement custom visualization
    return figure
```

## Integration with Other Components

### Data Management
The scenario analysis system integrates with the data management system:
- Loads input data through DataManager
- Saves results in standardized formats
- Generates metadata for analyses

### Calculation Engine
Integration with the calculation engine:
- Uses calculated results as baseline
- Performs recalculations with modified parameters
- Validates results against ground truth

### Reporting System
Support for the reporting system:
- Export results in multiple formats
- Generate summary statistics
- Create visualization outputs

## Testing

The scenario analysis system includes comprehensive tests covering:
- DSA accuracy and correctness
- PSA statistical properties
- Custom scenario execution
- Visualization output quality
- Performance benchmarks

Run tests with:
```bash
python -m pytest tests/test_scenario_analysis.py
```

## API Reference

### AdvancedScenarioAnalyzer Class

#### `__init__()`
Initialize the AdvancedScenarioAnalyzer.

#### `perform_deterministic_analysis(baseline_data, parameters)`
Perform deterministic sensitivity analysis.

**Parameters:**
- `baseline_data` (pd.DataFrame): Baseline calculation results
- `parameters` (dict): DSA parameter sheets

**Returns:**
- DSA analysis results

#### `perform_probabilistic_analysis(baseline_data, parameters, simulation_count=1000, random_seed=None)`
Perform probabilistic sensitivity analysis.

**Parameters:**
- `baseline_data` (pd.DataFrame): Baseline calculation results
- `parameters` (pd.DataFrame): PSA parameter data
- `simulation_count` (int): Number of Monte Carlo simulations
- `random_seed` (int, optional): Random seed for reproducibility

**Returns:**
- PSA analysis results

#### `perform_custom_scenario(baseline_data, scenario)`
Perform custom scenario analysis.

**Parameters:**
- `baseline_data` (pd.DataFrame): Baseline calculation results
- `scenario` (dict): Custom scenario definition

**Returns:**
- Custom scenario results

#### `generate_tornado_chart(dsa_results)`
Generate tornado chart for DSA results.

**Parameters:**
- `dsa_results` (dict): DSA analysis results

**Returns:**
- Plotly figure object

#### `calculate_sensitivity_indices(psa_results, parameters)`
Calculate sensitivity indices from PSA results.

**Parameters:**
- `psa_results` (dict): PSA analysis results
- `parameters` (dict): PSA parameter definitions

**Returns:**
- Sensitivity indices dictionary