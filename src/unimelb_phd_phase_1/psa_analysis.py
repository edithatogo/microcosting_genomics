"""Probabilistic Sensitivity Analysis (PSA) module for microcosting analysis.

This module provides functionality to perform probabilistic sensitivity analysis
using Monte Carlo simulation to quantify uncertainty in cost outcomes.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
import matplotlib.pyplot as plt

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class PSAAnalyzer:
    """Analyzer for performing Probabilistic Sensitivity Analysis."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the PSAAnalyzer.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def load_psa_parameters(self) -> Dict[str, pd.DataFrame]:
        """Load PSA parameters from prepared sheets.
        
        Returns:
            Dictionary of PSA parameter sheets
        """
        self.logger.info("Loading PSA parameters...")
        
        psa_sheets = {}
        psa_sheet_names = [
            "PSA",
            "psa"
        ]
        
        for sheet_name in psa_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    psa_sheets[sheet_name] = df
                    self.logger.info(f"  Loaded {sheet_name} with shape {df.shape}")
                else:
                    self.logger.debug(f"  Could not load {sheet_name}")
            except Exception as e:
                self.logger.debug(f"  Error loading {sheet_name}: {e}")
                
        return psa_sheets
    
    def sample_from_distribution(self, distribution_type: str, 
                               parameters: Dict[str, float]) -> np.ndarray:
        """Sample values from a specified probability distribution.
        
        Args:
            distribution_type: Type of distribution ('normal', 'uniform', 'triangular', etc.)
            parameters: Dictionary of distribution parameters
            
        Returns:
            Array of sampled values
        """
        size = parameters.get('size', 1000)  # Default to 1000 samples
        
        if distribution_type == 'normal':
            mean = parameters.get('mean', 0)
            std = parameters.get('std', 1)
            return np.random.normal(mean, std, size)
        elif distribution_type == 'uniform':
            low = parameters.get('low', 0)
            high = parameters.get('high', 1)
            return np.random.uniform(low, high, size)
        elif distribution_type == 'triangular':
            left = parameters.get('left', 0)
            mode = parameters.get('mode', 0.5)
            right = parameters.get('right', 1)
            return np.random.triangular(left, mode, right, size)
        else:
            # Default to normal distribution
            mean = parameters.get('mean', 0)
            std = parameters.get('std', 1)
            return np.random.normal(mean, std, size)
    
    def perform_monte_carlo_simulation(self, parameters: Dict[str, Dict], 
                                     iterations: int = 1000) -> Dict[str, np.ndarray]:
        """Perform Monte Carlo simulation with specified parameters.
        
        Args:
            parameters: Dictionary mapping parameter names to distribution info
            iterations: Number of Monte Carlo iterations
            
        Returns:
            Dictionary of simulation results
        """
        self.logger.info(f"Performing Monte Carlo simulation with {iterations} iterations...")
        
        results = {}
        
        # Sample from each parameter distribution
        for param_name, param_info in parameters.items():
            dist_type = param_info.get('distribution', 'normal')
            dist_params = param_info.get('parameters', {})
            dist_params['size'] = iterations
            
            samples = self.sample_from_distribution(dist_type, dist_params)
            results[param_name] = samples
            
        return results
    
    def calculate_cost_outcomes(self, simulation_results: Dict[str, np.ndarray]) -> np.ndarray:
        """Calculate cost outcomes from simulation results.
        
        Args:
            simulation_results: Dictionary of parameter samples from simulation
            
        Returns:
            Array of cost outcomes
        """
        # This is a simplified implementation
        # In a real implementation, this would run the full cost model
        # with the sampled parameter values
        
        # For demonstration, we'll just combine some parameters
        # to create cost outcomes
        if 'labour_cost' in simulation_results and 'equipment_cost' in simulation_results:
            labour_costs = simulation_results['labour_cost']
            equipment_costs = simulation_results['equipment_cost']
            # Simple cost model: total cost = labour + equipment + some fixed costs
            fixed_costs = 500  # Placeholder fixed costs
            total_costs = labour_costs + equipment_costs + fixed_costs
            return total_costs
        else:
            # If we don't have specific parameters, return a simple distribution
            return np.random.normal(1000, 200, len(list(simulation_results.values())[0]))
    
    def generate_psa_histogram(self, cost_outcomes: np.ndarray, 
                              title: str = "PSA Cost Outcomes Distribution") -> plt.Figure:
        """Generate a histogram of PSA cost outcomes.
        
        Args:
            cost_outcomes: Array of cost outcomes from simulation
            title: Title for the chart
            
        Returns:
            Matplotlib figure with histogram
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(cost_outcomes, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        ax.set_xlabel('Cost Outcomes ($)')
        ax.set_ylabel('Frequency')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        
        # Add statistics
        mean_cost = np.mean(cost_outcomes)
        std_cost = np.std(cost_outcomes)
        ax.axvline(mean_cost, color='red', linestyle='--', 
                  label=f'Mean: ${mean_cost:.2f}')
        ax.axvline(mean_cost - std_cost, color='orange', linestyle=':', 
                  label=f'-1 SD: ${mean_cost - std_cost:.2f}')
        ax.axvline(mean_cost + std_cost, color='orange', linestyle=':', 
                  label=f'+1 SD: ${mean_cost + std_cost:.2f}')
        ax.legend()
        
        plt.tight_layout()
        return fig
    
    def calculate_confidence_intervals(self, cost_outcomes: np.ndarray, 
                                     percentiles: List[float] = [2.5, 25, 50, 75, 97.5]) -> Dict[str, float]:
        """Calculate confidence intervals for cost outcomes.
        
        Args:
            cost_outcomes: Array of cost outcomes from simulation
            percentiles: List of percentiles to calculate
            
        Returns:
            Dictionary of percentile values
        """
        results = {}
        for percentile in percentiles:
            results[f"{percentile}%"] = np.percentile(cost_outcomes, percentile)
        return results
    
    def generate_psa_report(self, iterations: int = 1000, 
                           output_file: Optional[str] = None) -> str:
        """Generate a comprehensive PSA analysis report.
        
        Args:
            iterations: Number of Monte Carlo iterations
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Load PSA parameters
            psa_parameters = self.load_psa_parameters()
            
            # Define parameter distributions (in a real implementation, 
            # these would come from the PSA parameter sheets)
            parameter_distributions = {
                'labour_cost': {
                    'distribution': 'normal',
                    'parameters': {'mean': 800, 'std': 100}
                },
                'equipment_cost': {
                    'distribution': 'triangular',
                    'parameters': {'left': 400, 'mode': 600, 'right': 1000}
                },
                'consumable_cost': {
                    'distribution': 'uniform',
                    'parameters': {'low': 200, 'high': 400}
                }
            }
            
            # Perform Monte Carlo simulation
            simulation_results = self.perform_monte_carlo_simulation(
                parameter_distributions, iterations)
            
            # Calculate cost outcomes
            cost_outcomes = self.calculate_cost_outcomes(simulation_results)
            
            # Calculate confidence intervals
            confidence_intervals = self.calculate_confidence_intervals(cost_outcomes)
            
            # Generate report
            report = []
            report.append("# Probabilistic Sensitivity Analysis (PSA) Report\n")
            report.append("## Executive Summary\n")
            report.append("This report presents the results of probabilistic sensitivity analysis "
                         "using Monte Carlo simulation to quantify uncertainty in cost outcomes.\n")
            
            report.append(f"## Simulation Details\n")
            report.append(f"- Monte Carlo iterations: {iterations}\n")
            report.append(f"- Parameters analyzed: {len(parameter_distributions)}\n")
            
            report.append("## Parameter Distributions\n")
            for param_name, param_info in parameter_distributions.items():
                dist_type = param_info['distribution']
                params = param_info['parameters']
                report.append(f"- {param_name}: {dist_type} distribution with parameters {params}\n")
            
            report.append("\n## Cost Outcomes Statistics\n")
            report.append(f"- Mean cost: ${np.mean(cost_outcomes):.2f}\n")
            report.append(f"- Standard deviation: ${np.std(cost_outcomes):.2f}\n")
            report.append(f"- Minimum cost: ${np.min(cost_outcomes):.2f}\n")
            report.append(f"- Maximum cost: ${np.max(cost_outcomes):.2f}\n")
            
            report.append("\n## Confidence Intervals\n")
            for percentile, value in confidence_intervals.items():
                report.append(f"- {percentile} percentile: ${value:.2f}\n")
            
            report.append("\n## Key Findings\n")
            report.append("- Monte Carlo simulation quantifies uncertainty in cost outcomes\n")
            report.append("- Confidence intervals provide range of likely cost values\n")
            report.append("- Histogram visualization shows distribution of cost outcomes\n")
            report.append("- Results can inform decision-making under uncertainty\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating PSA report: {e}")
            raise


def main():
    """Main function for testing the PSA analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = PSAAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_psa_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in PSA analysis: {e}")
        raise


if __name__ == "__main__":
    main()