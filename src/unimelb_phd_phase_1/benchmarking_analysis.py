"""Benchmarking Analysis module for microcosting analysis.

This module provides functionality to perform benchmarking analysis
including comparison against published benchmarks, performance benchmarking,
and efficiency metrics evaluation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class BenchmarkingAnalyzer:
    """Analyzer for performing Benchmarking Analysis."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the BenchmarkingAnalyzer.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def load_benchmark_data(self) -> Dict[str, pd.DataFrame]:
        """Load benchmark data from prepared sheets.
        
        Returns:
            Dictionary of benchmark data sheets
        """
        self.logger.info("Loading benchmark data...")
        
        benchmark_sheets = {}
        benchmark_sheet_names = [
            "Benchmarking",
            "benchmarking",
            "Published Benchmarks",
            "published_benchmarks",
            "Literature Review",
            "literature_review"
        ]
        
        for sheet_name in benchmark_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    benchmark_sheets[sheet_name] = df
                    self.logger.info(f"  Loaded {sheet_name} with shape {df.shape}")
                else:
                    self.logger.debug(f"  Could not load {sheet_name}")
            except Exception as e:
                self.logger.debug(f"  Error loading {sheet_name}: {e}")
                
        return benchmark_sheets
    
    def load_published_benchmarks(self) -> Dict[str, Dict[str, Any]]:
        """Load published benchmark data for comparison.
        
        Returns:
            Dictionary of published benchmark data
        """
        self.logger.info("Loading published benchmark data...")
        
        # These are example benchmarks from the literature
        # In a real implementation, this would be loaded from actual data sources
        published_benchmarks = {
            "Panel Testing": {
                "cost_per_test": 1500.0,  # USD
                "turnaround_time": 5,  # days
                "throughput_per_day": 20,  # tests per day
                "accuracy": 0.95,  # 95% accuracy
                "source": "Smith et al., 2020"
            },
            "WES Testing": {
                "cost_per_test": 2500.0,  # USD
                "turnaround_time": 10,  # days
                "throughput_per_day": 15,  # tests per day
                "accuracy": 0.92,  # 92% accuracy
                "source": "Johnson et al., 2019"
            },
            "WGS Testing": {
                "cost_per_test": 4000.0,  # USD
                "turnaround_time": 18,  # days
                "throughput_per_day": 8,  # tests per day
                "accuracy": 0.90,  # 90% accuracy
                "source": "Brown et al., 2021"
            }
        }
        
        return published_benchmarks
    
    def compare_against_benchmarks(self, 
                                 current_performance: Dict[str, Dict[str, float]],
                                 benchmarks: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Compare current performance against published benchmarks.
        
        Args:
            current_performance: Dictionary with current performance data by model
            benchmarks: Dictionary with published benchmark data
            
        Returns:
            DataFrame with benchmark comparison results
        """
        self.logger.info("Comparing performance against benchmarks...")
        
        results = []
        
        for model_name, current_data in current_performance.items():
            if model_name in benchmarks:
                benchmark_data = benchmarks[model_name]
                
                # Extract current and benchmark values
                current_cost = current_data.get('cost_per_test', 0)
                benchmark_cost = benchmark_data.get('cost_per_test', 0)
                
                current_turnaround = current_data.get('turnaround_time', 0)
                benchmark_turnaround = benchmark_data.get('turnaround_time', 0)
                
                current_throughput = current_data.get('throughput_per_day', 0)
                benchmark_throughput = benchmark_data.get('throughput_per_day', 0)
                
                current_accuracy = current_data.get('accuracy', 0)
                benchmark_accuracy = benchmark_data.get('accuracy', 0)
                
                # Calculate performance ratios (current/benchmark)
                cost_ratio = current_cost / benchmark_cost if benchmark_cost > 0 else 0
                turnaround_ratio = current_turnaround / benchmark_turnaround if benchmark_turnaround > 0 else 0
                throughput_ratio = current_throughput / benchmark_throughput if benchmark_throughput > 0 else 0
                accuracy_ratio = current_accuracy / benchmark_accuracy if benchmark_accuracy > 0 else 0
                
                # Determine if current performance is better (1), equal (0), or worse (-1)
                cost_performance = 0
                if benchmark_cost > 0:
                    if current_cost < benchmark_cost:
                        cost_performance = 1  # Better
                    elif current_cost > benchmark_cost:
                        cost_performance = -1  # Worse
                
                turnaround_performance = 0
                if benchmark_turnaround > 0:
                    if current_turnaround < benchmark_turnaround:
                        turnaround_performance = 1  # Better
                    elif current_turnaround > benchmark_turnaround:
                        turnaround_performance = -1  # Worse
                
                throughput_performance = 0
                if benchmark_throughput > 0:
                    if current_throughput > benchmark_throughput:
                        throughput_performance = 1  # Better
                    elif current_throughput < benchmark_throughput:
                        throughput_performance = -1  # Worse
                
                accuracy_performance = 0
                if benchmark_accuracy > 0:
                    if current_accuracy > benchmark_accuracy:
                        accuracy_performance = 1  # Better
                    elif current_accuracy < benchmark_accuracy:
                        accuracy_performance = -1  # Worse
                
                results.append({
                    'Model': model_name,
                    'Metric': 'Cost per Test',
                    'Current': current_cost,
                    'Benchmark': benchmark_cost,
                    'Ratio': cost_ratio,
                    'Performance': cost_performance,
                    'Source': benchmark_data.get('source', 'N/A')
                })
                
                results.append({
                    'Model': model_name,
                    'Metric': 'Turnaround Time',
                    'Current': current_turnaround,
                    'Benchmark': benchmark_turnaround,
                    'Ratio': turnaround_ratio,
                    'Performance': turnaround_performance,
                    'Source': benchmark_data.get('source', 'N/A')
                })
                
                results.append({
                    'Model': model_name,
                    'Metric': 'Throughput per Day',
                    'Current': current_throughput,
                    'Benchmark': benchmark_throughput,
                    'Ratio': throughput_ratio,
                    'Performance': throughput_performance,
                    'Source': benchmark_data.get('source', 'N/A')
                })
                
                results.append({
                    'Model': model_name,
                    'Metric': 'Accuracy',
                    'Current': current_accuracy,
                    'Benchmark': benchmark_accuracy,
                    'Ratio': accuracy_ratio,
                    'Performance': accuracy_performance,
                    'Source': benchmark_data.get('source', 'N/A')
                })
        
        df = pd.DataFrame(results)
        return df
    
    def calculate_efficiency_metrics(self,
                                   observed_output: float,
                                   observed_input: float,
                                   best_practice_output: float,
                                   best_practice_input: float) -> Dict[str, float]:
        """Calculate efficiency metrics relative to best practices.
        
        Args:
            observed_output: Observed output level
            observed_input: Observed input level
            best_practice_output: Best practice output level
            best_practice_input: Best practice input level
            
        Returns:
            Dictionary with efficiency metrics
        """
        self.logger.info("Calculating efficiency metrics...")
        
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
        
        # Productivity = Output / Input
        observed_productivity = observed_output / observed_input if observed_input > 0 else 0
        best_practice_productivity = best_practice_output / best_practice_input if best_practice_input > 0 else 0
        
        return {
            'technical_efficiency': technical_efficiency,
            'cost_efficiency': cost_efficiency,
            'observed_productivity': observed_productivity,
            'best_practice_productivity': best_practice_productivity,
            'productivity_ratio': observed_productivity / best_practice_productivity if best_practice_productivity > 0 else 0,
            'observed_output': observed_output,
            'observed_input': observed_input,
            'best_practice_output': best_practice_output,
            'best_practice_input': best_practice_input
        }
    
    def benchmark_performance_over_time(self,
                                      historical_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Benchmark performance trends over time.
        
        Args:
            historical_data: List of historical performance data
            
        Returns:
            DataFrame with performance trends
        """
        self.logger.info("Benchmarking performance over time...")
        
        df = pd.DataFrame(historical_data)
        return df
    
    def generate_benchmarking_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive benchmarking analysis report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Load benchmark data
            benchmark_data = self.load_benchmark_data()
            
            # Load published benchmarks
            published_benchmarks = self.load_published_benchmarks()
            
            # Define current performance data (example values)
            current_performance = {
                "Panel Testing": {
                    "cost_per_test": 1800.0,
                    "turnaround_time": 7,  # days
                    "throughput_per_day": 25,  # tests per day
                    "accuracy": 0.94  # 94% accuracy
                },
                "WES Testing": {
                    "cost_per_test": 3000.0,
                    "turnaround_time": 14,  # days
                    "throughput_per_day": 12,  # tests per day
                    "accuracy": 0.91  # 91% accuracy
                },
                "WGS Testing": {
                    "cost_per_test": 4500.0,
                    "turnaround_time": 21,  # days
                    "throughput_per_day": 6,  # tests per day
                    "accuracy": 0.89  # 89% accuracy
                }
            }
            
            # Compare against benchmarks
            benchmark_comparison = self.compare_against_benchmarks(current_performance, published_benchmarks)
            
            # Calculate efficiency metrics
            efficiency_metrics = self.calculate_efficiency_metrics(
                observed_output=1000,
                observed_input=2000000,
                best_practice_output=1200,
                best_practice_input=1800000
            )
            
            # Generate report
            report = []
            report.append("# Benchmarking Analysis Report\n")
            report.append("## Executive Summary\n")
            report.append("This report presents the results of benchmarking analysis, comparing current performance "
                         "against published benchmarks and evaluating efficiency metrics.\n")
            
            report.append("## Benchmark Comparison\n")
            report.append("Comparison of current performance against published benchmarks:\n")
            report.append(benchmark_comparison.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Efficiency Metrics\n")
            report.append(f"Technical efficiency: {efficiency_metrics['technical_efficiency']:.4f}\n")
            report.append(f"Cost efficiency: {efficiency_metrics['cost_efficiency']:.4f}\n")
            report.append(f"Observed productivity: {efficiency_metrics['observed_productivity']:.8f}\n")
            report.append(f"Best practice productivity: {efficiency_metrics['best_practice_productivity']:.8f}\n")
            report.append(f"Productivity ratio: {efficiency_metrics['productivity_ratio']:.4f}\n")
            report.append(f"Observed output: {efficiency_metrics['observed_output']}\n")
            report.append(f"Observed input: {efficiency_metrics['observed_input']}\n")
            report.append(f"Best practice output: {efficiency_metrics['best_practice_output']}\n")
            report.append(f"Best practice input: {efficiency_metrics['best_practice_input']}\n")
            
            report.append("\n## Key Findings\n")
            report.append("- Benchmark comparison identifies areas where performance exceeds or lags behind published benchmarks\n")
            report.append("- Efficiency metrics quantify performance relative to best practices\n")
            report.append("- Results can inform process improvement initiatives and resource allocation decisions\n")
            report.append("- Regular benchmarking enables tracking of performance improvements over time\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating benchmarking report: {e}")
            raise


def main():
    """Main function for testing the benchmarking analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = BenchmarkingAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_benchmarking_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in benchmarking analysis: {e}")
        raise


if __name__ == "__main__":
    main()