# Analysis Configuration Report

## Executive Summary

This report presents the available analysis configurations and their parameters.

## Available Configurations


### cost_driver_analysis

- **Description**: Configuration for cost driver analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: cost_analysis, drivers

- **Parameters**: 3


#### Parameters:

- **top_n_drivers** (int)
  - Description: Number of top cost drivers to display
  - Value: 15
  - Default: 10
  - Min: 1
  - Max: 100

- **include_percentage** (bool)
  - Description: Include percentage contribution in results
  - Value: True
  - Default: True

- **model_types** (list)
  - Description: Types of models to analyze
  - Value: ['Panel', 'WES', 'WGS']
  - Default: ['Panel', 'WES', 'WGS']


### dsa_analysis

- **Description**: Configuration for deterministic sensitivity analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: sensitivity, deterministic

- **Parameters**: 3


#### Parameters:

- **parameter_variations** (list)
  - Description: Variation factors for parameter sensitivity
  - Value: [0.5, 0.75, 1.0, 1.25, 1.5]
  - Default: [0.5, 0.75, 1.0, 1.25, 1.5]

- **include_tornado** (bool)
  - Description: Include tornado diagram in results
  - Value: True
  - Default: True

- **top_sensitivity_parameters** (int)
  - Description: Number of top sensitivity parameters to display
  - Value: 10
  - Default: 10
  - Min: 1
  - Max: 50


### psa_analysis

- **Description**: Configuration for probabilistic sensitivity analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: sensitivity, probabilistic, monte_carlo

- **Parameters**: 3


#### Parameters:

- **monte_carlo_iterations** (int)
  - Description: Number of Monte Carlo iterations
  - Value: 1000
  - Default: 1000
  - Min: 100
  - Max: 100000

- **confidence_intervals** (list)
  - Description: Percentiles for confidence intervals
  - Value: [2.5, 25, 50, 75, 97.5]
  - Default: [2.5, 25, 50, 75, 97.5]

- **include_histogram** (bool)
  - Description: Include histogram visualization
  - Value: True
  - Default: True


### voi_analysis

- **Description**: Configuration for value of information analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: value_of_information, evpi, evppi

- **Parameters**: 3


#### Parameters:

- **wtp_range** (list)
  - Description: Willingness-to-pay range for VOI analysis
  - Value: [0, 100000]
  - Default: [0, 100000]

- **wtp_steps** (int)
  - Description: Number of steps in WTP range
  - Value: 100
  - Default: 100
  - Min: 10
  - Max: 1000

- **include_ceac** (bool)
  - Description: Include cost-effectiveness acceptability curve
  - Value: True
  - Default: True


### budget_impact_analysis

- **Description**: Configuration for budget impact analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: budget, impact, forecasting

- **Parameters**: 3


#### Parameters:

- **time_horizon** (int)
  - Description: Time horizon for budget impact analysis (years)
  - Value: 5
  - Default: 5
  - Min: 1
  - Max: 20

- **discount_rate** (float)
  - Description: Discount rate for future costs
  - Value: 0.03
  - Default: 0.03
  - Min: 0.0
  - Max: 0.2

- **volume_scenarios** (list)
  - Description: Volume scenarios to analyze
  - Value: ['low', 'base', 'high']
  - Default: ['low', 'base', 'high']


### break_even_analysis

- **Description**: Configuration for break-even analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: break_even, cost_recovery

- **Parameters**: 3


#### Parameters:

- **price_range** (list)
  - Description: Price range for break-even analysis
  - Value: [0, 10000]
  - Default: [0, 10000]

- **fixed_costs** (float)
  - Description: Fixed costs for break-even calculation
  - Value: 500000
  - Default: 500000
  - Min: 0

- **include_sensitivity** (bool)
  - Description: Include sensitivity analysis in break-even results
  - Value: True
  - Default: True


### cost_effectiveness_analysis

- **Description**: Configuration for cost-effectiveness analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: cost_effectiveness, icer

- **Parameters**: 3


#### Parameters:

- **effectiveness_measure** (str)
  - Description: Measure of effectiveness
  - Value: diagnostic_yield
  - Default: diagnostic_yield
  - Choices: ['diagnostic_yield', 'turnaround_time', 'accuracy']

- **include_technical_efficiency** (bool)
  - Description: Include technical efficiency metrics
  - Value: True
  - Default: True

- **comparator_model** (str)
  - Description: Comparator model for ICER calculation
  - Value: WES
  - Default: WES
  - Choices: ['Panel', 'WES', 'WGS']


### benchmarking_analysis

- **Description**: Configuration for benchmarking analysis

- **Version**: 1.0.0

- **Author**: Microcosting Team

- **Tags**: benchmarking, comparison

- **Parameters**: 3


#### Parameters:

- **benchmark_sources** (list)
  - Description: Sources of benchmark data
  - Value: ['published_literature', 'internal_data']
  - Default: ['published_literature', 'internal_data']

- **performance_metrics** (list)
  - Description: Performance metrics to benchmark
  - Value: ['cost_per_test', 'turnaround_time', 'throughput']
  - Default: ['cost_per_test', 'turnaround_time', 'throughput']

- **include_efficiency_metrics** (bool)
  - Description: Include efficiency metrics in benchmarking
  - Value: True
  - Default: True

## Key Features

- Configuration-driven analysis parameters enable flexible and customizable analyses

- Default configurations provide sensible starting points for all analysis types

- Parameter validation ensures data integrity and consistency

- Extensible design allows for custom configurations

- YAML-based configuration files for easy editing and version control
