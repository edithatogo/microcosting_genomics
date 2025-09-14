"""Web-based visualization utilities for the microcosting analysis web interface."""

import base64
import io
from pathlib import Path
import sys

import matplotlib.pyplot as plt

# Add the src directory to the path
src_path = Path(__file__).resolve().parent
sys.path.insert(0, str(src_path))

from .visualization import (  # noqa: E402
    plot_cost_distribution, 
    plot_category_costs, 
    plot_top_costs
)


def create_plot_base64(plot_function, *args, **kwargs):
    """Create a plot and return it as a base64 encoded string.
    
    Args:
        plot_function: Function that creates a matplotlib plot
        *args: Arguments to pass to the plot function
        **kwargs: Keyword arguments to pass to the plot function
        
    Returns:
        str: Base64 encoded PNG image
    """
    # Create the plot
    fig = plot_function(*args, **kwargs)
    
    # Save to a bytes buffer
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    
    # Convert to base64
    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    # Close the figure to free memory
    plt.close(fig)
    
    return img_base64


def generate_visualization(data, viz_type, column_name=None, category_column=None):
    """Generate a visualization based on the specified type.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data
        viz_type (str): Type of visualization ("distribution", "category", "top")
        column_name (str, optional): Column to visualize
        category_column (str, optional): Category column for grouped visualizations
        
    Returns:
        str: Base64 encoded PNG image
    """
    # Find appropriate columns if not specified
    if column_name is None:
        # Find numeric columns
        numeric_columns = data.select_dtypes(include=["number"]).columns.tolist()
        if not numeric_columns:
            raise ValueError("No numeric columns found in data")
        column_name = numeric_columns[0]
    
    if viz_type == "distribution":
        return create_plot_base64(plot_cost_distribution, data, column_name)
    elif viz_type == "category":
        if category_column is None:
            # Find category columns
            category_columns = [col for col in data.columns if "Category" in col or "category" in col.lower()]
            if not category_columns:
                raise ValueError("No category columns found in data")
            category_column = category_columns[0]
        return create_plot_base64(plot_category_costs, data, category_column, column_name)
    elif viz_type == "top":
        return create_plot_base64(plot_top_costs, data, column_name)
    else:
        raise ValueError(f"Unknown visualization type: {viz_type}")


def get_available_columns(data):
    """Get lists of available columns for visualization.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data
        
    Returns:
        dict: Dictionary with lists of numeric and category columns
    """
    numeric_columns = data.select_dtypes(include=["number"]).columns.tolist()
    category_columns = [col for col in data.columns if "Category" in col or "category" in col.lower()]
    
    # If no explicit category columns found, look for likely candidates
    if not category_columns:
        category_columns = [col for col in data.columns 
                          if data[col].dtype == "object" and 
                          data[col].nunique() < len(data) * 0.5]  # Less than 50% unique values
    
    return {
        "numeric": numeric_columns[:20],  # Limit to first 20
        "category": category_columns[:10]  # Limit to first 10
    }

