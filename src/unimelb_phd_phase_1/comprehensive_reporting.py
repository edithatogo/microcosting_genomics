"""Comprehensive reporting module for microcosting analysis.

This module integrates all analytical components to generate comprehensive reports
for the genomics microcosting model.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import logging
from datetime import datetime

from .data_manager import DataManager
from .cost_driver_analysis import CostDriverAnalyzer
from .dsa_analysis import DSAAnalyzer
from .psa_analysis import PSAAnalyzer
from .voi_analysis import VOIAnalyzer
from .budget_impact_analysis import BudgetImpactAnalyzer
from .break_even_analysis import BreakEvenAnalyzer
from .logging_config import get_logger

logger = get_logger(__name__)


class ComprehensiveReporter:
    """Comprehensive reporter that integrates all analytical components."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the ComprehensiveReporter.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize analyzers
        self.cost_driver_analyzer = CostDriverAnalyzer(data_manager)
        self.dsa_analyzer = DSAAnalyzer(data_manager)
        self.psa_analyzer = PSAAnalyzer(data_manager)
        self.voi_analyzer = VOIAnalyzer(data_manager)
        self.budget_impact_analyzer = BudgetImpactAnalyzer(data_manager)
        self.break_even_analyzer = BreakEvenAnalyzer(data_manager)
    
    def generate_executive_summary(self) -> str:
        """Generate an executive summary of all analyses.
        
        Returns:
            Executive summary as a string
        """
        summary = []
        summary.append("# Comprehensive Microcosting Analysis Report")
        summary.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("")
        summary.append("## Executive Summary")
        summary.append("This comprehensive report integrates cost driver analysis, deterministic sensitivity analysis (DSA), "
                      "probabilistic sensitivity analysis (PSA), value of information (VOI) analysis, budget impact "
                      "analysis, and break-even analysis to provide a complete picture of the genomics microcosting model.")
        summary.append("")
        summary.append("## Analysis Components")
        summary.append("1. **Cost Driver Analysis**: Identifies key cost contributors by value and proportion")
        summary.append("2. **Deterministic Sensitivity Analysis (DSA)**: Examines impact of parameter variation")
        summary.append("3. **Probabilistic Sensitivity Analysis (PSA)**: Quantifies uncertainty using Monte Carlo simulation")
        summary.append("4. **Value of Information (VOI) Analysis**: Assesses economic value of reducing uncertainty")
        summary.append("5. **Budget Impact Analysis**: Evaluates cost implications of different testing volumes and scenarios")
        summary.append("6. **Break-even Analysis**: Determines volume thresholds for cost recovery and minimum efficient scale")
        summary.append("")
        
        return "\n".join(summary)
    
    def generate_integrated_report(self, output_dir: Optional[str] = None) -> str:
        """Generate a comprehensive integrated report combining all analyses.
        
        Args:
            output_dir: Optional directory to save detailed reports
            
        Returns:
            Integrated report as a string
        """
        try:
            report = []
            
            # Add executive summary
            report.append(self.generate_executive_summary())
            
            # Add cost driver analysis section
            report.append("## Cost Driver Analysis")
            try:
                cost_driver_report = self.cost_driver_analyzer.generate_cost_driver_report()
                # Extract just the analysis part (skip the header)
                cost_driver_lines = cost_driver_report.split('\n')
                # Find the start of the actual analysis
                analysis_start = 0
                for i, line in enumerate(cost_driver_lines):
                    if line.startswith("## Absolute Cost Drivers"):
                        analysis_start = i
                        break
                report.extend(cost_driver_lines[analysis_start:])
            except Exception as e:
                report.append(f"Error generating cost driver analysis: {e}")
            report.append("")
            
            # Add DSA analysis section
            report.append("## Deterministic Sensitivity Analysis (DSA)")
            try:
                dsa_report = self.dsa_analyzer.generate_dsa_report()
                # Extract just the analysis part
                dsa_lines = dsa_report.split('\n')
                analysis_start = 0
                for i, line in enumerate(dsa_lines):
                    if line.startswith("## Sensitivity Analysis Results"):
                        analysis_start = i
                        break
                report.extend(dsa_lines[analysis_start:])
            except Exception as e:
                report.append(f"Error generating DSA analysis: {e}")
            report.append("")
            
            # Add PSA analysis section
            report.append("## Probabilistic Sensitivity Analysis (PSA)")
            try:
                psa_report = self.psa_analyzer.generate_psa_report()
                # Extract just the analysis part
                psa_lines = psa_report.split('\n')
                analysis_start = 0
                for i, line in enumerate(psa_lines):
                    if line.startswith("## Simulation Details"):
                        analysis_start = i
                        break
                report.extend(psa_lines[analysis_start:])
            except Exception as e:
                report.append(f"Error generating PSA analysis: {e}")
            report.append("")
            
            # Add VOI analysis section
            report.append("## Value of Information (VOI) Analysis")
            try:
                voi_report = self.voi_analyzer.generate_voi_report()
                # Extract just the analysis part
                voi_lines = voi_report.split('\n')
                analysis_start = 0
                for i, line in enumerate(voi_lines):
                    if line.startswith("## Expected Value of Perfect Information"):
                        analysis_start = i
                        break
                report.extend(voi_lines[analysis_start:])
            except Exception as e:
                report.append(f"Error generating VOI analysis: {e}")
            report.append("")
            
            # Add Budget Impact analysis section
            report.append("## Budget Impact Analysis")
            try:
                budget_report = self.budget_impact_analyzer.generate_budget_impact_report()
                # Extract just the analysis part
                budget_lines = budget_report.split('\n')
                analysis_start = 0
                for i, line in enumerate(budget_lines):
                    if line.startswith("## Volume Sensitivity Analysis"):
                        analysis_start = i
                        break
                report.extend(budget_lines[analysis_start:])
            except Exception as e:
                report.append(f"Error generating Budget Impact analysis: {e}")
            report.append("")
            
            # Add Break-even analysis section
            report.append("## Break-even Analysis")
            try:
                break_even_report = self.break_even_analyzer.generate_break_even_report()
                # Extract just the analysis part
                break_even_lines = break_even_report.split('\n')
                analysis_start = 0
                for i, line in enumerate(break_even_lines):
                    if line.startswith("## Break-even Volume Calculation"):
                        analysis_start = i
                        break
                report.extend(break_even_lines[analysis_start:])
            except Exception as e:
                report.append(f"Error generating Break-even analysis: {e}")
            report.append("")
            
            # Add methodology section
            report.append("## Methodology")
            report.append("All analyses were conducted using a systematic framework that:")
            report.append("- Processes all input data sheets consistently using the DataManager")
            report.append("- Executes Excel formula translations programmatically")
            report.append("- Maintains data integrity through validation checks")
            report.append("- Supports scenario modeling through advanced analytical modules")
            report.append("")
            
            # Add conclusions section
            report.append("## Conclusions")
            report.append("This integrated analysis provides comprehensive insights into:")
            report.append("- Key cost drivers by value and proportion across all models")
            report.append("- Model robustness through deterministic sensitivity analysis")
            report.append("- Uncertainty quantification through probabilistic sensitivity analysis")
            report.append("- Economic value of reducing uncertainty through value of information analysis")
            report.append("- Budget implications of different testing volumes and scenarios")
            report.append("- Volume thresholds for cost recovery and minimum efficient scale")
            report.append("- Informed decision-making for genomics testing implementation")
            report.append("")
            
            report_str = "\n".join(report)
            
            # Save to file if output directory specified
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                # Save main report
                main_report_file = output_path / "comprehensive_analysis_report.md"
                with open(main_report_file, 'w') as f:
                    f.write(report_str)
                
                # Save individual reports
                try:
                    cost_driver_file = output_path / "cost_driver_analysis.md"
                    self.cost_driver_analyzer.generate_cost_driver_report(str(cost_driver_file))
                    
                    break_even_file = output_path / "break_even_analysis.md"
                    self.break_even_analyzer.generate_break_even_report(output_file=str(break_even_file))
                    
                    dsa_file = output_path / "dsa_analysis.md"
                    self.dsa_analyzer.generate_dsa_report(str(dsa_file))
                    
                    psa_file = output_path / "psa_analysis.md"
                    self.psa_analyzer.generate_psa_report(output_file=str(psa_file))
                    
                    voi_file = output_path / "voi_analysis.md"
                    self.voi_analyzer.generate_voi_report(output_file=str(voi_file))
                    
                    budget_file = output_path / "budget_impact_analysis.md"
                    self.budget_impact_analyzer.generate_budget_impact_report(output_file=str(budget_file))
                except Exception as e:
                    self.logger.error(f"Error saving individual reports: {e}")
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating integrated report: {e}")
            raise


def main():
    """Main function for testing the comprehensive reporting."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize reporter
        reporter = ComprehensiveReporter(data_manager)
        
        # Generate report
        report = reporter.generate_integrated_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in comprehensive reporting: {e}")
        raise


if __name__ == "__main__":
    main()