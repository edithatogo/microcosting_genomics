"""Cost-Effectiveness Analysis module for microcosting analysis.

This module provides functionality to perform cost-effectiveness analysis
including cost per diagnostic yield comparisons, technical efficiency metrics,
and productivity improvements assessment.
"""

import pandas as pd
from typing import Dict, Optional

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class CostEffectivenessAnalyzer:
    """Analyzer for performing Cost-Effectiveness Analysis."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the CostEffectivenessAnalyzer.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def load_cost_effectiveness_parameters(self) -> Dict[str, pd.DataFrame]:
        """Load cost-effectiveness parameters from prepared sheets.
        
        Returns:
            Dictionary of cost-effectiveness parameter sheets
        """
        self.logger.info("Loading cost-effectiveness parameters...")
        
        cost_effectiveness_sheets = {}
        cost_effectiveness_sheet_names = [
            "Cost Effectiveness",
            "cost_effectiveness",
            "Cost-Effectiveness Analysis",
            "cost_effectiveness_analysis"
        ]
        
        for sheet_name in cost_effectiveness_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    cost_effectiveness_sheets[sheet_name] = df
                    self.logger.info(f"  Loaded {sheet_name} with shape {df.shape}")
                else:
                    self.logger.debug(f"  Could not load {sheet_name}")
            except Exception as e:
                self.logger.debug(f"  Error loading {sheet_name}: {e}")
                
        return cost_effectiveness_sheets
    
    def calculate_cost_per_diagnostic_yield(self,
                                         cost_per_test: float,
                                         diagnostic_yield_rate: float) -> float:
        """Calculate cost per diagnostic yield.
        
        Args:
            cost_per_test: Cost per test
            diagnostic_yield_rate: Diagnostic yield rate (positive results per test)
            
        Returns:
            Cost per diagnostic yield
        """
        self.logger.info("Calculating cost per diagnostic yield...")
        
        if diagnostic_yield_rate <= 0:
            return float('inf')
        
        cost_per_diagnostic_yield = cost_per_test / diagnostic_yield_rate
        return cost_per_diagnostic_yield
    
    def compare_cost_effectiveness_across_models(self,
                                              model_data: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """Compare cost-effectiveness across different testing models.
        
        Args:
            model_data: Dictionary with model parameters
            
        Returns:
            DataFrame with cost-effectiveness comparison
        """
        self.logger.info("Comparing cost-effectiveness across models...")
        
        results = []
        
        for model_name, params in model_data.items():
            cost_per_test = params.get('cost_per_test', 0)
            diagnostic_yield_rate = params.get('diagnostic_yield_rate', 0)
            turnaround_time = params.get('turnaround_time', 0)
            
            # Calculate cost per diagnostic yield
            cost_per_diagnostic_yield = self.calculate_cost_per_diagnostic_yield(
                cost_per_test, diagnostic_yield_rate)
            
            # Calculate efficiency score (higher is better)
            # We'll use a composite score based on cost effectiveness and speed
            efficiency_score = 0
            if cost_per_diagnostic_yield > 0 and turnaround_time > 0:
                efficiency_score = 1 / (cost_per_diagnostic_yield * turnaround_time)
            
            results.append({
                'Model': model_name,
                'Cost_Per_Test': cost_per_test,
                'Diagnostic_Yield_Rate': diagnostic_yield_rate,
                'Turnaround_Time': turnaround_time,
                'Cost_Per_Diagnostic_Yield': cost_per_diagnostic_yield,
                'Efficiency_Score': efficiency_score
            })
        
        df = pd.DataFrame(results)
        # Sort by efficiency score (descending)
        df = df.sort_values('Efficiency_Score', ascending=False)
        return df
    
    def calculate_technical_efficiency_metrics(self,
                                            observed_output: float,
                                            observed_input: float,
                                            best_practice_output: float,
                                            best_practice_input: float) -> Dict[str, float]:
        """Calculate technical efficiency metrics.
        
        Args:
            observed_output: Observed output level
            observed_input: Observed input level
            best_practice_output: Best practice output level
            best_practice_input: Best practice input level
            
        Returns:
            Dictionary with technical efficiency metrics
        """
        self.logger.info("Calculating technical efficiency metrics...")
        
        # Technical efficiency = (Observed output / Best practice output) / 
        #                        (Observed input / Best practice input)
        if observed_input > 0 and best_practice_input > 0 and best_practice_output > 0:
            technical_efficiency = (observed_output / best_practice_output) / (observed_input / best_practice_input)
        else:
            technical_efficiency = 0
            
        # Cost efficiency = Observed cost / Best practice cost
        observed_cost = observed_input  # Simplified assumption
        best_practice_cost = best_practice_input  # Simplified assumption
        cost_efficiency = observed_cost / best_practice_cost if best_practice_cost > 0 else 0
        
        return {
            'technical_efficiency': technical_efficiency,
            'cost_efficiency': cost_efficiency,
            'observed_output': observed_output,
            'observed_input': observed_input,
            'best_practice_output': best_practice_output,
            'best_practice_input': best_practice_input
        }
    
    def assess_productivity_improvements(self,
                                       baseline_data: Dict[str, float],
                                       current_data: Dict[str, float]) -> Dict[str, float]:
        """Assess productivity improvements over time.
        
        Args:
            baseline_data: Baseline performance data
            current_data: Current performance data
            
        Returns:
            Dictionary with productivity improvement metrics
        """
        self.logger.info("Assessing productivity improvements...")
        
        baseline_tests = baseline_data.get('tests_completed', 0)
        baseline_cost = baseline_data.get('total_cost', 0)
        baseline_time = baseline_data.get('total_time', 0)
        
        current_tests = current_data.get('tests_completed', 0)
        current_cost = current_data.get('total_cost', 0)
        current_time = current_data.get('total_time', 0)
        
        # Calculate productivity metrics
        baseline_productivity = baseline_tests / baseline_time if baseline_time > 0 else 0
        current_productivity = current_tests / current_time if current_time > 0 else 0
        
        # Calculate improvement percentages
        test_volume_improvement = ((current_tests - baseline_tests) / baseline_tests) * 100 if baseline_tests > 0 else 0
        cost_efficiency_improvement = ((baseline_cost - current_cost) / baseline_cost) * 100 if baseline_cost > 0 else 0
        productivity_improvement = ((current_productivity - baseline_productivity) / baseline_productivity) * 100 if baseline_productivity > 0 else 0
        
        # Calculate cost per test improvements
        baseline_cost_per_test = baseline_cost / baseline_tests if baseline_tests > 0 else 0
        current_cost_per_test = current_cost / current_tests if current_tests > 0 else 0
        cost_per_test_improvement = ((baseline_cost_per_test - current_cost_per_test) / baseline_cost_per_test) * 100 if baseline_cost_per_test > 0 else 0
        
        return {
            'test_volume_improvement_pct': test_volume_improvement,
            'cost_efficiency_improvement_pct': cost_efficiency_improvement,
            'productivity_improvement_pct': productivity_improvement,
            'cost_per_test_improvement_pct': cost_per_test_improvement,
            'baseline_tests': baseline_tests,
            'current_tests': current_tests,
            'baseline_cost': baseline_cost,
            'current_cost': current_cost,
            'baseline_productivity': baseline_productivity,
            'current_productivity': current_productivity
        }
    
    def perform_incremental_cost_effectiveness_analysis(self,
                                                     intervention_cost: float,
                                                     intervention_effectiveness: float,
                                                     comparator_cost: float,
                                                     comparator_effectiveness: float) -> Dict[str, float]:
        """Perform incremental cost-effectiveness analysis.
        
        Args:
            intervention_cost: Cost of new intervention
            intervention_effectiveness: Effectiveness of new intervention
            comparator_cost: Cost of comparator
            comparator_effectiveness: Effectiveness of comparator
            
        Returns:
            Dictionary with incremental cost-effectiveness metrics
        """
        self.logger.info("Performing incremental cost-effectiveness analysis...")
        
        # Calculate incremental cost and effectiveness
        incremental_cost = intervention_cost - comparator_cost
        incremental_effectiveness = intervention_effectiveness - comparator_effectiveness
        
        # Calculate incremental cost-effectiveness ratio (ICER)
        icer = incremental_cost / incremental_effectiveness if incremental_effectiveness > 0 else float('inf')
        
        # Determine if intervention is dominant (more effective and less costly)
        is_intervention_dominant = incremental_cost < 0 and incremental_effectiveness > 0
        
        # Determine if comparator is dominant (less costly and more effective)
        is_comparator_dominant = incremental_cost > 0 and incremental_effectiveness < 0
        
        return {
            'incremental_cost': incremental_cost,
            'incremental_effectiveness': incremental_effectiveness,
            'icer': icer,
            'is_intervention_dominant': is_intervention_dominant,
            'is_comparator_dominant': is_comparator_dominant,
            'intervention_cost': intervention_cost,
            'intervention_effectiveness': intervention_effectiveness,
            'comparator_cost': comparator_cost,
            'comparator_effectiveness': comparator_effectiveness
        }
    
    def generate_cost_effectiveness_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive cost-effectiveness analysis report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Load cost-effectiveness parameters
            self.load_cost_effectiveness_parameters()
            
            # Compare cost-effectiveness across models
            model_data = {
                'Panel Testing': {
                    'cost_per_test': 1800.0,
                    'diagnostic_yield_rate': 0.15,  # 15% yield rate
                    'turnaround_time': 7  # days
                },
                'WES Testing': {
                    'cost_per_test': 3000.0,
                    'diagnostic_yield_rate': 0.30,  # 30% yield rate
                    'turnaround_time': 14  # days
                },
                'WGS Testing': {
                    'cost_per_test': 4500.0,
                    'diagnostic_yield_rate': 0.40,  # 40% yield rate
                    'turnaround_time': 21  # days
                }
            }
            
            model_comparison = self.compare_cost_effectiveness_across_models(model_data)
            
            # Calculate technical efficiency metrics
            technical_efficiency = self.calculate_technical_efficiency_metrics(
                observed_output=1000,
                observed_input=2000000,
                best_practice_output=1200,
                best_practice_input=1800000
            )
            
            # Assess productivity improvements
            baseline_data = {
                'tests_completed': 800,
                'total_cost': 1800000,
                'total_time': 30  # days
            }
            
            current_data = {
                'tests_completed': 1000,
                'total_cost': 2000000,
                'total_time': 30  # days
            }
            
            productivity_improvements = self.assess_productivity_improvements(baseline_data, current_data)
            
            # Perform incremental cost-effectiveness analysis
            icer_analysis = self.perform_incremental_cost_effectiveness_analysis(
                intervention_cost=4500.0,  # WGS
                intervention_effectiveness=0.40,  # 40% yield
                comparator_cost=3000.0,  # WES
                comparator_effectiveness=0.30  # 30% yield
            )
            
            # Generate report
            report = []
            report.append("# Cost-Effectiveness Analysis Report\n")
            report.append("## Executive Summary\n")
            report.append("This report presents the results of cost-effectiveness analysis, comparing cost per diagnostic yield "
                         "across models, evaluating technical efficiency metrics, and assessing productivity improvements.\n")
            
            report.append("## Cost-Effectiveness Comparison Across Models\n")
            report.append("Comparison of cost-effectiveness across different testing models:\n")
            report.append(model_comparison.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Technical Efficiency Metrics\n")
            report.append(f"Technical efficiency: {technical_efficiency['technical_efficiency']:.4f}\n")
            report.append(f"Cost efficiency: {technical_efficiency['cost_efficiency']:.4f}\n")
            report.append(f"Observed output: {technical_efficiency['observed_output']}\n")
            report.append(f"Observed input: {technical_efficiency['observed_input']}\n")
            report.append(f"Best practice output: {technical_efficiency['best_practice_output']}\n")
            report.append(f"Best practice input: {technical_efficiency['best_practice_input']}\n")
            
            report.append("\n## Productivity Improvements\n")
            report.append(f"Test volume improvement: {productivity_improvements['test_volume_improvement_pct']:.2f}%\n")
            report.append(f"Cost efficiency improvement: {productivity_improvements['cost_efficiency_improvement_pct']:.2f}%\n")
            report.append(f"Productivity improvement: {productivity_improvements['productivity_improvement_pct']:.2f}%\n")
            report.append(f"Cost per test improvement: {productivity_improvements['cost_per_test_improvement_pct']:.2f}%\n")
            report.append(f"Baseline tests: {productivity_improvements['baseline_tests']}\n")
            report.append(f"Current tests: {productivity_improvements['current_tests']}\n")
            report.append(f"Baseline cost: ${productivity_improvements['baseline_cost']:,.2f}\n")
            report.append(f"Current cost: ${productivity_improvements['current_cost']:,.2f}\n")
            
            report.append("\n## Incremental Cost-Effectiveness Analysis\n")
            report.append(f"Intervention cost (WGS): ${icer_analysis['intervention_cost']:,.2f}\n")
            report.append(f"Intervention effectiveness (WGS): {icer_analysis['intervention_effectiveness']:.2f}\n")
            report.append(f"Comparator cost (WES): ${icer_analysis['comparator_cost']:,.2f}\n")
            report.append(f"Comparator effectiveness (WES): {icer_analysis['comparator_effectiveness']:.2f}\n")
            report.append(f"Incremental cost: ${icer_analysis['incremental_cost']:,.2f}\n")
            report.append(f"Incremental effectiveness: {icer_analysis['incremental_effectiveness']:.4f}\n")
            report.append(f"ICER (Incremental Cost-Effectiveness Ratio): ${icer_analysis['icer']:,.2f} per unit of effectiveness\n")
            report.append(f"Is WGS dominant? {icer_analysis['is_intervention_dominant']}\n")
            report.append(f"Is WES dominant? {icer_analysis['is_comparator_dominant']}\n")
            
            report.append("\n## Key Findings\n")
            report.append("- Model comparison identifies the most cost-effective testing approach\n")
            report.append("- Technical efficiency metrics benchmark performance against best practices\n")
            report.append("- Productivity improvements track operational enhancements over time\n")
            report.append("- Incremental cost-effectiveness analysis compares new interventions to existing approaches\n")
            report.append("- Results can inform technology adoption and resource allocation decisions\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating cost-effectiveness report: {e}")
            raise


def main():
    """Main function for testing the cost-effectiveness analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = CostEffectivenessAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_cost_effectiveness_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in cost-effectiveness analysis: {e}")
        raise


if __name__ == "__main__":
    main()