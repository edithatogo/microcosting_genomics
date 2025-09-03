"""Sample enhanced cost analysis plugin."""

import pandas as pd
from typing import Any, Dict
from unimelb_phd_phase_1.plugin_system import AnalysisPlugin


class SampleCostAnalysisPlugin(AnalysisPlugin):
    """Sample plugin for cost analysis functionality."""
    
    def __init__(self):
        super().__init__(
            name="sample_cost_analysis",
            version="1.0.0",
            description="Sample cost analysis plugin for demonstration"
        )
    
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Perform sample cost analysis.
        
        Args:
            data (Any): Input data
            **kwargs: Additional analysis parameters
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        # Handle different data types
        if isinstance(data, pd.DataFrame):
            result = {
                "data_type": "DataFrame",
                "rows": len(data),
                "columns": len(data.columns),
                "numeric_columns": len(data.select_dtypes(include=['number']).columns)
            }
        elif isinstance(data, dict):
            result = {
                "data_type": "Dictionary",
                "keys": list(data.keys()),
                "size": len(data)
            }
        else:
            result = {
                "data_type": type(data).__name__,
                "size": len(str(data)) if hasattr(data, '__len__') else "N/A",
                "content_preview": str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
            }
        
        # Add any additional parameters
        result.update(kwargs)
        return result