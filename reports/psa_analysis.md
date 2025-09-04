# Probabilistic Sensitivity Analysis (PSA) Report

## Executive Summary

This report presents the results of probabilistic sensitivity analysis using Monte Carlo simulation to quantify uncertainty in cost outcomes.

## Simulation Details

- Monte Carlo iterations: 1000

- Parameters analyzed: 3

## Parameter Distributions

- labour_cost: normal distribution with parameters {'mean': 800, 'std': 100, 'size': 1000}

- equipment_cost: triangular distribution with parameters {'left': 400, 'mode': 600, 'right': 1000, 'size': 1000}

- consumable_cost: uniform distribution with parameters {'low': 200, 'high': 400, 'size': 1000}


## Cost Outcomes Statistics

- Mean cost: $1973.11

- Standard deviation: $161.00

- Minimum cost: $1509.20

- Maximum cost: $2422.90


## Confidence Intervals

- 2.5% percentile: $1676.09

- 25% percentile: $1861.00

- 50% percentile: $1961.59

- 75% percentile: $2084.51

- 97.5% percentile: $2291.38


## Key Findings

- Monte Carlo simulation quantifies uncertainty in cost outcomes

- Confidence intervals provide range of likely cost values

- Histogram visualization shows distribution of cost outcomes

- Results can inform decision-making under uncertainty
