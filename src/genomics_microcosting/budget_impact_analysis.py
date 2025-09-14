"""Budget Impact Analysis module for microcosting analysis.

This module provides functionality to perform budget impact analysis
including volume sensitivity analysis, time horizon analysis, and
comparative scenario modeling to evaluate cost implications of
different testing strategies.
"""

import pandas as pd
from typing import Dict, List, Optional

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class BudgetImpactAnalyzer:
    """Analyzer for performing Budget Impact Analysis."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the BudgetImpactAnalyzer.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def load_budget_parameters(self) -> Dict[str, pd.DataFrame]:
        """Load budget impact parameters from prepared sheets.
        
        Returns:
            Dictionary of budget parameter sheets
        """
        self.logger.info("Loading budget impact parameters...")
        
        budget_sheets = {}
        budget_sheet_names = [
            "Budget Impact",
            "budget_impact",
            "Volume Sensitivity",
            "volume_sensitivity"
        ]
        
        for sheet_name in budget_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    budget_sheets[sheet_name] = df
                    self.logger.info(f"  Loaded {sheet_name} with shape {df.shape}")
                else:
                    self.logger.debug(f"  Could not load {sheet_name}")
            except Exception as e:
                self.logger.debug(f"  Error loading {sheet_name}: {e}")
                
        return budget_sheets
    
    def perform_volume_sensitivity_analysis(self, 
                                          base_volume: int = 1000,
                                          volume_range: Optional[List[int]] = None,
                                          cost_per_test: float = 2000.0) -> pd.DataFrame:
        """Perform volume sensitivity analysis to model cost implications of test volume changes.
        
        Args:
            base_volume: Base number of tests
            volume_range: Range of volumes to analyze (default: [500, 750, 1000, 1250, 1500])
            cost_per_test: Base cost per test
            
        Returns:
            DataFrame with volume sensitivity results
        """
        self.logger.info("Performing volume sensitivity analysis...")
        
        if volume_range is None:
            volume_range = [500, 750, 1000, 1250, 1500]
        
        results = []
        base_cost = base_volume * cost_per_test
        
        for volume in volume_range:
            # Simple linear cost model (in reality, there would be economies of scale)
            total_cost = volume * cost_per_test
            
            # Calculate percentage change from base
            volume_change_pct = ((volume - base_volume) / base_volume) * 100
            cost_change_pct = ((total_cost - base_cost) / base_cost) * 100
            
            results.append({
                'Volume': volume,
                'Total_Cost': total_cost,
                'Volume_Change_Pct': volume_change_pct,
                'Cost_Change_Pct': cost_change_pct,
                'Cost_Per_Test': cost_per_test
            })
        
        return pd.DataFrame(results)
    
    def perform_time_horizon_analysis(self,
                                    initial_volume: int = 1000,
                                    growth_rate: float = 0.05,
                                    years: int = 5,
                                    cost_per_test: float = 2000.0,
                                    annual_cost_reduction: float = 0.02) -> pd.DataFrame:
        """Perform time horizon analysis to project costs over multiple time periods.
        
        Args:
            initial_volume: Initial number of tests
            growth_rate: Annual growth rate of volume (as decimal)
            years: Number of years to project
            cost_per_test: Initial cost per test
            annual_cost_reduction: Annual cost reduction rate (as decimal)
            
        Returns:
            DataFrame with time horizon projection results
        """
        self.logger.info("Performing time horizon analysis...")
        
        results = []
        
        current_volume = initial_volume
        current_cost_per_test = cost_per_test
        
        for year in range(1, years + 1):
            total_cost = current_volume * current_cost_per_test
            
            results.append({
                'Year': year,
                'Volume': round(current_volume),
                'Cost_Per_Test': round(current_cost_per_test, 2),
                'Total_Cost': round(total_cost, 2)
            })
            
            # Update for next year
            current_volume *= (1 + growth_rate)
            current_cost_per_test *= (1 - annual_cost_reduction)
        
        return pd.DataFrame(results)
    
    def perform_scenario_analysis(self,
                                scenarios: Optional[Dict[str, Dict[str, float]]] = None) -> pd.DataFrame:
        """Perform comparative scenario modeling to evaluate cost implications of different strategies.
        
        Args:
            scenarios: Dictionary of scenarios with their parameters
            
        Returns:
            DataFrame with scenario analysis results
        """
        self.logger.info("Performing scenario analysis...")
        
        if scenarios is None:
            # Default scenarios
            scenarios = {
                'Current Practice': {
                    'volume': 1000,
                    'cost_per_test': 2000.0
                },
                'High Volume': {
                    'volume': 1500,
                    'cost_per_test': 1800.0  # Economies of scale
                },
                'New Technology': {
                    'volume': 1200,
                    'cost_per_test': 2200.0  # New technology cost
                },
                'Optimized Process': {
                    'volume': 1100,
                    'cost_per_test': 1700.0  # Process improvements
                }
            }
        
        results = []
        
        for scenario_name, params in scenarios.items():
            volume = params.get('volume', 1000)
            cost_per_test = params.get('cost_per_test', 2000.0)
            total_cost = volume * cost_per_test
            
            results.append({
                'Scenario': scenario_name,
                'Volume': volume,
                'Cost_Per_Test': cost_per_test,
                'Total_Cost': total_cost
            })
        
        return pd.DataFrame(results)
    
    def calculate_economies_of_scale(self,
                                   volume_range: List[int],
                                   fixed_costs: float = 500000.0,
                                   variable_cost_per_test: float = 1500.0) -> pd.DataFrame:
        """Calculate economies of scale effects.
        
        Args:
            volume_range: Range of volumes to analyze
            fixed_costs: Fixed costs component
            variable_cost_per_test: Variable cost per test
            
        Returns:
            DataFrame with economies of scale analysis
        """
        self.logger.info("Calculating economies of scale...")
        
        results = []
        
        for volume in volume_range:
            total_variable_costs = volume * variable_cost_per_test
            total_costs = fixed_costs + total_variable_costs
            cost_per_test = total_costs / volume
            
            results.append({
                'Volume': volume,
                'Fixed_Costs': fixed_costs,
                'Variable_Costs': total_variable_costs,
                'Total_Costs': total_costs,
                'Cost_Per_Test': round(cost_per_test, 2)
            })
        
        return pd.DataFrame(results)
    
    def generate_budget_impact_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive budget impact analysis report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Load budget parameters
            self.load_budget_parameters()
            
            # Perform volume sensitivity analysis
            volume_sensitivity = self.perform_volume_sensitivity_analysis()
            
            # Perform time horizon analysis
            time_horizon = self.perform_time_horizon_analysis()
            
            # Perform scenario analysis
            scenarios = self.perform_scenario_analysis()
            
            # Calculate economies of scale
            economies_of_scale = self.calculate_economies_of_scale([500, 750, 1000, 1250, 1500])
            
            # Generate report
            report = []
            report.append("# Budget Impact Analysis Report\n")
            report.append("## Executive Summary\n")
            report.append("This report presents the results of budget impact analysis, examining the cost implications "
                         "of different testing volumes, time horizons, and scenarios for genomics testing.\n")
            
            report.append("## Volume Sensitivity Analysis\n")
            report.append("Analysis of cost implications with varying test volumes:\n")
            report.append(volume_sensitivity.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Time Horizon Analysis\n")
            report.append("Projection of costs over multiple time periods:\n")
            report.append(time_horizon.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Scenario Analysis\n")
            report.append("Comparison of different testing scenarios:\n")
            report.append(scenarios.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Economies of Scale Analysis\n")
            report.append("Cost per test at different volume levels:\n")
            report.append(economies_of_scale.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Key Findings\n")
            report.append("- Volume changes have a direct linear impact on total costs in this simplified model\n")
            report.append("- Time horizon analysis shows how costs evolve with growth and efficiency improvements\n")
            report.append("- Scenario analysis enables comparison of different strategic options\n")
            report.append("- Economies of scale reduce cost per test as volume increases\n")
            report.append("- Results can inform budget planning and strategic decision-making\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating budget impact report: {e}")
            raise


def main():
    """Main function for testing the budget impact analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = BudgetImpactAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_budget_impact_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in budget impact analysis: {e}")
        raise


if __name__ == "__main__":
    main()