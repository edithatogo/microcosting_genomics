"""Test data sets representing various genomics microcosting scenarios.

This module provides standardized test data for different scenarios to ensure
consistent testing across all analytical modules.
"""

import pandas as pd
import numpy as np
from typing import Dict


class TestScenarios:
    """Collection of test scenarios for genomics microcosting analysis."""
    
    @staticmethod
    def base_case_scenario() -> Dict[str, pd.DataFrame]:
        """Base case scenario with standard parameters.
        
        Returns:
            Dictionary of DataFrames representing the base case scenario
        """
        return {
            "Detailed Table": pd.DataFrame({
                'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
                'Category': ['Labour', 'Labour', 'Labour', 'Labour'],
                'Sub-Category': ['Sequencing', 'Sequencing', 'Sequencing', 'Sequencing'],
                'Step': ['Sample Prep', 'Sample Prep', 'Sample Prep', 'Sample Prep'],
                'Quantity': [1.0, 1.0, 1.0, 1.0],
                'Unit_Cost': [50.0, 75.0, 75.0, 100.0],
                'Total_Cost': [50.0, 75.0, 75.0, 100.0]
            }),
            "DSA - Labour Prices": pd.DataFrame({
                'Parameter': ['Hourly Rate'],
                'Baseline': [50.0],
                'Low': [40.0],
                'High': [60.0]
            }),
            "PSA": pd.DataFrame({
                'Parameter': ['Labour Cost', 'Equipment Cost'],
                'Distribution': ['normal', 'normal'],
                'Mean': [50000, 40000],
                'Std': [5000, 4000]
            })
        }
    
    @staticmethod
    def high_volume_scenario() -> Dict[str, pd.DataFrame]:
        """High volume scenario with increased test volumes.
        
        Returns:
            Dictionary of DataFrames representing the high volume scenario
        """
        return {
            "Detailed Table": pd.DataFrame({
                'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
                'Category': ['Labour', 'Labour', 'Labour', 'Labour'],
                'Sub-Category': ['Sequencing', 'Sequencing', 'Sequencing', 'Sequencing'],
                'Step': ['Sample Prep', 'Sample Prep', 'Sample Prep', 'Sample Prep'],
                'Quantity': [5.0, 5.0, 5.0, 5.0],  # 5x volume
                'Unit_Cost': [50.0, 75.0, 75.0, 100.0],
                'Total_Cost': [250.0, 375.0, 375.0, 500.0]
            }),
            "DSA - Labour Prices": pd.DataFrame({
                'Parameter': ['Hourly Rate'],
                'Baseline': [50.0],
                'Low': [40.0],
                'High': [60.0]
            }),
            "Budget Impact": pd.DataFrame({
                'Year': [1, 2, 3],
                'Volume': [5000, 10000, 15000],  # High volume projection
                'Cost_Per_Test': [200, 190, 180]
            })
        }
    
    @staticmethod
    def cost_pressure_scenario() -> Dict[str, pd.DataFrame]:
        """Cost pressure scenario with increased input costs.
        
        Returns:
            Dictionary of DataFrames representing the cost pressure scenario
        """
        return {
            "Detailed Table": pd.DataFrame({
                'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
                'Category': ['Labour', 'Labour', 'Labour', 'Labour'],
                'Sub-Category': ['Sequencing', 'Sequencing', 'Sequencing', 'Sequencing'],
                'Step': ['Sample Prep', 'Sample Prep', 'Sample Prep', 'Sample Prep'],
                'Quantity': [1.0, 1.0, 1.0, 1.0],
                'Unit_Cost': [75.0, 112.5, 112.5, 150.0],  # 50% increase
                'Total_Cost': [75.0, 112.5, 112.5, 150.0]
            }),
            "DSA - Labour Prices": pd.DataFrame({
                'Parameter': ['Hourly Rate'],
                'Baseline': [75.0],  # 50% increase
                'Low': [60.0],
                'High': [90.0]
            }),
            "PSA": pd.DataFrame({
                'Parameter': ['Labour Cost', 'Equipment Cost'],
                'Distribution': ['normal', 'normal'],
                'Mean': [75000, 60000],  # 50% increase
                'Std': [7500, 6000]
            })
        }
    
    @staticmethod
    def technology_advancement_scenario() -> Dict[str, pd.DataFrame]:
        """Technology advancement scenario with improved efficiency.
        
        Returns:
            Dictionary of DataFrames representing the technology advancement scenario
        """
        return {
            "Detailed Table": pd.DataFrame({
                'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
                'Category': ['Labour', 'Labour', 'Labour', 'Labour'],
                'Sub-Category': ['Sequencing', 'Sequencing', 'Sequencing', 'Sequencing'],
                'Step': ['Sample Prep', 'Sample Prep', 'Sample Prep', 'Sample Prep'],
                'Quantity': [0.5, 0.5, 0.5, 0.5],  # 50% reduction due to efficiency
                'Unit_Cost': [50.0, 75.0, 75.0, 100.0],
                'Total_Cost': [25.0, 37.5, 37.5, 50.0]
            }),
            "DSA - Equipment Throughput": pd.DataFrame({
                'Parameter': ['Utilization Rate'],
                'Baseline': [0.95],  # Improved utilization
                'Low': [0.8],
                'High': [0.99]
            }),
            "Break Even": pd.DataFrame({
                'Parameter': ['Efficiency_Gain'],
                'Value': [0.5],
                'Description': ['50% reduction in labour hours due to automation']
            })
        }
    
    @staticmethod
    def regulatory_compliance_scenario() -> Dict[str, pd.DataFrame]:
        """Regulatory compliance scenario with additional compliance costs.
        
        Returns:
            Dictionary of DataFrames representing the regulatory compliance scenario
        """
        return {
            "Detailed Table": pd.DataFrame({
                'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
                'Category': ['Labour', 'Labour', 'Labour', 'Compliance'],
                'Sub-Category': ['Sequencing', 'Sequencing', 'Sequencing', 'Quality Control'],
                'Step': ['Sample Prep', 'Sample Prep', 'Sample Prep', 'Documentation'],
                'Quantity': [1.0, 1.0, 1.0, 1.0],
                'Unit_Cost': [50.0, 75.0, 75.0, 25.0],  # Additional compliance cost
                'Total_Cost': [50.0, 75.0, 75.0, 25.0]
            }),
            "DSA - Compliance Costs": pd.DataFrame({
                'Parameter': ['Compliance Hours'],
                'Baseline': [10.0],
                'Low': [5.0],
                'High': [15.0]
            })
        }
    
    @staticmethod
    def all_scenarios() -> Dict[str, Dict[str, pd.DataFrame]]:
        """Get all test scenarios.
        
        Returns:
            Dictionary mapping scenario names to their data
        """
        return {
            "base_case": TestScenarios.base_case_scenario(),
            "high_volume": TestScenarios.high_volume_scenario(),
            "cost_pressure": TestScenarios.cost_pressure_scenario(),
            "technology_advancement": TestScenarios.technology_advancement_scenario(),
            "regulatory_compliance": TestScenarios.regulatory_compliance_scenario()
        }


