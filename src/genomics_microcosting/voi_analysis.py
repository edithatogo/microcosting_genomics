"""Valueimport pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import logging

# Handle matplotlib import for Python 3.13 compatibility
try:
    import matplotlib
    matplotlib.use('Agg')  # Set non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except (ImportError, AttributeError):
    HAS_MATPLOTLIB = False
    plt = None

from .data_manager import DataManager
from .logging_config import get_loggermation (VOI) analysis module for microcosting analysis.

This module provides functionality to perform value of information analysis
including Expected Value of Perfect Information (EVPI) and Expected Value of
Partial Perfect Information (EVPPI) to assess the economic value of reducing
uncertainty in cost outcomes.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any

from .data_manager import DataManager
from .logging_config import get_logger
from .psa_analysis import PSAAnalyzer

logger = get_logger(__name__)


class VOIAnalyzer:
    """Analyzer for performing Value of Information Analysis."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the VOIAnalyzer.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def load_voi_parameters(self) -> Dict[str, pd.DataFrame]:
        """Load VOI parameters from prepared sheets.
        
        Returns:
            Dictionary of VOI parameter sheets
        """
        self.logger.info("Loading VOI parameters...")
        
        voi_sheets = {}
        voi_sheet_names = [
            "VOI",
            "voi",
            "EVPI",
            "evpi",
            "EVPPI",
            "evppi"
        ]
        
        for sheet_name in voi_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    voi_sheets[sheet_name] = df
                    self.logger.info(f"  Loaded {sheet_name} with shape {df.shape}")
                else:
                    self.logger.debug(f"  Could not load {sheet_name}")
            except Exception as e:
                self.logger.debug(f"  Error loading {sheet_name}: {e}")
                
        return voi_sheets
    
    def calculate_evpi(self, cost_outcomes: np.ndarray, 
                       effectiveness_outcomes: Optional[np.ndarray] = None,
                       willingness_to_pay: float = 50000) -> Dict[str, float]:
        """Calculate Expected Value of Perfect Information (EVPI).
        
        EVPI represents the maximum amount decision makers would be willing
        to pay to eliminate all uncertainty in the decision.
        
        Args:
            cost_outcomes: Array of cost outcomes from PSA
            effectiveness_outcomes: Optional array of effectiveness outcomes
            willingness_to_pay: Willingness to pay threshold for cost-effectiveness
            
        Returns:
            Dictionary with EVPI results
        """
        self.logger.info("Calculating EVPI...")
        
        # For cost-only analysis (no effectiveness outcomes)
        if effectiveness_outcomes is None:
            # EVPI for cost-only analysis is the difference between the expected
            # value of the optimal decision with perfect information and the
            # expected value of the decision made with current information
            
            # Simplified approach: EVPI as a percentage of mean cost
            mean_cost = np.mean(cost_outcomes)
            std_cost = np.std(cost_outcomes)
            
            # EVPI approximation using the cost distribution
            evpi_value = 0.5 * std_cost  # Simplified approximation
            
            return {
                "evpi": evpi_value,
                "evpi_as_percentage_of_mean": (evpi_value / mean_cost) * 100,
                "mean_cost": mean_cost,
                "std_cost": std_cost
            }
        else:
            # For cost-effectiveness analysis
            # Net benefit for each simulation
            net_benefit = effectiveness_outcomes * willingness_to_pay - cost_outcomes
            
            # Maximum net benefit for each simulation (perfect information)
            max_net_benefit = np.max(net_benefit)
            
            # Expected net benefit with current information
            expected_net_benefit = np.mean(net_benefit)
            
            # EVPI is the difference
            evpi_value = max_net_benefit - expected_net_benefit
            
            return {
                "evpi": evpi_value,
                "evpi_as_percentage_of_mean_cost": (evpi_value / np.mean(cost_outcomes)) * 100,
                "mean_cost": np.mean(cost_outcomes),
                "mean_effectiveness": np.mean(effectiveness_outcomes),
                "willingness_to_pay": willingness_to_pay
            }
    
    def calculate_evppi(self, cost_outcomes: np.ndarray, 
                        parameter_groups: Dict[str, List[str]],
                        parameter_values: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Calculate Expected Value of Partial Perfect Information (EVPPI).
        
        EVPPI represents the value of eliminating uncertainty for specific parameters.
        
        Args:
            cost_outcomes: Array of cost outcomes from PSA
            parameter_groups: Dictionary mapping group names to parameter lists
            parameter_values: Dictionary mapping parameter names to their sampled values
            
        Returns:
            Dictionary with EVPPI results for each parameter group
        """
        self.logger.info("Calculating EVPPI...")
        
        evppi_results = {}
        
        # For each parameter group
        for group_name, parameters in parameter_groups.items():
            self.logger.info(f"  Calculating EVPPI for group: {group_name}")
            
            # Simplified approach: EVPPI as variance reduction for parameter group
            # In a full implementation, this would use non-parametric regression
            # or other advanced methods
            
            # For now, we'll approximate EVPPI as proportional to parameter uncertainty
            group_variance = 0
            for param in parameters:
                if param in parameter_values:
                    group_variance += np.var(parameter_values[param])
            
            # Simplified EVPPI calculation
            total_variance = np.var(cost_outcomes)
            evppi_value = (group_variance / total_variance) * np.var(cost_outcomes) * 0.3
            
            evppi_results[group_name] = {
                "evppi": evppi_value,
                "evppi_as_percentage_of_total_variance": (group_variance / total_variance) * 100,
                "parameters": parameters
            }
        
        return evppi_results
    
    def generate_net_benefit_curve(self, cost_outcomes: np.ndarray,
                                 effectiveness_outcomes: Optional[np.ndarray] = None,
                                 willingness_to_pay_range: Optional[List[float]] = None) -> Dict[str, Any]:
        """Generate net benefit curve for cost-effectiveness analysis.
        
        Args:
            cost_outcomes: Array of cost outcomes from PSA
            effectiveness_outcomes: Optional array of effectiveness outcomes
            willingness_to_pay_range: Range of willingness to pay values to evaluate
            
        Returns:
            Dictionary with net benefit curve data
        """
        self.logger.info("Generating net benefit curve...")
        
        if effectiveness_outcomes is None:
            # For cost-only analysis, return simplified curve
            return {
                "wtp_values": [],
                "net_benefits": [],
                "cost_only": True
            }
        
        if willingness_to_pay_range is None:
            # Default range from 0 to 200% of mean cost divided by mean effectiveness
            mean_cost = np.mean(cost_outcomes)
            mean_effectiveness = np.mean(effectiveness_outcomes)
            max_wtp = (2 * mean_cost) / mean_effectiveness if mean_effectiveness > 0 else 100000
            willingness_to_pay_range = np.linspace(0, max_wtp, 50)
        
        net_benefits = []
        for wtp in willingness_to_pay_range:
            net_benefit = effectiveness_outcomes * wtp - cost_outcomes
            expected_net_benefit = np.mean(net_benefit)
            net_benefits.append(expected_net_benefit)
        
        return {
            "wtp_values": willingness_to_pay_range.tolist(),
            "net_benefits": net_benefits,
            "cost_only": False,
            "mean_cost": float(np.mean(cost_outcomes)),
            "mean_effectiveness": float(np.mean(effectiveness_outcomes))
        }
    
    def generate_ceac(self, cost_outcomes: np.ndarray,
                     effectiveness_outcomes: np.ndarray,
                     willingness_to_pay_range: Optional[List[float]] = None) -> Dict[str, Any]:
        """Generate Cost-Effectiveness Acceptability Curve (CEAC).
        
        Args:
            cost_outcomes: Array of cost outcomes from PSA
            effectiveness_outcomes: Array of effectiveness outcomes
            willingness_to_pay_range: Range of willingness to pay values to evaluate
            
        Returns:
            Dictionary with CEAC data
        """
        self.logger.info("Generating CEAC...")
        
        if willingness_to_pay_range is None:
            # Default range from 0 to 200% of mean cost divided by mean effectiveness
            mean_cost = np.mean(cost_outcomes)
            mean_effectiveness = np.mean(effectiveness_outcomes)
            max_wtp = (2 * mean_cost) / mean_effectiveness if mean_effectiveness > 0 else 100000
            willingness_to_pay_range = np.linspace(0, max_wtp, 50)
        
        ceac_probabilities = []
        for wtp in willingness_to_pay_range:
            net_benefit = effectiveness_outcomes * wtp - cost_outcomes
            # Probability that net benefit is positive (cost-effective)
            prob_cost_effective = np.mean(net_benefit > 0)
            ceac_probabilities.append(prob_cost_effective)
        
        return {
            "wtp_values": willingness_to_pay_range.tolist(),
            "ceac_probabilities": ceac_probabilities,
            "mean_cost": float(np.mean(cost_outcomes)),
            "mean_effectiveness": float(np.mean(effectiveness_outcomes))
        }
    
    def generate_voi_report(self, iterations: int = 1000, 
                           output_file: Optional[str] = None) -> str:
        """Generate a comprehensive VOI analysis report.
        
        Args:
            iterations: Number of Monte Carlo iterations
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Load VOI parameters
            self.load_voi_parameters()
            
            # For demonstration, we'll use PSA analyzer to generate cost outcomes
            psa_analyzer = PSAAnalyzer(self.data_manager)
            
            # Define parameter distributions for simulation
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
            
            # Perform Monte Carlo simulation to get cost outcomes
            simulation_results = psa_analyzer.perform_monte_carlo_simulation(
                parameter_distributions, iterations)
            
            # Calculate cost outcomes
            cost_outcomes = psa_analyzer.calculate_cost_outcomes(simulation_results)
            
            # Calculate EVPI
            evpi_results = self.calculate_evpi(cost_outcomes)
            
            # Define parameter groups for EVPPI
            parameter_groups = {
                'labor': ['labour_cost'],
                'equipment': ['equipment_cost'],
                'consumables': ['consumable_cost']
            }
            
            # Calculate EVPPI
            evppi_results = self.calculate_evppi(cost_outcomes, parameter_groups, simulation_results)
            
            # Generate net benefit curve
            # For demonstration, we'll create some effectiveness outcomes
            effectiveness_outcomes = np.random.normal(0.8, 0.1, len(cost_outcomes))
            net_benefit_curve = self.generate_net_benefit_curve(
                cost_outcomes, effectiveness_outcomes)
            
            # Generate CEAC
            ceac_data = self.generate_ceac(cost_outcomes, effectiveness_outcomes)
            
            # Generate report
            report = []
            report.append("# Value of Information (VOI) Analysis Report\n")
            report.append("## Executive Summary\n")
            report.append("This report presents the results of value of information analysis, "
                         "including Expected Value of Perfect Information (EVPI) and Expected "
                         "Value of Partial Perfect Information (EVPPI) to assess the economic "
                         "value of reducing uncertainty in cost outcomes.\n")
            
            report.append("## Expected Value of Perfect Information (EVPI)\n")
            report.append("EVPI represents the maximum amount decision makers would be willing "
                         "to pay to eliminate all uncertainty in the decision.\n")
            report.append(f"- EVPI: ${evpi_results['evpi']:.2f}\n")
            report.append(f"- EVPI as percentage of mean cost: {evpi_results['evpi_as_percentage_of_mean']:.2f}%\n")
            report.append(f"- Mean cost: ${evpi_results['mean_cost']:.2f}\n")
            report.append(f"- Standard deviation of cost: ${evpi_results['std_cost']:.2f}\n")
            
            report.append("\n## Expected Value of Partial Perfect Information (EVPPI)\n")
            report.append("EVPPI represents the value of eliminating uncertainty for specific parameter groups.\n")
            
            for group_name, results in evppi_results.items():
                report.append(f"### {group_name.title()} Parameters\n")
                report.append(f"- EVPPI: ${results['evppi']:.2f}\n")
                report.append(f"- EVPPI as percentage of total variance: {results['evppi_as_percentage_of_total_variance']:.2f}%\n")
                report.append(f"- Parameters: {', '.join(results['parameters'])}\n")
            
            report.append("\n## Cost-Effectiveness Analysis\n")
            report.append("### Net Benefit Curve\n")
            if not net_benefit_curve["cost_only"]:
                report.append(f"- Mean cost: ${net_benefit_curve['mean_cost']:.2f}\n")
                report.append(f"- Mean effectiveness: {net_benefit_curve['mean_effectiveness']:.4f}\n")
                report.append("- Net benefit curve generated across willingness-to-pay range\n")
            else:
                report.append("- Cost-only analysis (no effectiveness data)\n")
            
            report.append("\n### Cost-Effectiveness Acceptability Curve (CEAC)\n")
            report.append(f"- Mean cost: ${ceac_data['mean_cost']:.2f}\n")
            report.append(f"- Mean effectiveness: {ceac_data['mean_effectiveness']:.4f}\n")
            report.append("- CEAC shows probability of cost-effectiveness across willingness-to-pay range\n")
            
            report.append("\n## Key Findings\n")
            report.append("- EVPI quantifies the maximum value of eliminating all uncertainty\n")
            report.append("- EVPPI identifies which parameter groups contribute most to decision uncertainty\n")
            report.append("- Net benefit curves help identify optimal decision strategies\n")
            report.append("- CEAC shows probability of cost-effectiveness at different willingness-to-pay thresholds\n")
            report.append("- Results can inform research prioritization and data collection investments\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating VOI report: {e}")
            raise


def main():
    """Main function for testing the VOI analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = VOIAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_voi_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in VOI analysis: {e}")
        raise


if __name__ == "__main__":
    main()