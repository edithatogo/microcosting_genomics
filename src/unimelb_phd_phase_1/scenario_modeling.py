"""Scenario modeling tools for what-if analysis in microcosting."""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
import copy
from dataclasses import dataclass, asdict
from .calculation_engine import CalculationEngine
from .config import load_config


@dataclass
class Scenario:
    """Represents a scenario with specific parameter adjustments."""
    name: str
    description: str
    parameters: Dict[str, Any]
    adjustments: Dict[str, float]  # column -> multiplier or absolute value


class ScenarioManager:
    """Manages scenario creation, comparison, and analysis."""
    
    def __init__(self, base_data: Dict[str, pd.DataFrame]):
        """Initialize the scenario manager with base data.
        
        Args:
            base_data: Dictionary of DataFrames representing the base case data
        """
        self.base_data = base_data
        self.scenarios: Dict[str, Scenario] = {}
        self.results: Dict[str, Dict[str, pd.DataFrame]] = {}
    
    def add_scenario(self, scenario: Scenario) -> None:
        """Add a scenario to the manager.
        
        Args:
            scenario: Scenario object to add
        """
        self.scenarios[scenario.name] = scenario
    
    def add_scenario_from_dict(self, name: str, description: str, parameters: Dict[str, Any], 
                              adjustments: Dict[str, float]) -> None:
        """Add a scenario from dictionary parameters.
        
        Args:
            name: Name of the scenario
            description: Description of the scenario
            parameters: Parameters for the scenario
            adjustments: Column adjustments for the scenario
        """
        scenario = Scenario(name, description, parameters, adjustments)
        self.add_scenario(scenario)
    
    def apply_scenario(self, scenario_name: str, table_name: str) -> pd.DataFrame:
        """Apply a scenario to a specific table.
        
        Args:
            scenario_name: Name of the scenario to apply
            table_name: Name of the table to apply the scenario to
            
        Returns:
            DataFrame with scenario adjustments applied
        """
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
            
        if table_name not in self.base_data:
            raise ValueError(f"Table '{table_name}' not found in base data")
            
        scenario = self.scenarios[scenario_name]
        base_df = self.base_data[table_name].copy()
        
        # Apply adjustments
        for column, adjustment in scenario.adjustments.items():
            if column in base_df.columns:
                # If adjustment is > 1, treat as multiplier
                # If adjustment is <= 1, treat as absolute value (if positive)
                if adjustment > 1 or adjustment < 0:
                    base_df[column] = base_df[column] * adjustment
                else:
                    base_df[column] = adjustment
        
        return base_df
    
    def run_scenario_analysis(self, scenario_name: str) -> Dict[str, pd.DataFrame]:
        """Run analysis for a specific scenario across all tables.
        
        Args:
            scenario_name: Name of the scenario to run
            
        Returns:
            Dictionary of DataFrames with scenario applied to each table
        """
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
            
        results = {}
        for table_name in self.base_data.keys():
            results[table_name] = self.apply_scenario(scenario_name, table_name)
            
        self.results[scenario_name] = results
        return results
    
    def compare_scenarios(self, scenario_names: List[str], table_name: str, 
                         columns: Optional[List[str]] = None) -> pd.DataFrame:
        """Compare multiple scenarios for a specific table.
        
        Args:
            scenario_names: List of scenario names to compare
            table_name: Name of the table to compare
            columns: Specific columns to compare (if None, compare all numeric columns)
            
        Returns:
            DataFrame with scenario comparisons
        """
        # Check that all scenarios exist
        for name in scenario_names:
            if name not in self.scenarios:
                raise ValueError(f"Scenario '{name}' not found")
        
        # Run scenarios that haven't been run yet
        for name in scenario_names:
            if name not in self.results:
                self.run_scenario_analysis(name)
        
        # Get base data for comparison
        base_df = self.base_data[table_name]
        
        # Determine columns to compare
        if columns is None:
            # Select numeric columns
            columns = base_df.select_dtypes(include=['number']).columns.tolist()
        
        # Create comparison DataFrame
        comparison_data = []
        for column in columns:
            if column in base_df.columns:
                row = {'Column': column, 'Base Case': base_df[column].sum()}
                for scenario_name in scenario_names:
                    scenario_df = self.results[scenario_name][table_name]
                    if column in scenario_df.columns:
                        row[scenario_name] = scenario_df[column].sum()
                    else:
                        row[scenario_name] = 0
                comparison_data.append(row)
        
        return pd.DataFrame(comparison_data)
    
    def generate_scenario_report(self, scenario_names: List[str], 
                               output_file: Optional[str] = None) -> str:
        """Generate a report comparing multiple scenarios.
        
        Args:
            scenario_names: List of scenario names to compare
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        report = []
        report.append("# Scenario Analysis Report\n")
        report.append("## Scenario Definitions\n")
        
        # Add scenario definitions
        for name in scenario_names:
            if name in self.scenarios:
                scenario = self.scenarios[name]
                report.append(f"### {scenario.name}\n")
                report.append(f"**Description:** {scenario.description}\n")
                report.append("**Adjustments:**\n")
                for column, adjustment in scenario.adjustments.items():
                    report.append(f"  - {column}: {adjustment}\n")
                report.append("\n")
        
        # Add comparison results
        report.append("## Scenario Comparisons\n")
        
        for table_name in self.base_data.keys():
            report.append(f"### {table_name}\n")
            try:
                comparison_df = self.compare_scenarios(scenario_names, table_name)
                if not comparison_df.empty:
                    report.append(comparison_df.to_markdown(index=False))
                    report.append("\n")
            except Exception as e:
                report.append(f"Error comparing scenarios for {table_name}: {e}\n")
        
        report_str = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_str)
        
        return report_str


def create_common_scenarios() -> Dict[str, Scenario]:
    """Create common scenarios for microcosting analysis.
    
    Returns:
        Dictionary of common scenarios
    """
    scenarios = {}
    
    # Inflation scenario
    scenarios['inflation_5'] = Scenario(
        name='inflation_5',
        description='5% inflation across all cost components',
        parameters={'inflation_rate': 0.05},
        adjustments={
            'Unit Cost': 1.05,
            'Price': 1.05,
            'Hourly Rate': 1.05
        }
    )
    
    # Cost reduction scenario
    scenarios['cost_reduction_10'] = Scenario(
        name='cost_reduction_10',
        description='10% reduction in all costs through efficiency improvements',
        parameters={'reduction_rate': 0.10},
        adjustments={
            'Unit Cost': 0.90,
            'Price': 0.90,
            'Hourly Rate': 0.90
        }
    )
    
    # High throughput scenario
    scenarios['high_throughput'] = Scenario(
        name='high_throughput',
        description='50% increase in throughput reducing per-unit equipment costs',
        parameters={'throughput_increase': 0.50},
        adjustments={
            'Equipment Unit Cost': 0.67,  # 1/(1+0.50)
            'Equipment Price': 0.67
        }
    )
    
    # Labor cost increase scenario
    scenarios['labor_cost_increase'] = Scenario(
        name='labor_cost_increase',
        description='15% increase in labor costs due to market conditions',
        parameters={'labor_increase': 0.15},
        adjustments={
            'Hourly Rate': 1.15,
            'Labor Unit Cost': 1.15
        }
    )
    
    return scenarios


# Example usage function
def example_usage():
    """Example of how to use the scenario modeling tools."""
    print("Loading data for scenario analysis...")
    
    # This would typically load actual data
    # For demonstration, we'll create sample data
    sample_data = {
        'detailed_table': pd.DataFrame({
            'Step': ['A', 'B', 'C'],
            'Unit Cost': [100.0, 200.0, 150.0],
            'Price': [120.0, 220.0, 170.0],
            'Hours': [2.0, 3.0, 1.5]
        }),
        'labor_prices': pd.DataFrame({
            'Category': ['Tech', 'Manager', 'Assistant'],
            'Hourly Rate': [50.0, 80.0, 30.0]
        })
    }
    
    # Create scenario manager
    scenario_manager = ScenarioManager(sample_data)
    
    # Add common scenarios
    common_scenarios = create_common_scenarios()
    for name, scenario in common_scenarios.items():
        scenario_manager.add_scenario(scenario)
    
    # Run a scenario analysis
    print("Running inflation scenario...")
    results = scenario_manager.run_scenario_analysis('inflation_5')
    
    # Compare scenarios
    print("Comparing scenarios...")
    comparison = scenario_manager.compare_scenarios(
        ['inflation_5', 'cost_reduction_10'], 
        'detailed_table'
    )
    print(comparison)
    
    # Generate report
    print("Generating report...")
    report = scenario_manager.generate_scenario_report(
        ['inflation_5', 'cost_reduction_10', 'high_throughput']
    )
    print(report)


if __name__ == "__main__":
    example_usage()