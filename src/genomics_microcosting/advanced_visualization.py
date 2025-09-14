"""Advanced visualization tools for microcosting analysis with interactive features."""

# Handle matplotlib import for Python 3.13 compatibility
try:
    import matplotlib
    matplotlib.use('Agg')  # Set non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except (ImportError, AttributeError):
    HAS_MATPLOTLIB = False
    plt = None

import seaborn as sns
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo


def plot_interactive_cost_distribution(data, column_name, title="Cost Distribution"):
    """Create an interactive histogram of cost distribution.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        column_name (str): Name of the column to plot.
        title (str): Title for the plot.
        
    Returns:
        plotly.graph_objects.Figure: The generated interactive figure.
    """
    if column_name not in data.columns:
        raise ValueError(f"Column '{column_name}' not found in data")
        
    # Remove NaN values
    values = data[column_name].dropna()
    
    # Create interactive histogram
    fig = px.histogram(
        x=values,
        nbins=50,
        title=title,
        labels={'x': column_name, 'y': 'Frequency'},
        color_discrete_sequence=['skyblue']
    )
    
    fig.update_layout(
        xaxis_title=column_name,
        yaxis_title="Frequency",
        showlegend=False
    )
    
    return fig


def plot_interactive_category_costs(data, category_column, cost_column, title="Costs by Category"):
    """Create an interactive bar chart of costs by category.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to sum.
        title (str): Title for the plot.
        
    Returns:
        plotly.graph_objects.Figure: The generated interactive figure.
    """
    if category_column not in data.columns:
        raise ValueError(f"Column '{category_column}' not found in data")
    if cost_column not in data.columns:
        raise ValueError(f"Column '{cost_column}' not found in data")
        
    # Group by category and sum costs
    category_costs = data.groupby(category_column)[cost_column].sum().sort_values(ascending=False).reset_index()
    
    # Create interactive bar chart
    fig = px.bar(
        category_costs,
        x=category_column,
        y=cost_column,
        title=title,
        color_discrete_sequence=['lightcoral']
    )
    
    fig.update_layout(
        xaxis_title=category_column,
        yaxis_title=f'Total {cost_column}',
        xaxis_tickangle=-45
    )
    
    return fig


def plot_cost_trend_analysis(data, category_column, cost_column, title="Cost Trend Analysis"):
    """Create a trend analysis plot showing cost distribution across categories.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to analyze.
        title (str): Title for the plot.
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    if category_column not in data.columns:
        raise ValueError(f"Column '{category_column}' not found in data")
    if cost_column not in data.columns:
        raise ValueError(f"Column '{cost_column}' not found in data")
    
    # Group by category and calculate statistics
    grouped = data.groupby(category_column)[cost_column].agg(['count', 'mean', 'std', 'min', 'max']).reset_index()
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create bar plot with error bars
    bars = ax.bar(range(len(grouped)), grouped['mean'], 
                  yerr=grouped['std'], capsize=5, alpha=0.7, color='lightgreen', edgecolor='black')
    
    ax.set_xlabel(category_column)
    ax.set_ylabel(f'Average {cost_column}')
    ax.set_title(title)
    ax.set_xticks(range(len(grouped)))
    ax.set_xticklabels(grouped[category_column], rotation=45, ha='right')
    ax.grid(True, alpha=0.3)
    
    # Add count labels
    for i, (bar, count) in enumerate(zip(bars, grouped['count'])):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + bar.get_yerr()[1] + 
                (grouped['max'].max() * 0.01),
                f'n={count}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    return fig


def plot_cost_correlation_matrix(data, cost_columns, title="Cost Correlation Matrix"):
    """Create a correlation matrix heatmap for cost columns.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        cost_columns (list): List of cost column names to include.
        title (str): Title for the plot.
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    for col in cost_columns:
        if col not in data.columns:
            raise ValueError(f"Column '{col}' not found in data")
    
    # Calculate correlation matrix
    corr_matrix = data[cost_columns].corr()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create heatmap
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                square=True, linewidths=0.5, ax=ax)
    
    ax.set_title(title)
    plt.tight_layout()
    return fig