def generate_monte_carlo_samples(scenario_data: Dict[str, pd.DataFrame], 
                               iterations: int = 1000) -> Dict[str, np.ndarray]:
    """Generate Monte Carlo samples for PSA based on scenario data.
    
    Args:
        scenario_data: Dictionary of scenario data
        iterations: Number of Monte Carlo iterations
        
    Returns:
        Dictionary of parameter samples
    """
    samples = {}
    
    # If PSA data exists, use it to generate samples
    if "PSA" in scenario_data:
        psa_data = scenario_data["PSA"]
        for _, row in psa_data.iterrows():
            param_name = row['Parameter']
            if row['Distribution'] == 'normal':
                mean = row['Mean']
                std = row['Std']
                samples[param_name] = np.random.normal(mean, std, iterations)
            elif row['Distribution'] == 'uniform':
                low = row.get('Low', mean - std)
                high = row.get('High', mean + std)
                samples[param_name] = np.random.uniform(low, high, iterations)
    
    # If no PSA data, generate samples based on detailed table
    elif "Detailed Table" in scenario_data:
        detailed_data = scenario_data["Detailed Table"]
        for category in detailed_data['Category'].unique():
            category_data = detailed_data[detailed_data['Category'] == category]
            mean_cost = category_data['Total_Cost'].mean()
            std_cost = category_data['Total_Cost'].std() or mean_cost * 0.1
            samples[f"{category}_Cost"] = np.random.normal(mean_cost, std_cost, iterations)
    
    return samples


# Example usage:
if __name__ == "__main__":
    # Generate all scenarios
    scenarios = TestScenarios.all_scenarios()
    
    # Print scenario information
    for scenario_name, scenario_data in scenarios.items():
        print(f"\n{scenario_name.upper()} SCENARIO:")
        for sheet_name, data in scenario_data.items():
            print(f"  {sheet_name}: {data.shape[0]} rows, {data.shape[1]} columns")