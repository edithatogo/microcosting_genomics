"""Break-even Analysis module for microcosting analysis.

This module provides functionality to perform break-even analysis
including volume threshold calculations, contribution margin analysis,
and minimum efficient scale identification.
"""

import pandas as pd
from typing import Dict, List, Optional

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class BreakEvenAnalyzer:
    """Analyzer for performing Break-even Analysis."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the BreakEvenAnalyzer.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def load_break_even_parameters(self) -> Dict[str, pd.DataFrame]:
        """Load break-even parameters from prepared sheets.
        
        Returns:
            Dictionary of break-even parameter sheets
        """
        self.logger.info("Loading break-even parameters...")
        
        break_even_sheets = {}
        break_even_sheet_names = [
            "Break Even",
            "break_even",
            "Break-even Analysis",
            "break_even_analysis"
        ]
        
        for sheet_name in break_even_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    break_even_sheets[sheet_name] = df
                    self.logger.info(f"  Loaded {sheet_name} with shape {df.shape}")
                else:
                    self.logger.debug(f"  Could not load {sheet_name}")
            except Exception as e:
                self.logger.debug(f"  Error loading {sheet_name}: {e}")
                
        return break_even_sheets
    
    def calculate_break_even_volume(self,
                                 fixed_costs: float,
                                 price_per_test: float,
                                 variable_cost_per_test: float) -> float:
        """Calculate the break-even volume (number of tests needed to cover costs).
        
        Args:
            fixed_costs: Total fixed costs
            price_per_test: Revenue per test
            variable_cost_per_test: Variable cost per test
            
        Returns:
            Break-even volume (number of tests)
        """
        self.logger.info("Calculating break-even volume...")
        
        # Break-even volume = Fixed Costs / (Price per test - Variable cost per test)
        contribution_margin_per_test = price_per_test - variable_cost_per_test
        
        if contribution_margin_per_test <= 0:
            # No break-even point if contribution margin is zero or negative
            return float('inf')
        
        break_even_volume = fixed_costs / contribution_margin_per_test
        return break_even_volume
    
    def calculate_contribution_margin(self,
                                   price_per_test: float,
                                   variable_cost_per_test: float) -> Dict[str, float]:
        """Calculate contribution margin metrics.
        
        Args:
            price_per_test: Revenue per test
            variable_cost_per_test: Variable cost per test
            
        Returns:
            Dictionary with contribution margin metrics
        """
        self.logger.info("Calculating contribution margin...")
        
        contribution_margin_per_test = price_per_test - variable_cost_per_test
        contribution_margin_ratio = (contribution_margin_per_test / price_per_test) * 100 if price_per_test > 0 else 0
        
        return {
            'contribution_margin_per_test': contribution_margin_per_test,
            'contribution_margin_ratio': contribution_margin_ratio,
            'price_per_test': price_per_test,
            'variable_cost_per_test': variable_cost_per_test
        }
    
    def perform_sensitivity_analysis(self,
                                   fixed_costs: float,
                                   price_per_test: float,
                                   variable_cost_range: List[float],
                                   volume_range: List[int]) -> pd.DataFrame:
        """Perform sensitivity analysis on break-even volume with varying parameters.
        
        Args:
            fixed_costs: Total fixed costs
            price_per_test: Base price per test
            variable_cost_range: Range of variable costs to analyze
            volume_range: Range of volumes to analyze
            
        Returns:
            DataFrame with sensitivity analysis results
        """
        self.logger.info("Performing break-even sensitivity analysis...")
        
        results = []
        
        for variable_cost in variable_cost_range:
            for volume in volume_range:
                # Calculate revenue and costs at this volume
                revenue = price_per_test * volume
                variable_costs = variable_cost * volume
                total_costs = fixed_costs + variable_costs
                profit = revenue - total_costs
                
                # Calculate break-even volume for this variable cost
                contribution_margin = price_per_test - variable_cost
                break_even_vol = fixed_costs / contribution_margin if contribution_margin > 0 else float('inf')
                
                results.append({
                    'Variable_Cost_Per_Test': variable_cost,
                    'Volume': volume,
                    'Revenue': revenue,
                    'Variable_Costs': variable_costs,
                    'Fixed_Costs': fixed_costs,
                    'Total_Costs': total_costs,
                    'Profit': profit,
                    'Break_Even_Volume': break_even_vol
                })
        
        return pd.DataFrame(results)
    
    def calculate_minimum_efficient_scale(self,
                                       fixed_costs: float,
                                       variable_cost_per_test: float,
                                       price_per_test: float,
                                       efficiency_threshold: float = 0.95) -> Dict[str, float]:
        """Calculate the minimum efficient scale where costs are minimized.
        
        Args:
            fixed_costs: Total fixed costs
            variable_cost_per_test: Variable cost per test
            price_per_test: Price per test
            efficiency_threshold: Threshold for considering scale efficient (default: 95%)
            
        Returns:
            Dictionary with minimum efficient scale metrics
        """
        self.logger.info("Calculating minimum efficient scale...")
        
        # Calculate break-even volume
        break_even_volume = self.calculate_break_even_volume(
            fixed_costs, price_per_test, variable_cost_per_test)
        
        # At break-even, total cost per test equals price
        # As volume increases beyond break-even, cost per test decreases due to spreading fixed costs
        # Minimum efficient scale is where cost per test reaches a stable level
        
        # For simplicity, we'll assume minimum efficient scale is at a volume where
        # fixed cost per test is a small percentage of total cost per test
        target_fixed_cost_ratio = 1 - efficiency_threshold  # 5% fixed cost ratio for 95% efficiency
        
        if fixed_costs > 0 and variable_cost_per_test > 0:
            # Minimum efficient volume = Fixed costs / (Target fixed cost ratio * Variable cost per test)
            min_efficient_volume = fixed_costs / (target_fixed_cost_ratio * variable_cost_per_test)
        else:
            min_efficient_volume = break_even_volume
        
        # Calculate cost per test at minimum efficient scale
        total_cost_at_efficiency = fixed_costs + (variable_cost_per_test * min_efficient_volume)
        cost_per_test_at_efficiency = total_cost_at_efficiency / min_efficient_volume if min_efficient_volume > 0 else float('inf')
        
        return {
            'minimum_efficient_volume': min_efficient_volume,
            'break_even_volume': break_even_volume,
            'cost_per_test_at_efficiency': cost_per_test_at_efficiency,
            'efficiency_threshold': efficiency_threshold
        }
    
    def analyze_service_lines(self,
                            service_line_data: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """Analyze break-even for different service lines.
        
        Args:
            service_line_data: Dictionary with service line parameters
            
        Returns:
            DataFrame with service line break-even analysis
        """
        self.logger.info("Analyzing service lines...")
        
        results = []
        
        for service_line, params in service_line_data.items():
            fixed_costs = params.get('fixed_costs', 0)
            price_per_test = params.get('price_per_test', 0)
            variable_cost_per_test = params.get('variable_cost_per_test', 0)
            
            # Calculate break-even volume
            break_even_volume = self.calculate_break_even_volume(
                fixed_costs, price_per_test, variable_cost_per_test)
            
            # Calculate contribution margin
            contribution_margin = self.calculate_contribution_margin(
                price_per_test, variable_cost_per_test)
            
            # Calculate minimum efficient scale
            min_efficient_scale = self.calculate_minimum_efficient_scale(
                fixed_costs, variable_cost_per_test, price_per_test)
            
            results.append({
                'Service_Line': service_line,
                'Fixed_Costs': fixed_costs,
                'Price_Per_Test': price_per_test,
                'Variable_Cost_Per_Test': variable_cost_per_test,
                'Break_Even_Volume': break_even_volume,
                'Contribution_Margin_Per_Test': contribution_margin['contribution_margin_per_test'],
                'Contribution_Margin_Ratio': contribution_margin['contribution_margin_ratio'],
                'Minimum_Efficient_Volume': min_efficient_scale['minimum_efficient_volume']
            })
        
        return pd.DataFrame(results)
    
    def generate_break_even_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive break-even analysis report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Load break-even parameters
            self.load_break_even_parameters()
            
            # Calculate break-even volume for a typical scenario
            break_even_volume = self.calculate_break_even_volume(
                fixed_costs=500000.0,
                price_per_test=2500.0,
                variable_cost_per_test=1500.0)
            
            # Calculate contribution margin
            contribution_margin = self.calculate_contribution_margin(
                price_per_test=2500.0,
                variable_cost_per_test=1500.0)
            
            # Perform sensitivity analysis
            sensitivity_analysis = self.perform_sensitivity_analysis(
                fixed_costs=500000.0,
                price_per_test=2500.0,
                variable_cost_range=[1200.0, 1350.0, 1500.0, 1650.0, 1800.0],
                volume_range=[250, 500, 750, 1000, 1250])
            
            # Calculate minimum efficient scale
            min_efficient_scale = self.calculate_minimum_efficient_scale(
                fixed_costs=500000.0,
                variable_cost_per_test=1500.0,
                price_per_test=2500.0)
            
            # Analyze service lines
            service_line_data = {
                'Panel Testing': {
                    'fixed_costs': 200000.0,
                    'price_per_test': 1800.0,
                    'variable_cost_per_test': 1000.0
                },
                'WES Testing': {
                    'fixed_costs': 400000.0,
                    'price_per_test': 3000.0,
                    'variable_cost_per_test': 1800.0
                },
                'WGS Testing': {
                    'fixed_costs': 600000.0,
                    'price_per_test': 4500.0,
                    'variable_cost_per_test': 2500.0
                }
            }
            
            service_line_analysis = self.analyze_service_lines(service_line_data)
            
            # Generate report
            report = []
            report.append("# Break-even Analysis Report\n")
            report.append("## Executive Summary\n")
            report.append("This report presents the results of break-even analysis, determining volume thresholds for cost recovery, "
                         "calculating contribution margins by service line, and identifying minimum efficient scale.\n")
            
            report.append("## Break-even Volume Calculation\n")
            report.append("For a typical scenario with:\n")
            report.append("- Fixed costs: $500,000\n")
            report.append("- Price per test: $2,500\n")
            report.append("- Variable cost per test: $1,500\n")
            report.append(f"\nBreak-even volume: {break_even_volume:.0f} tests\n")
            
            report.append("\n## Contribution Margin Analysis\n")
            report.append(f"Contribution margin per test: ${contribution_margin['contribution_margin_per_test']:.2f}\n")
            report.append(f"Contribution margin ratio: {contribution_margin['contribution_margin_ratio']:.2f}%\n")
            
            report.append("\n## Sensitivity Analysis\n")
            report.append("Break-even analysis with varying variable costs and volumes:\n")
            report.append(sensitivity_analysis.to_markdown(index=False))
            report.append("\n")
            
            report.append("\n## Minimum Efficient Scale\n")
            report.append(f"Minimum efficient volume: {min_efficient_scale['minimum_efficient_volume']:.0f} tests\n")
            report.append(f"Break-even volume: {min_efficient_scale['break_even_volume']:.0f} tests\n")
            report.append(f"Cost per test at efficiency: ${min_efficient_scale['cost_per_test_at_efficiency']:.2f}\n")
            
            report.append("\n## Service Line Analysis\n")
            report.append("Break-even analysis by service line:\n")
            report.append(service_line_analysis.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Key Findings\n")
            report.append("- Break-even volume identifies the minimum number of tests needed to cover costs\n")
            report.append("- Contribution margin analysis shows profitability per test\n")
            report.append("- Sensitivity analysis reveals how changes in costs affect break-even points\n")
            report.append("- Minimum efficient scale identifies the volume where costs are minimized\n")
            report.append("- Service line analysis enables comparison across different testing types\n")
            report.append("- Results can inform pricing strategies and volume planning\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating break-even report: {e}")
            raise


def main():
    """Main function for testing the break-even analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = BreakEvenAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_break_even_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in break-even analysis: {e}")
        raise


if __name__ == "__main__":
    main()