def plot_interactive_cost_scatter(data, x_column, y_column, category_column=None, title="Cost Scatter Plot"):
    """Create an interactive scatter plot of costs.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        x_column (str): Name of the column for x-axis.
        y_column (str): Name of the column for y-axis.
        category_column (str, optional): Name of the column for coloring points.
        title (str): Title for the plot.
        
    Returns:
        plotly.graph_objects.Figure: The generated interactive figure.
    """
    if x_column not in data.columns:
        raise ValueError(f"Column '{x_column}' not found in data")
    if y_column not in data.columns:
        raise ValueError(f"Column '{y_column}' not found in data")
        
    # Remove rows with NaN values in either column
    clean_data = data[[x_column, y_column]].dropna()
    
    if category_column and category_column in data.columns:
        clean_data[category_column] = data[category_column].dropna()
        fig = px.scatter(
            clean_data,
            x=x_column,
            y=y_column,
            color=category_column,
            title=title
        )
    else:
        fig = px.scatter(
            clean_data,
            x=x_column,
            y=y_column,
            title=title
        )
    
    fig.update_layout(
        xaxis_title=x_column,
        yaxis_title=y_column
    )
    
    return fig


def plot_cost_boxplot(data, category_column, cost_column, title="Cost Distribution by Category"):
    """Create a boxplot showing cost distribution across categories.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to analyze.
        title (str): Title for the plot.
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    if category_column not in data.columns:
        raise ValueError(f"Column '{category_column}' not found in data")
    if cost_column not in data.columns:
        raise ValueError(f"Column '{cost_column}' not found in data")
    
    # Remove rows with NaN values
    clean_data = data[[category_column, cost_column]].dropna()
    
    # Get unique categories
    unique_categories = clean_data[category_column].unique()
    
    # Filter out categories with no data
    boxplot_data = []
    boxplot_labels = []
    for cat in unique_categories:
        cat_data = clean_data[clean_data[category_column] == cat][cost_column]
        if len(cat_data) > 0:  # Only include categories with data
            boxplot_data.append(cat_data)
            boxplot_labels.append(cat)
    
    # Check if we have data to plot
    if not boxplot_data:
        raise ValueError("No valid data to plot")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create boxplot
    bp = ax.boxplot(boxplot_data, labels=boxplot_labels, patch_artist=True)
    
    # Color the boxes
    colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']
    for patch, color in zip(bp['boxes'], colors * (len(bp['boxes']) // len(colors) + 1)):
        patch.set_facecolor(color)
    
    ax.set_xlabel(category_column)
    ax.set_ylabel(cost_column)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return fig


def create_interactive_dashboard(data_dict):
    """Create an interactive dashboard with multiple visualizations.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys.
        
    Returns:
        plotly.graph_objects.Figure: The generated interactive dashboard.
    """
    if 'detailed_table' not in data_dict:
        raise ValueError("Detailed table not found in prepared data")
        
    detailed_data = data_dict['detailed_table']
    
    # Find cost columns
    cost_columns = [col for col in detailed_data.columns if 'unit_cost' in col or 'price' in col]
    category_columns = [col for col in detailed_data.columns if 'Category' in col]
    
    if not cost_columns or not category_columns:
        # Try to find any numeric and categorical columns
        numeric_columns = detailed_data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = detailed_data.select_dtypes(include=['object']).columns.tolist()
        
        if not cost_columns and numeric_columns:
            cost_columns = [numeric_columns[0]]
        if not category_columns and categorical_columns:
            category_columns = [categorical_columns[0]]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Cost Distribution', 'Costs by Category', 
                       'Top Costs', 'Cost Scatter Plot'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Add plots if we have the required data
    if cost_columns:
        # Cost distribution (simplified for subplot)
        values = detailed_data[cost_columns[0]].dropna()
        fig.add_trace(
            go.Histogram(x=values[:1000], name=f'Distribution of {cost_columns[0]}'), 
            row=1, col=1
        )
        
        # Top costs
        top_costs = detailed_data.nlargest(20, cost_columns[0])
        fig.add_trace(
            go.Bar(x=list(range(len(top_costs))), y=top_costs[cost_columns[0]], 
                   name=f'Top 20 {cost_columns[0]}'),
            row=2, col=1
        )
    
    if category_columns and cost_columns:
        # Costs by category
        category_costs = detailed_data.groupby(category_columns[0])[cost_columns[0]].sum().sort_values(ascending=False)
        fig.add_trace(
            go.Bar(x=category_costs.index[:15], y=category_costs.values[:15], 
                   name=f'Total {cost_columns[0]} by {category_columns[0]}'),
            row=1, col=2
        )
        
        # Scatter plot (if we have two numeric columns)
        if len(cost_columns) >= 2:
            clean_data = detailed_data[[cost_columns[0], cost_columns[1]]].dropna()
            fig.add_trace(
                go.Scatter(x=clean_data[cost_columns[0]][:500], 
                          y=clean_data[cost_columns[1]][:500],
                          mode='markers',
                          name=f'{cost_columns[0]} vs {cost_columns[1]}'),
                row=2, col=2
            )
    
    fig.update_layout(
        title_text="Interactive Microcosting Analysis Dashboard",
        showlegend=False,
        height=800
    )
    
    return fig


def save_interactive_plot(fig, output_file):
    """Save an interactive plot as HTML.
    
    Args:
        fig (plotly.graph_objects.Figure): The figure to save.
        output_file (str or Path): Path to output HTML file.
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    pyo.plot(fig, filename=str(output_file), auto_open=False)


