"""End-to-end test scenarios for genomics microcosting analysis.

This module defines comprehensive end-to-end test scenarios for each analysis type
to ensure complete workflow testing of the genomics microcosting framework.
"""

import pandas as pd
from typing import Dict, List, Any


class EndToEndTestScenarios:
    """Comprehensive end-to-end test scenarios for all analysis types."""
    
    @staticmethod
    def cost_driver_analysis_scenario() -> Dict[str, Any]:
        """Scenario for testing complete cost driver analysis workflow.
        
        Returns:
            Dictionary containing all data needed for cost driver analysis
        """
        return {
            "name": "Cost Driver Analysis",
            "description": "Complete workflow for identifying and quantifying cost drivers",
            "input_data": {
                "Detailed Table": pd.DataFrame({
                    'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
                    'Category': ['Labour', 'Labour', 'Equipment', 'Equipment'],
                    'Sub-Category': ['Sequencing', 'Sequencing', 'Library Prep', 'Library Prep'],
                    'Step': ['Sample Prep', 'Sample Prep', 'Sample Prep', 'Sample Prep'],
                    'Quantity': [1.0, 1.0, 1.0, 1.0],
                    'Unit_Cost': [50000, 75000, 40000, 60000],
                    'Total_Cost': [50000, 75000, 40000, 60000]
                })
            },
            "expected_outputs": {
                "top_cost_driver": "Labour",
                "cost_drivers_count": 4,
                "total_cost": 225000
            },
            "validation_criteria": [
                "All cost drivers have positive values",
                "Percentages sum to approximately 100%",
                "Labour is identified as top cost driver",
                "All test types are represented"
            ]
        }
    
    @staticmethod
    def dsa_analysis_scenario() -> Dict[str, Any]:
        """Scenario for testing complete deterministic sensitivity analysis workflow.
        
        Returns:
            Dictionary containing all data needed for DSA analysis
        """
        return {
            "name": "Deterministic Sensitivity Analysis",
            "description": "Complete workflow for deterministic sensitivity analysis",
            "input_data": {
                "DSA - Labour Prices": pd.DataFrame({
                    'Parameter': ['Hourly Rate', 'Overtime Rate'],
                    'Baseline': [50.0, 75.0],
                    'Low': [40.0, 60.0],
                    'High': [60.0, 90.0]
                }),
                "DSA - Equipment Throughput": pd.DataFrame({
                    'Parameter': ['Utilization Rate'],
                    'Baseline': [0.8],
                    'Low': [0.6],
                    'High': [0.95]
                })
            },
            "expected_outputs": {
                "parameters_analyzed": 3,
                "sensitivity_ranges_valid": True,
                "max_impact_parameter": "Hourly Rate"
            },
            "validation_criteria": [
                "Sensitivity ranges are logical (low < baseline < high)",
                "Impact values are non-negative",
                "Hourly Rate has highest sensitivity",
                "All parameters are analyzed"
            ]
        }
    
    @staticmethod
    def psa_analysis_scenario() -> Dict[str, Any]:
        """Scenario for testing complete probabilistic sensitivity analysis workflow.
        
        Returns:
            Dictionary containing all data needed for PSA analysis
        """
        return {
            "name": "Probabilistic Sensitivity Analysis",
            "description": "Complete workflow for probabilistic sensitivity analysis",
            "input_data": {
                "PSA": pd.DataFrame({
                    'Parameter': ['Labour Cost', 'Equipment Cost', 'Consumable Cost'],
                    'Distribution': ['normal', 'normal', 'normal'],
                    'Mean': [50000, 40000, 30000],
                    'Std': [5000, 4000, 3000]
                })
            },
            "expected_outputs": {
                "monte_carlo_iterations": 1000,
                "parameters_modeled": 3,
                "cost_outcomes_generated": True,
                "confidence_intervals_calculated": True
            },
            "validation_criteria": [
                "Monte Carlo samples have correct distribution properties",
                "Cost outcomes are realistic and positive",
                "Confidence intervals are logical",
                "Statistical properties are consistent"
            ]
        }
    
    @staticmethod
    def voi_analysis_scenario() -> Dict[str, Any]:
        """Scenario for testing complete value of information analysis workflow.
        
        Returns:
            Dictionary containing all data needed for VOI analysis
        """
        return {
            "name": "Value of Information Analysis",
            "description": "Complete workflow for value of information analysis",
            "input_data": {
                "VOI": pd.DataFrame({
                    'Parameter': ['Labour Cost', 'Equipment Cost'],
                    'Description': ['Hourly labour rates', 'Equipment utilization']
                })
            },
            "expected_outputs": {
                "evpi_calculated": True,
                "evppi_groups": 2,
                "uncertainty_measured": True,
                "value_metrics_generated": True
            },
            "validation_criteria": [
                "EVPI reflects overall uncertainty",
                "EVPPI is higher for parameters with greater variance",
                "Results are mathematically consistent",
                "Uncertainty propagation is logical"
            ]
        }
    
    @staticmethod
    def budget_impact_analysis_scenario() -> Dict[str, Any]:
        """Scenario for testing complete budget impact analysis workflow.
        
        Returns:
            Dictionary containing all data needed for budget impact analysis
        """
        return {
            "name": "Budget Impact Analysis",
            "description": "Complete workflow for budget impact analysis",
            "input_data": {
                "Budget Impact": pd.DataFrame({
                    'Year': [1, 2, 3, 4, 5],
                    'Volume': [1000, 2000, 3000, 4000, 5000],
                    'Cost_Per_Test': [200, 190, 180, 175, 170],
                    'Adoption_Rate': [0.1, 0.3, 0.5, 0.7, 0.9]
                })
            },
            "expected_outputs": {
                "time_horizon_years": 5,
                "volume_projection": True,
                "cost_projection": True,
                "budget_impact_calculated": True
            },
            "validation_criteria": [
                "Volume projections are realistic",
                "Cost projections show expected trends",
                "Budget impact calculated correctly",
                "Scenario comparisons are valid"
            ]
        }
    
    @staticmethod
    def break_even_analysis_scenario() -> Dict[str, Any]:
        """Scenario for testing complete break-even analysis workflow.
        
        Returns:
            Dictionary containing all data needed for break-even analysis
        """
        return {
            "name": "Break-Even Analysis",
            "description": "Complete workflow for break-even analysis",
            "input_data": {
                "Break Even": pd.DataFrame({
                    'Scenario': ['Current', 'New_Technology'],
                    'Fixed_Costs': [100000, 150000],
                    'Variable_Cost_Per_Test': [200, 150],
                    'Price_Per_Test': [300, 300]
                })
            },
            "expected_outputs": {
                "scenarios_compared": 2,
                "break_even_points_calculated": True,
                "sensitivity_analysis_performed": True,
                "recommendations_generated": True
            },
            "validation_criteria": [
                "Break-even points are mathematically correct",
                "Sensitivity analysis covers key parameters",
                "Comparisons between scenarios are valid",
                "Recommendations are actionable"
            ]
        }
    
    @staticmethod
    def comprehensive_reporting_scenario() -> Dict[str, Any]:
        """Scenario for testing complete comprehensive reporting workflow.
        
        Returns:
            Dictionary containing all data needed for comprehensive reporting
        """
        return {
            "name": "Comprehensive Reporting",
            "description": "Complete workflow for comprehensive integrated reporting",
            "input_data": {
                # This would include data from all other analyses
                "Executive_Summary": pd.DataFrame({
                    'Metric': ['Total_Cost', 'Top_Cost_Driver', 'Key_Sensitivity'],
                    'Value': [225000, 'Labour', 'Labour_Rates'],
                    'Change_From_Baseline': [0.0, '', '']
                })
            },
            "expected_outputs": {
                "executive_summary_generated": True,
                "detailed_findings_included": True,
                "recommendations_provided": True,
                "report_complete": True
            },
            "validation_criteria": [
                "All analysis results are integrated",
                "Report structure is complete",
                "Findings are clearly presented",
                "Recommendations are evidence-based"
            ]
        }
    
    @staticmethod
    def all_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get all end-to-end test scenarios.
        
        Returns:
            Dictionary mapping scenario names to their definitions
        """
        return {
            "cost_driver": EndToEndTestScenarios.cost_driver_analysis_scenario(),
            "dsa": EndToEndTestScenarios.dsa_analysis_scenario(),
            "psa": EndToEndTestScenarios.psa_analysis_scenario(),
            "voi": EndToEndTestScenarios.voi_analysis_scenario(),
            "budget_impact": EndToEndTestScenarios.budget_impact_analysis_scenario(),
            "break_even": EndToEndTestScenarios.break_even_analysis_scenario(),
            "comprehensive_reporting": EndToEndTestScenarios.comprehensive_reporting_scenario()
        }
    
    @staticmethod
    def cross_scenario_dependencies() -> Dict[str, List[str]]:
        """Define dependencies between scenarios.
        
        Returns:
            Dictionary mapping scenario names to their dependencies
        """
        return {
            "dsa": ["cost_driver"],
            "psa": ["cost_driver"],
            "voi": ["psa"],
            "budget_impact": ["cost_driver"],
            "break_even": ["cost_driver"],
            "comprehensive_reporting": [
                "cost_driver", "dsa", "psa", "voi", 
                "budget_impact", "break_even"
            ]
        }


def generate_test_workflow():
    """Generate a complete test workflow based on all scenarios.
    
    Returns:
        List of workflow steps in execution order
    """
    scenarios = EndToEndTestScenarios.all_scenarios()
    dependencies = EndToEndTestScenarios.cross_scenario_dependencies()
    
    # Simple topological sort to determine execution order
    execution_order = []
    remaining_scenarios = list(scenarios.keys())
    
    # Start with scenarios that have no dependencies
    ready_scenarios = [name for name in remaining_scenarios 
                      if not dependencies.get(name, [])]
    
    while ready_scenarios:
        current = ready_scenarios.pop(0)
        execution_order.append(current)
        remaining_scenarios.remove(current)
        
        # Check if any remaining scenarios are now ready
        for scenario in remaining_scenarios:
            deps = dependencies.get(scenario, [])
            if all(dep in execution_order for dep in deps):
                ready_scenarios.append(scenario)
    
    return execution_order


# Example usage:
if __name__ == "__main__":
    # Generate all scenarios
    scenarios = EndToEndTestScenarios.all_scenarios()
    
    # Print scenario information
    print("END-TO-END TEST SCENARIOS:")
    print("=" * 50)
    
    for scenario_name, scenario_data in scenarios.items():
        print(f"\n{scenario_data['name']}:")
        print(f"  Description: {scenario_data['description']}")
        print(f"  Input sheets: {list(scenario_data['input_data'].keys())}")
        print(f"  Expected outputs: {scenario_data['expected_outputs']}")
        print(f"  Validation criteria: {len(scenario_data['validation_criteria'])} criteria")
    
    # Print execution order
    execution_order = generate_test_workflow()
    print(f"\nRECOMMENDED EXECUTION ORDER: {' -> '.join(execution_order)}")