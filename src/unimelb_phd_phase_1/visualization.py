"""Visualization tools for microcosting analysis."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pathlib import Path
import numpy as np


def load_prepared_data(data_dir=None):
    """Load prepared data from the data directory.
    
    Args:
        data_dir (str or Path, optional): Path to the data directory. 
            If None, uses the default data/prepared directory.
            
    Returns:
        dict: Dictionary of loaded DataFrames with keys as table names.
    """
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[2] / "data" / "prepared"
    else:
        data_dir = Path(data_dir)
        
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
    data_files = list(data_dir.glob("*.parquet"))
    data = {}
    
    for file_path in data_files:
        table_name = file_path.stem
        try:
            data[table_name] = pd.read_parquet(file_path)
        except Exception as e:
            print(f"Warning: Could not load {file_path}: {e}")
            
    return data


def plot_cost_distribution(data, column_name, title="Cost Distribution", figsize=(10, 6)):
    """Plot the distribution of costs from a specified column.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        column_name (str): Name of the column to plot.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    if column_name not in data.columns:
        raise ValueError(f"Column '{column_name}' not found in data")
        
    fig, ax = plt.subplots(figsize=figsize)
    
    # Remove NaN values
    values = data[column_name].dropna()
    
    # Plot histogram
    ax.hist(values, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    ax.set_xlabel(column_name)
    ax.set_ylabel('Frequency')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    
    return fig


def plot_category_costs(data, category_column, cost_column, title="Costs by Category", figsize=(12, 8)):
    """Plot total costs by category.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to sum.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    if category_column not in data.columns:
        raise ValueError(f"Column '{category_column}' not found in data")
    if cost_column not in data.columns:
        raise ValueError(f"Column '{cost_column}' not found in data")
        
    # Group by category and sum costs
    category_costs = data.groupby(category_column)[cost_column].sum().sort_values(ascending=False)
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create bar plot
    bars = ax.bar(range(len(category_costs)), category_costs.values, color='lightcoral')
    ax.set_xlabel(category_column)
    ax.set_ylabel(f'Total {cost_column}')
    ax.set_title(title)
    ax.set_xticks(range(len(category_costs)))
    ax.set_xticklabels(category_costs.index, rotation=45, ha='right')
    ax.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, category_costs.values)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + value*0.01,
                f'{value:.2f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    return fig


def plot_cost_breakdown(data, category_column, cost_columns, title="Cost Breakdown by Category", figsize=(12, 8)):
    """Plot cost breakdown by category for multiple cost columns.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_columns (list): List of cost column names to include.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    if category_column not in data.columns:
        raise ValueError(f"Column '{category_column}' not found in data")
        
    for col in cost_columns:
        if col not in data.columns:
            raise ValueError(f"Column '{col}' not found in data")
            
    # Group by category and sum costs for each column
    grouped_data = data.groupby(category_column)[cost_columns].sum()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create stacked bar plot
    grouped_data.plot(kind='bar', stacked=True, ax=ax)
    ax.set_xlabel(category_column)
    ax.set_ylabel('Total Cost')
    ax.set_title(title)
    ax.legend(title='Cost Components')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    return fig


def plot_top_costs(data, cost_column, top_n=10, title="Top Costs", figsize=(10, 6)):
    """Plot the top N costs.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        cost_column (str): Name of the cost column.
        top_n (int): Number of top costs to display.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    if cost_column not in data.columns:
        raise ValueError(f"Column '{cost_column}' not found in data")
        
    # Sort by cost and take top N
    top_costs = data.nlargest(top_n, cost_column)
    
    # If there's a descriptive column, use it for labels
    label_column = None
    for col in ['Step', 'Test', 'Category', 'Sub-Category']:
        if col in data.columns:
            label_column = col
            break
            
    if label_column is None:
        labels = [f'Item {i+1}' for i in range(len(top_costs))]
    else:
        labels = top_costs[label_column].fillna('Unknown')
        
    fig, ax = plt.subplots(figsize=figsize)
    
    bars = ax.bar(range(len(top_costs)), top_costs[cost_column], color='gold')
    ax.set_xlabel('Items')
    ax.set_ylabel(cost_column)
    ax.set_title(title)
    ax.set_xticks(range(len(top_costs)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, top_costs[cost_column])):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + value*0.01,
                f'{value:.2f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    return fig


def create_summary_dashboard(data_dir=None, output_dir=None):
    """Create a summary dashboard with common visualizations.
    
    Args:
        data_dir (str or Path, optional): Path to the data directory.
        output_dir (str or Path, optional): Path to save plots. If None, shows plots.
        
    Returns:
        list: List of generated figure objects.
    """
    # Load data
    data_dict = load_prepared_data(data_dir)
    
    if 'detailed_table' not in data_dict:
        raise ValueError("Detailed table not found in prepared data")
        
    detailed_data = data_dict['detailed_table']
    
    # Find cost columns (those with 'Unit Cost' or 'Price' in the name)
    cost_columns = [col for col in detailed_data.columns if 'Unit Cost' in col or 'Price' in col]
    if not cost_columns:
        # Try to find any numeric columns
        numeric_columns = detailed_data.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_columns:
            cost_columns = [numeric_columns[0]]  # Use the first numeric column
    
    figures = []
    
    # Plot 1: Distribution of a cost column (if available)
    if cost_columns:
        try:
            fig = plot_cost_distribution(detailed_data, cost_columns[0], 
                                       f"Distribution of {cost_columns[0]}")
            figures.append(fig)
            if output_dir:
                fig.savefig(Path(output_dir) / f"cost_distribution_{cost_columns[0]}.png", 
                           bbox_inches='tight', dpi=300)
                plt.close(fig)
        except Exception as e:
            print(f"Warning: Could not create cost distribution plot: {e}")
    
    # Plot 2: Costs by category (if category column exists)
    category_columns = [col for col in detailed_data.columns if 'Category' in col]
    if category_columns and cost_columns:
        try:
            fig = plot_category_costs(detailed_data, category_columns[0], cost_columns[0],
                                    f"Total {cost_columns[0]} by {category_columns[0]}")
            figures.append(fig)
            if output_dir:
                fig.savefig(Path(output_dir) / f"costs_by_{category_columns[0]}.png", 
                           bbox_inches='tight', dpi=300)
                plt.close(fig)
        except Exception as e:
            print(f"Warning: Could not create category costs plot: {e}")
    
    # Plot 3: Top costs
    if cost_columns:
        try:
            fig = plot_top_costs(detailed_data, cost_columns[0], top_n=15,
                               title=f"Top 15 {cost_columns[0]}")
            figures.append(fig)
            if output_dir:
                fig.savefig(Path(output_dir) / f"top_{cost_columns[0]}.png", 
                           bbox_inches='tight', dpi=300)
                plt.close(fig)
        except Exception as e:
            print(f"Warning: Could not create top costs plot: {e}")
    
    if not output_dir:
        # Show all plots if not saving to files
        plt.show()
        
    return figures


# Example usage function
def example_usage():
    """Example of how to use the visualization functions."""
    print("Loading data...")
    data_dict = load_prepared_data()
    
    if 'detailed_table' in data_dict:
        detailed_data = data_dict['detailed_table']
        print(f"Loaded detailed table with {len(detailed_data)} rows")
        
        # Find cost columns
        cost_columns = [col for col in detailed_data.columns if 'Unit Cost' in col or 'Price' in col]
        category_columns = [col for col in detailed_data.columns if 'Category' in col]
        
        print(f"Found cost columns: {cost_columns}")
        print(f"Found category columns: {category_columns}")
        
        # Create a simple plot if we have data
        if cost_columns:
            try:
                fig = plot_cost_distribution(detailed_data, cost_columns[0])
                plt.show()
            except Exception as e:
                print(f"Could not create plot: {e}")
    else:
        print("Detailed table not found in prepared data")


if __name__ == "__main__":
    example_usage()