def create_comprehensive_visualization_report(data_dict, output_dir):
    """Create a comprehensive visualization report with multiple chart types.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys.
        output_dir (str or Path): Directory to save plots.
        
    Returns:
        list: List of generated figure filenames.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    figures = []
    
    if 'detailed_table' not in data_dict:
        print("Warning: detailed_table not found in data. Skipping detailed plots.")
        return figures
    
    detailed_data = data_dict['detailed_table']
    
    # Find cost columns
    cost_columns = [col for col in detailed_data.columns if 'unit_cost' in col or 'price' in col]
    category_columns = [col for col in detailed_data.columns if 'Category' in col]
    
    if not cost_columns:
        # Try to find any numeric columns
        numeric_columns = detailed_data.select_dtypes(include=['number']).columns.tolist()
        if numeric_columns:
            cost_columns = [numeric_columns[0]]
    
    # Create enhanced plots
    try:
        # 1. Cost trend analysis
        if category_columns and cost_columns:
            fig = plot_cost_trend_analysis(detailed_data, category_columns[0], cost_columns[0],
                                         f"Cost Trend Analysis: {cost_columns[0]} by {category_columns[0]}")
            fig_file = output_dir / f"cost_trend_analysis_{category_columns[0]}.png"
            fig.savefig(fig_file, bbox_inches='tight', dpi=300)
            plt.close(fig)
            figures.append(str(fig_file.name))
        
        # 2. Cost correlation matrix (if we have multiple cost columns)
        if len(cost_columns) > 1:
            fig = plot_cost_correlation_matrix(detailed_data, cost_columns[:5],
                                             "Cost Correlation Matrix (Top 5 Cost Columns)")
            fig_file = output_dir / "cost_correlation_matrix.png"
            fig.savefig(fig_file, bbox_inches='tight', dpi=300)
            plt.close(fig)
            figures.append(str(fig_file.name))
        
        # 3. Cost boxplot
        if category_columns and cost_columns:
            try:
                fig = plot_cost_boxplot(detailed_data, category_columns[0], cost_columns[0],
                                      f"Cost Distribution by {category_columns[0]}")
                fig_file = output_dir / f"cost_boxplot_{category_columns[0]}.png"
                fig.savefig(fig_file, bbox_inches='tight', dpi=300)
                plt.close(fig)
                figures.append(str(fig_file.name))
            except Exception as e:
                print(f"Warning: Could not create boxplot: {e}")
        
        # 4. Interactive visualizations
        if cost_columns:
            # Interactive cost distribution
            fig = plot_interactive_cost_distribution(detailed_data, cost_columns[0],
                                                   f"Interactive Distribution of {cost_columns[0]}")
            # Sanitize filename
            sanitized_col_name = "".join(c for c in cost_columns[0] if c.isalnum() or c in (" ", "-", "_")).rstrip()
            sanitized_col_name = sanitized_col_name.replace(" ", "_").replace("/", "_per_")
            html_file = output_dir / f"interactive_cost_distribution_{sanitized_col_name}.html"
            save_interactive_plot(fig, html_file)
            figures.append(str(html_file.name))
        
        if category_columns and cost_columns:
            # Interactive category costs
            fig = plot_interactive_category_costs(detailed_data, category_columns[0], cost_columns[0],
                                                f"Interactive Costs by {category_columns[0]}")
            # Sanitize filename
            sanitized_cat_name = "".join(c for c in category_columns[0] if c.isalnum() or c in (" ", "-", "_")).rstrip()
            sanitized_cat_name = sanitized_cat_name.replace(" ", "_").replace("/", "_per_")
            html_file = output_dir / f"interactive_category_costs_{sanitized_cat_name}.html"
            save_interactive_plot(fig, html_file)
            figures.append(str(html_file.name))
            
            # Interactive scatter plot (if we have two numeric columns)
            if len(cost_columns) >= 2:
                fig = plot_interactive_cost_scatter(detailed_data, cost_columns[0], cost_columns[1],
                                                  category_columns[0] if category_columns else None,
                                                  f"Interactive Scatter: {cost_columns[0]} vs {cost_columns[1]}")
                # Sanitize filenames
                sanitized_col1_name = "".join(c for c in cost_columns[0] if c.isalnum() or c in (" ", "-", "_")).rstrip()
                sanitized_col1_name = sanitized_col1_name.replace(" ", "_").replace("/", "_per_")
                sanitized_col2_name = "".join(c for c in cost_columns[1] if c.isalnum() or c in (" ", "-", "_")).rstrip()
                sanitized_col2_name = sanitized_col2_name.replace(" ", "_").replace("/", "_per_")
                html_file = output_dir / f"interactive_cost_scatter_{sanitized_col1_name}_vs_{sanitized_col2_name}.html"
                save_interactive_plot(fig, html_file)
                figures.append(str(html_file.name))
        
        # 5. Interactive dashboard
        fig = create_interactive_dashboard(data_dict)
        html_file = output_dir / "interactive_dashboard.html"
        save_interactive_plot(fig, html_file)
        figures.append(str(html_file.name))
        
    except Exception as e:
        print(f"Warning: Error creating enhanced visualizations: {e}")
        import traceback
        traceback.print_exc()
    
    return figures


# Example usage function
def example_usage():
    """Example of how to use the advanced visualization functions."""
    from .visualization import load_prepared_data
    
    print("Loading data...")
    data_dict = load_prepared_data()
    
    if 'detailed_table' in data_dict:
        detailed_data = data_dict['detailed_table']
        print(f"Loaded detailed table with {len(detailed_data)} rows")
        
        # Find cost columns
        cost_columns = [col for col in detailed_data.columns if 'unit_cost' in col or 'price' in col]
        category_columns = [col for col in detailed_data.columns if 'Category' in col]
        
        print(f"Found cost columns: {cost_columns}")
        print(f"Found category columns: {category_columns}")
        
        # Create an interactive plot if we have data
        if cost_columns:
            try:
                fig = plot_interactive_cost_distribution(detailed_data, cost_columns[0])
                fig.show()
            except Exception as e:
                print(f"Could not create interactive plot: {e}")
    else:
        print("Detailed table not found in prepared data")


if __name__ == "__main__":
    example_usage()