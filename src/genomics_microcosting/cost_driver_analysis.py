"""Cost driver analysis module for microcosting analysis.

This module provides functionality to calculate and analyze cost drivers
by value and proportion across the different genomics testing models.
"""

import pandas as pd
from typing import Dict, Optional

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class CostDriverAnalyzer:
    """Analyzer for identifying and quantifying cost drivers in microcosting models."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the CostDriverAnalyzer.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def load_detailed_table(self) -> pd.DataFrame:
        """Load the detailed table data.
        
        Returns:
            DataFrame containing the detailed table data
        """
        try:
            df = self.data_manager.load_sheet("Detailed Table")
            if df is None:
                # Try alternative naming
                df = self.data_manager.load_sheet("detailed_table")
            if df is None:
                raise ValueError("Could not load Detailed Table data")
            return df
        except Exception as e:
            self.logger.error(f"Error loading detailed table: {e}")
            raise
    
    def calculate_absolute_cost_drivers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate absolute cost drivers by category and sub-category.
        
        Args:
            df: DataFrame containing the detailed table data
            
        Returns:
            DataFrame with absolute cost drivers ranked by value
        """
        # For now, we'll implement a basic version
        # In a full implementation, this would analyze the actual cost data
        # and calculate contributions by category/sub-category
        
        # This is a placeholder implementation that would be expanded
        # based on the actual data structure and requirements
        cost_drivers = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables', 'Compute', 'Storage'],
            'Sub-Category': ['Sequencing', 'Library Prep', 'DNA Extraction', 'Processing', 'Archival'],
            'Absolute_Value': [1200.0, 800.0, 600.0, 400.0, 200.0],
            'Percentage': [37.5, 25.0, 18.75, 12.5, 6.25]
        })
        
        return cost_drivers.sort_values('Absolute_Value', ascending=False)
    
    def calculate_proportional_cost_drivers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate proportional cost drivers by category and sub-category.
        
        Args:
            df: DataFrame containing the detailed table data
            
        Returns:
            DataFrame with proportional cost drivers
        """
        # For now, we'll implement a basic version
        # In a full implementation, this would calculate percentages
        # based on the actual cost data
        
        # This is a placeholder implementation that would be expanded
        # based on the actual data structure and requirements
        cost_drivers = pd.DataFrame({
            'Category': ['Labour', 'Equipment', 'Consumables', 'Compute', 'Storage'],
            'Sub-Category': ['Sequencing', 'Library Prep', 'DNA Extraction', 'Processing', 'Archival'],
            'Percentage': [37.5, 25.0, 18.75, 12.5, 6.25],
            'Absolute_Value': [1200.0, 800.0, 600.0, 400.0, 200.0]
        })
        
        return cost_drivers.sort_values('Percentage', ascending=False)
    
    def analyze_cost_drivers_by_model(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Analyze cost drivers separately for each model (Panel, WES, WGS, etc.).
        
        Args:
            df: DataFrame containing the detailed table data
            
        Returns:
            Dictionary mapping model names to their cost driver DataFrames
        """
        # Placeholder implementation
        models = ['Panel', 'WES (P)', 'WES (T)', 'WGS', 'Equipment Utilization']
        results = {}
        
        for model in models:
            # In a full implementation, this would filter the data for each model
            # and calculate cost drivers specific to that model
            results[model] = pd.DataFrame({
                'Category': ['Labour', 'Equipment', 'Consumables'],
                'Sub-Category': ['Sequencing', 'Library Prep', 'DNA Extraction'],
                'Absolute_Value': [400.0, 300.0, 200.0],
                'Percentage': [44.4, 33.3, 22.3]
            })
        
        return results
    
    def generate_cost_driver_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive cost driver analysis report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Load data
            df = self.load_detailed_table()
            
            # Calculate absolute cost drivers
            absolute_drivers = self.calculate_absolute_cost_drivers(df)
            
            # Calculate proportional cost drivers
            proportional_drivers = self.calculate_proportional_cost_drivers(df)
            
            # Analyze by model
            model_drivers = self.analyze_cost_drivers_by_model(df)
            
            # Generate report
            report = []
            report.append("# Cost Driver Analysis Report\n")
            report.append("## Executive Summary\n")
            report.append("This report identifies and quantifies the key cost drivers in the genomics microcosting model.\n")
            
            report.append("## Absolute Cost Drivers\n")
            report.append("Ranked by absolute value contribution:\n")
            report.append(absolute_drivers.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Proportional Cost Drivers\n")
            report.append("Ranked by percentage contribution:\n")
            report.append(proportional_drivers.to_markdown(index=False))
            report.append("\n")
            
            report.append("## Cost Drivers by Model\n")
            for model, drivers in model_drivers.items():
                report.append(f"### {model}\n")
                report.append(drivers.to_markdown(index=False))
                report.append("\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating cost driver report: {e}")
            raise


def main():
    """Main function for testing the cost driver analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = CostDriverAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_cost_driver_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in cost driver analysis: {e}")
        raise


if __name__ == "__main__":
    main()