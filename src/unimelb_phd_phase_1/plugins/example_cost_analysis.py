"""Example cost analysis plugin."""

import pandas as pd
from typing import Any, Dict
from unimelb_phd_phase_1.plugin_system import AnalysisPlugin


class CostAnalysisPlugin(AnalysisPlugin):
    """Plugin for cost analysis functionality."""
    
    def __init__(self):
        super().__init__(
            name="cost_analysis",
            version="1.0.0",
            description="Cost analysis plugin for microcosting data"
        )
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform cost analysis on microcosting data.
        
        Args:
            data (pd.DataFrame): Microcosting data
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Data must be a pandas DataFrame")
        
        # Perform basic cost analysis
        results = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "numeric_columns": len(data.select_dtypes(include=['number']).columns),
            "memory_usage_mb": data.memory_usage(deep=True).sum() / 1024 / 1024
        }
        
        # If there are numeric columns, calculate basic statistics
        numeric_data = data.select_dtypes(include=['number'])
        if not numeric_data.empty:
            results["cost_statistics"] = {
                "mean_cost": numeric_data.mean().to_dict(),
                "median_cost": numeric_data.median().to_dict(),
                "std_cost": numeric_data.std().to_dict()
            }
        
        return results