# API Reference

This document provides detailed API documentation for all modules in the microcosting genomics analysis toolkit.

## Core Modules

### calculation_engine.py

Main calculation engine for processing Excel formulas.

#### CalculationEngine
```python
class CalculationEngine:
    def __init__(self, sheet_manager, verbose=False):
        """Initialize the calculation engine.
        
        Args:
            sheet_manager (SheetManager): Sheet manager instance for data access
            verbose (bool): Enable verbose logging
        """
        pass
    
    def get_cell_value(self, sheet_name, cell_ref):
        """Get the value of a cell from a sheet.
        
        Args:
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference (e.g., "A1")
            
        Returns:
            Cell value or None if not found
        """
        pass
    
    def get_cell_formula(self, sheet_name, cell_ref):
        """Get the formula of a cell from a sheet.
        
        Args:
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference (e.g., "A1")
            
        Returns:
            Formula string or None if not found
        """
        pass
    
    def execute_formula(self, formula_or_parsed, sheet_name, cell_ref):
        """Execute a formula and return the result.
        
        Args:
            formula_or_parsed (str or dict): Formula string or parsed formula
            sheet_name (str): Name of the sheet containing the formula
            cell_ref (str): Cell reference (e.g., "A1")
            
        Returns:
            Formula execution result
        """
        pass
    
    def run_engine(self, sheet_name=None, fail_on_error=True):
        """Run the calculation engine on the specified sheet.
        
        Args:
            sheet_name (str): Name of the sheet to process
            fail_on_error (bool): Whether to raise exceptions on errors
            
        Returns:
            Tuple of (results DataFrame, errors list)
        """
        pass
```

### formula_parser.py

Excel formula parsing utilities.

#### parse_formula
```python
def parse_formula(formula):
    """Parse an Excel formula into a structured representation.
    
    Args:
        formula (str): Formula string to parse
        
    Returns:
        Dictionary representing the parsed formula
    """
    pass
```

### strategies.py

Formula calculation strategies implementing the Strategy pattern.

#### BaseStrategy
```python
class BaseStrategy:
    """Base class for all calculation strategies."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute the calculation strategy.
        
        Args:
            parsed_formula (dict): Parsed formula to execute
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Calculation result
        """
        pass
```

#### LiteralStrategy
```python
class LiteralStrategy(BaseStrategy):
    """Strategy for handling numeric literals."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute literal strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "value" key
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Numeric value from the literal
        """
        pass
```

#### ReferenceStrategy
```python
class ReferenceStrategy(BaseStrategy):
    """Strategy for handling cell references."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute reference strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "sheet" and "cell" keys
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Value from the referenced cell
        """
        pass
```

#### MultiplicationStrategy
```python
class MultiplicationStrategy(BaseStrategy):
    """Strategy for handling multiplication formulas."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute multiplication strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "operands" key
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Product of all operands
        """
        pass
```

#### AdditionStrategy
```python
class AdditionStrategy(BaseStrategy):
    """Strategy for handling addition formulas."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute addition strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "operands" key
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Sum of all operands
        """
        pass
```

#### SumRangeStrategy
```python
class SumRangeStrategy(BaseStrategy):
    """Strategy for handling SUM formulas with a range."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute sum range strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "start_cell" and "end_cell" keys
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Sum of all numeric values in the range
        """
        pass
```

#### IfStrategy
```python
class IfStrategy(BaseStrategy):
    """Strategy for handling IF formulas."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute IF strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "condition", "true_val", and "false_val" keys
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Result of true_val if condition is true, false_val otherwise
        """
        pass
```

#### VLookupStrategy
```python
class VLookupStrategy(BaseStrategy):
    """Strategy for handling VLOOKUP formulas."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute VLOOKUP strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "lookup_value", "table_array", "col_index_num", and "range_lookup" keys
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Lookup result from the table
        """
        pass
```

#### PmtStrategy
```python
class PmtStrategy(BaseStrategy):
    """Strategy for handling PMT formulas."""
    
    def execute(self, parsed_formula, engine, sheet_name, cell_ref):
        """Execute PMT strategy.
        
        Args:
            parsed_formula (dict): Parsed formula with "rate", "nper", and "pv" keys
            engine (CalculationEngine): Calculation engine instance
            sheet_name (str): Name of the sheet
            cell_ref (str): Cell reference
            
        Returns:
            Payment amount calculated using the PMT formula
        """
        pass
```

### sheet_manager.py

Sheet loading and management.

#### SheetManager
```python
class SheetManager:
    def __init__(self, excel_file_path=None, verbose=False, prepared_data_path=None, sheet_configs=None):
        """Initialize the sheet manager.
        
        Args:
            excel_file_path (Path | str | None, optional): Path to the Excel file.
                If None, loads from configuration. Defaults to None.
            verbose (bool, optional): Whether to enable verbose logging. Defaults to False.
            prepared_data_path (Path | str | None, optional): Path to prepared data directory.
                If None, uses default location. Defaults to None.
            sheet_configs (dict | None, optional): Sheet configuration dictionary.
                If None, uses default configuration. Defaults to None.
        """
        pass
    
    def get_sheet_names(self):
        """Get list of available sheet names.
        
        Returns:
            list: List of sheet names
        """
        pass
    
    def get_data(self, sheet_name):
        """Get data DataFrame for a given sheet.
        
        Args:
            sheet_name (str): Name of the sheet
            
        Returns:
            pandas.DataFrame: Sheet data
        """
        pass
    
    def get_formulas(self, sheet_name):
        """Get formulas DataFrame for a given sheet.
        
        Args:
            sheet_name (str): Name of the sheet
            
        Returns:
            pandas.DataFrame: Sheet formulas
        """
        pass
    
    def get_ground_truth(self, sheet_name=None):
        """Get ground truth values from the original Excel file.
        
        Args:
            sheet_name (str | None, optional): Name of the sheet. If None, uses default.
            
        Returns:
            pandas.DataFrame: Ground truth data
        """
        pass
```

### data_manager.py

Unified data management with consistent handling across all sheet types.

#### DataManager
```python
class DataManager:
    def __init__(self, data_dir=None):
        """Initialize the data manager.
        
        Args:
            data_dir (Path, optional): Base data directory. If None, uses default location.
        """
        pass
    
    def get_sheet_names(self):
        """Get list of all available sheet names from configuration.
        
        Returns:
            List[str]: List of sheet names configured for processing
        """
        pass
    
    def load_sheet(self, sheet_name, format="parquet"):
        """Load a specific sheet in the specified format.
        
        Args:
            sheet_name (str): Name of the sheet to load
            format (str, optional): Format to load ('parquet' or 'csv'). Defaults to 'parquet'.
            
        Returns:
            Optional[pandas.DataFrame]: DataFrame containing the sheet data, or None if not found
        """
        pass
    
    def save_sheet(self, sheet_name, df, formats=None):
        """Save a sheet in specified formats with consistent naming.
        
        Args:
            sheet_name (str): Name of the sheet to save
            df (pandas.DataFrame): DataFrame containing the sheet data
            formats (List[str], optional): Formats to save ('parquet', 'csv'). 
                                         If None, saves in all supported formats.
            
        Returns:
            bool: True if successfully saved, False otherwise
        """
        pass
    
    def save_for_publication(self, sheet_name, df, metadata=None):
        """Save a sheet and its metadata for publication with consistent formatting.
        
        Args:
            sheet_name (str): Name of the sheet to save
            df (pandas.DataFrame): DataFrame containing the sheet data
            metadata (Dict[str, Any], optional): Metadata about the sheet
            
        Returns:
            bool: True if successfully saved, False otherwise
        """
        pass
```

## Configuration Modules

### config.py

Configuration loading and management.

#### load_config
```python
def load_config(config_path=None):
    """Load the YAML configuration file.
    
    This function loads the configuration from a YAML file, with support for
    fallback paths for backward compatibility.
    
    Args:
        config_path (str | Path | None, optional): Path to the configuration file.
            If None, tries default locations. Defaults to None.
    
    Returns:
        dict: The loaded configuration data.
    
    Raises:
        FileNotFoundError: If the configuration file cannot be found.
        ValueError: If there is an error parsing the YAML file.
    """
    pass
```

## Utility Modules

### utils.py

General utility functions.

#### coords_to_cell
```python
def coords_to_cell(row, col):
    """Convert (row, col) tuple to cell string.
    
    Converts zero-based row and column indices to Excel-style cell references.
    For example, (0, 0) becomes "A1", (1, 2) becomes "C2".
    
    Args:
        row (int): Zero-based row index.
        col (int): Zero-based column index.
    
    Returns:
        str: Excel-style cell reference (e.g., "A1").
    """
    pass
```

#### cell_to_coords
```python
def cell_to_coords(cell_str):
    """Convert cell string to (row, col) tuple.
    
    Converts Excel-style cell references to zero-based row and column indices.
    For example, "A1" becomes (0, 0), "C2" becomes (1, 2).
    Handles cell references with $ signs (e.g., "$A$1").
    
    Args:
        cell_str (str): Excel-style cell reference (e.g., "A1" or "$A$1").
    
    Returns:
        tuple: A tuple of (row, col) as zero-based indices, or (None, None) if invalid.
    """
    pass
```

### excel_utils.py

Excel file handling utilities.

#### load_sheet_with_headers
```python
def load_sheet_with_headers(file_path, sheet_name, *, header_rows, string_columns=None):
    """Read an Excel sheet with multiple header rows.
    
    Merged cells are expanded and header rows are forward filled. Columns
    listed in ``string_columns`` are left as object type while all others
    are coerced to numeric where possible.
    
    Args:
        file_path (str | Path): Path to the Excel file
        sheet_name (str): Name of the sheet to load
        header_rows (int): Number of header rows
        string_columns (Sequence[str] | None, optional): Columns to keep as strings
    
    Returns:
        pd.DataFrame: DataFrame with loaded sheet data
    """
    pass
```

### logging_config.py

Centralized logging configuration.

#### setup_logging
```python
def setup_logging(log_level=logging.INFO, log_file=None, format_string=None):
    """Set up logging for the application.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional file to write logs to
        format_string: Optional format string for log messages
        
    Returns:
        Configured logger instance
    """
    pass
```

#### get_logger
```python
def get_logger(name="microcosting"):
    """Get a logger instance with the specified name.
    
    Args:
        name: Name for the logger (default: "microcosting")
        
    Returns:
        Logger instance
    """
    pass
```

## Analysis Modules

### scenario_modeling.py

Scenario modeling tools for what-if analysis.

#### Scenario
```python
@dataclass
class Scenario:
    """Represents a scenario with specific parameter adjustments."""
    name: str
    description: str
    parameters: Dict[str, Any]
    adjustments: Dict[str, float]  # column -> multiplier or absolute value
```

#### ScenarioManager
```python
class ScenarioManager:
    def __init__(self, base_data: Dict[str, pd.DataFrame]):
        """Initialize the scenario manager with base data.
        
        Args:
            base_data: Dictionary of DataFrames representing the base case data
        """
        pass
    
    def add_scenario(self, scenario: Scenario) -> None:
        """Add a scenario to the manager.
        
        Args:
            scenario: Scenario object to add
        """
        pass
    
    def add_scenario_from_dict(self, name: str, description: str, parameters: Dict[str, Any], 
                              adjustments: Dict[str, float]) -> None:
        """Add a scenario from dictionary parameters.
        
        Args:
            name: Name of the scenario
            description: Description of the scenario
            parameters: Parameters for the scenario
            adjustments: Column adjustments for the scenario
        """
        pass
    
    def apply_scenario(self, scenario_name: str, table_name: str) -> pd.DataFrame:
        """Apply a scenario to a specific table.
        
        Args:
            scenario_name: Name of the scenario to apply
            table_name: Name of the table to apply the scenario to
            
        Returns:
            DataFrame with scenario adjustments applied
        """
        pass
    
    def run_scenario_analysis(self, scenario_name: str) -> Dict[str, pd.DataFrame]:
        """Run analysis for a specific scenario across all tables.
        
        Args:
            scenario_name: Name of the scenario to run
            
        Returns:
            Dictionary of DataFrames with scenario applied to each table
        """
        pass
    
    def compare_scenarios(self, scenario_names: List[str], table_name: str, 
                         columns: Optional[List[str]] = None) -> pd.DataFrame:
        """Compare multiple scenarios for a specific table.
        
        Args:
            scenario_names: List of scenario names to compare
            table_name: Name of the table to compare
            columns: Specific columns to compare (if None, compare all numeric columns)
            
        Returns:
            DataFrame with scenario comparisons
        """
        pass
    
    def generate_scenario_report(self, scenario_names: List[str], 
                               output_file: Optional[str] = None) -> str:
        """Generate a report comparing multiple scenarios.
        
        Args:
            scenario_names: List of scenario names to compare
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        pass
```

### advanced_scenario_modeling.py

Advanced deterministic and probabilistic sensitivity analysis capabilities.

#### AdvancedScenario
```python
@dataclass
class AdvancedScenario(Scenario):
    """Enhanced scenario with more sophisticated parameter adjustments."""
    sensitivity_parameters: Dict[str, Tuple[float, float]] = None  # parameter -> (min, max) for sensitivity analysis
    probability_distributions: Dict[str, Dict[str, Any]] = None  # parameter -> distribution info
    dependencies: Dict[str, List[str]] = None  # parameter -> list of dependent parameters
```

#### AdvancedScenarioManager
```python
class AdvancedScenarioManager(ScenarioManager):
    def __init__(self, base_data: Dict[str, pd.DataFrame]):
        """Initialize the advanced scenario manager with base data.
        
        Args:
            base_data: Dictionary of DataFrames representing the base case data
        """
        pass
    
    def add_advanced_scenario(self, scenario: AdvancedScenario) -> None:
        """Add an advanced scenario to the manager.
        
        Args:
            scenario: AdvancedScenario object to add
        """
        pass
    
    def run_sensitivity_analysis(self, scenario_name: str, parameter: str, 
                               range_min: float, range_max: float, 
                               steps: int = 10) -> Dict[str, List[float]]:
        """Run sensitivity analysis for a specific parameter.
        
        Args:
            scenario_name: Name of the scenario to analyze
            parameter: Parameter to vary
            range_min: Minimum value for the parameter
            range_max: Maximum value for the parameter
            steps: Number of steps to test
            
        Returns:
            Dictionary with parameter values and corresponding results
        """
        pass
    
    def run_probabilistic_analysis(self, scenario_name: str, iterations: int = 1000) -> Dict[str, List[Dict[str, pd.DataFrame]]]:
        """Run probabilistic analysis using Monte Carlo simulation.
        
        Args:
            scenario_name: Name of the scenario to analyze
            iterations: Number of Monte Carlo iterations
            
        Returns:
            Dictionary with probabilistic results
        """
        pass
    
    def compare_scenarios_detailed(self, scenario_names: List[str], table_name: str,
                                 metrics: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """Perform detailed comparison of scenarios with multiple metrics.
        
        Args:
            scenario_names: List of scenario names to compare
            table_name: Name of the table to compare
            metrics: List of metrics to calculate (mean, std, min, max, etc.)
            
        Returns:
            Dictionary with detailed comparison results
        """
        pass
```

## Visualization Modules

### visualization.py

Basic data visualization tools.

#### load_prepared_data
```python
def load_prepared_data(data_dir=None):
    """Load prepared data from the data directory.
    
    Args:
        data_dir (str or Path, optional): Path to the data directory. 
            If None, uses the default data/prepared directory.
            
    Returns:
        dict: Dictionary of loaded DataFrames with keys as table names.
    """
    pass
```

#### plot_cost_distribution
```python
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
    pass
```

#### plot_category_costs
```python
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
    pass
```

#### plot_cost_breakdown
```python
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
    pass
```

#### plot_top_costs
```python
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
    pass
```

### advanced_visualization.py

Enhanced visualization tools with interactive Plotly charts.

#### plot_interactive_cost_distribution
```python
def plot_interactive_cost_distribution(data, column_name, title="Cost Distribution"):
    """Create an interactive histogram of cost distribution.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        column_name (str): Name of the column to plot.
        title (str): Title for the plot.
        
    Returns:
        plotly.graph_objects.Figure: The generated interactive figure.
    """
    pass
```

#### plot_interactive_category_costs
```python
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
    pass
```

#### plot_cost_trend_analysis
```python
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
    pass
```

#### plot_cost_correlation_matrix
```python
def plot_cost_correlation_matrix(data, cost_columns, title="Cost Correlation Matrix"):
    """Create a correlation matrix heatmap for cost columns.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data.
        cost_columns (list): List of cost column names to include.
        title (str): Title for the plot.
        
    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    pass
```

#### plot_interactive_cost_scatter
```python
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
    pass
```

## Web Modules

### web.py

Flask-based web application for data exploration.

#### create_app
```python
def create_app(data_dir=None):
    """Create and configure the Flask application.
    
    Args:
        data_dir (str or Path, optional): Path to the data directory.
        
    Returns:
        Flask: Configured Flask application.
    """
    pass
```

#### main
```python
def main():
    """Main function to run the web application."""
    pass
```

### web_viz.py

Web-based visualization utilities.

#### create_plot_base64
```python
def create_plot_base64(plot_function, *args, **kwargs):
    """Create a plot and return it as a base64 encoded string.
    
    Args:
        plot_function: Function that creates a matplotlib plot
        *args: Arguments to pass to the plot function
        **kwargs: Keyword arguments to pass to the plot function
        
    Returns:
        str: Base64 encoded PNG image
    """
    pass
```

#### generate_visualization
```python
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
    pass
```

#### get_available_columns
```python
def get_available_columns(data):
    """Get lists of available columns for visualization.
    
    Args:
        data (pd.DataFrame): DataFrame containing the data
        
    Returns:
        dict: Dictionary with lists of numeric and category columns
    """
    pass
```

## Plugin Modules

### plugin_system.py

Base plugin system implementation.

#### Plugin
```python
class Plugin:
    def __init__(self, name: str, version: str, description: str):
        """Initialize a plugin.
        
        Args:
            name (str): Plugin name
            version (str): Plugin version
            description (str): Plugin description
        """
        pass
    
    def initialize(self) -> None:
        """Initialize the plugin."""
        pass
    
    def cleanup(self) -> None:
        """Clean up the plugin."""
        pass
```

#### AnalysisPlugin
```python
class AnalysisPlugin(Plugin):
    """Plugin for analysis functionality."""
    
    def analyze(self, data: Any) -> Any:
        """Perform analysis on data.
        
        Args:
            data (Any): Input data
            
        Returns:
            Any: Analysis results
        """
        pass
```

#### VisualizationPlugin
```python
class VisualizationPlugin(Plugin):
    """Plugin for visualization functionality."""
    
    def visualize(self, data: Any, **kwargs) -> Any:
        """Create visualization of data.
        
        Args:
            data (Any): Input data
            **kwargs: Additional visualization parameters
            
        Returns:
            Any: Visualization object
        """
        pass
```

#### PluginManager
```python
class PluginManager:
    def __init__(self, plugin_directory: Optional[Path] = None):
        """Initialize the plugin manager.
        
        Args:
            plugin_directory (Path, optional): Directory to search for plugins
        """
        pass
    
    def load_plugin(self, plugin_path: Path) -> Plugin:
        """Load a plugin from a file.
        
        Args:
            plugin_path (Path): Path to the plugin file
            
        Returns:
            Plugin: Loaded plugin instance
            
        Raises:
            ImportError: If plugin cannot be loaded
        """
        pass
    
    def discover_plugins(self) -> List[Path]:
        """Discover plugin files in the plugin directory.
        
        Returns:
            List[Path]: List of plugin file paths
        """
        pass
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin.
        
        Args:
            plugin (Plugin): Plugin instance to register
        """
        pass
    
    def load_all_plugins(self) -> None:
        """Load and register all plugins in the plugin directory."""
        pass
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a registered plugin by name.
        
        Args:
            name (str): Plugin name
            
        Returns:
            Plugin: Plugin instance or None if not found
        """
        pass
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins.
        
        Returns:
            List[Dict[str, Any]]: List of plugin information
        """
        pass
```

### enhanced_plugin_system.py

Enhanced plugin system with metadata and configuration support.

#### PluginMetadata
```python
@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    license: str
    dependencies: List[str]
    tags: List[str]
    created_date: str
    last_updated: str
```

#### EnhancedPlugin
```python
class EnhancedPlugin(Plugin):
    """Enhanced plugin with metadata and lifecycle management."""
    
    def __init__(self, name: str, version: str, description: str, 
                 author: str = "", license: str = "", dependencies: List[str] = None,
                 tags: List[str] = None):
        """Initialize an enhanced plugin.
        
        Args:
            name (str): Plugin name
            version (str): Plugin version
            description (str): Plugin description
            author (str): Plugin author
            license (str): Plugin license
            dependencies (List[str]): Plugin dependencies
            tags (List[str]): Plugin tags for categorization
        """
        pass
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set plugin configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """Get plugin configuration.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        pass
    
    def export_metadata(self) -> Dict[str, Any]:
        """Export plugin metadata.
        
        Returns:
            Dict[str, Any]: Plugin metadata as dictionary
        """
        pass
    
    def validate_dependencies(self, available_plugins: List[str]) -> List[str]:
        """Validate plugin dependencies.
        
        Args:
            available_plugins (List[str]): List of available plugin names
            
        Returns:
            List[str]: List of missing dependencies
        """
        pass
```

#### DataProcessingPlugin
```python
class DataProcessingPlugin(EnhancedPlugin):
    """Plugin for data processing functionality."""
    
    def process(self, data: Any, **kwargs) -> Any:
        """Process data.
        
        Args:
            data (Any): Input data
            **kwargs: Additional processing parameters
            
        Returns:
            Any: Processed data
        """
        pass
```

#### ReportPlugin
```python
class ReportPlugin(EnhancedPlugin):
    """Plugin for report generation functionality."""
    
    def generate_report(self, data: Any, output_format: str = "markdown", **kwargs) -> str:
        """Generate report.
        
        Args:
            data (Any): Input data
            output_format (str): Output format (markdown, html, pdf, etc.)
            **kwargs: Additional report parameters
            
        Returns:
            str: Generated report
        """
        pass
```

#### EnhancedPluginManager
```python
class EnhancedPluginManager:
    def __init__(self, plugin_directory: Optional[Path] = None, 
                 config_file: Optional[Path] = None):
        """Initialize the enhanced plugin manager.
        
        Args:
            plugin_directory (Path, optional): Directory to search for plugins
            config_file (Path, optional): Configuration file for plugin settings
        """
        pass
    
    def load_config(self) -> None:
        """Load plugin manager configuration."""
        pass
    
    def save_config(self) -> None:
        """Save plugin manager configuration."""
        pass
    
    def load_plugin(self, plugin_path: Path) -> EnhancedPlugin:
        """Load an enhanced plugin from a file.
        
        Args:
            plugin_path (Path): Path to the plugin file
            
        Returns:
            EnhancedPlugin: Loaded plugin instance
            
        Raises:
            ImportError: If plugin cannot be loaded
        """
        pass
    
    def discover_plugins(self) -> List[Path]:
        """Discover plugin files in the plugin directory.
        
        Returns:
            List[Path]: List of plugin file paths
        """
        pass
    
    def register_plugin(self, plugin: EnhancedPlugin) -> None:
        """Register a plugin.
        
        Args:
            plugin (EnhancedPlugin): Plugin instance to register
        """
        pass
    
    def load_all_plugins(self) -> None:
        """Load and register all plugins in the plugin directory."""
        pass
    
    def get_plugin(self, name: str) -> Optional[EnhancedPlugin]:
        """Get a registered plugin by name.
        
        Args:
            name (str): Plugin name
            
        Returns:
            EnhancedPlugin: Plugin instance or None if not found
        """
        pass
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins.
        
        Returns:
            List[Dict[str, Any]]: List of plugin information
        """
        pass
    
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin.
        
        Args:
            name (str): Plugin name
            
        Returns:
            bool: True if plugin was enabled, False otherwise
        """
        pass
    
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin.
        
        Args:
            name (str): Plugin name
            
        Returns:
            bool: True if plugin was disabled, False otherwise
        """
        pass
    
    def execute_plugin(self, name: str, data: Any, **kwargs) -> Any:
        """Execute a plugin.
        
        Args:
            name (str): Plugin name
            data (Any): Input data
            **kwargs: Additional arguments for the plugin
            
        Returns:
            Any: Plugin execution result
            
        Raises:
            ValueError: If plugin is not found or not enabled
        """
        pass
```

## Performance Modules

### performance.py

Performance monitoring and optimization tools.

#### PerformanceProfiler
```python
class PerformanceProfiler:
    def __init__(self):
        """Initialize the performance profiler."""
        pass
    
    def profile(self, operation_name: str):
        """Decorator to profile a function.
        
        Args:
            operation_name (str): Name of the operation to profile
        """
        pass
    
    def get_report(self) -> Dict[str, Dict[str, Any]]:
        """Get performance report.
        
        Returns:
            Dict[str, Dict[str, Any]]: Performance metrics for all operations
        """
        pass
    
    def print_report(self) -> None:
        """Print formatted performance report."""
        pass
```

#### DataOptimizer
```python
class DataOptimizer:
    @staticmethod
    def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage.
        
        Args:
            df (pd.DataFrame): DataFrame to optimize
            
        Returns:
            pd.DataFrame: Optimized DataFrame
        """
        pass
    
    @staticmethod
    def chunked_processing(df: pd.DataFrame, chunk_size: int = 1000) -> pd.DataFrame:
        """Process DataFrame in chunks to reduce memory usage.
        
        Args:
            df (pd.DataFrame): DataFrame to process
            chunk_size (int): Size of each chunk
            
        Returns:
            pd.DataFrame: Processed DataFrame
        """
        pass
```

#### ParallelProcessor
```python
class ParallelProcessor:
    @staticmethod
    def parallel_apply(df: pd.DataFrame, func: Callable, column: str, 
                      n_cores: int = 4) -> pd.Series:
        """Apply function to column in parallel.
        
        Args:
            df (pd.DataFrame): DataFrame to process
            func (Callable): Function to apply
            column (str): Column to apply function to
            n_cores (int): Number of cores to use
            
        Returns:
            pd.Series: Series with function applied
        """
        pass
```

## Version Control Modules

### excel_version_control.py

Excel workbook version control utilities.

#### WorkbookVersion
```python
class WorkbookVersion:
    def __init__(self, version_id: str, timestamp: datetime, file_path: Path,
                 checksum: str, metadata: Dict[str, Any]):
        """Initialize a WorkbookVersion.
        
        Args:
            version_id (str): Unique identifier for this version
            timestamp (datetime): When this version was created
            file_path (Path): Path to the workbook file
            checksum (str): Checksum of the file content
            metadata (Dict[str, Any]): Additional metadata about the version
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        pass
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkbookVersion':
        """Create WorkbookVersion from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation
            
        Returns:
            WorkbookVersion: Created WorkbookVersion instance
        """
        pass
```

#### WorkbookVersionControl
```python
class WorkbookVersionControl:
    def __init__(self, repository_directory: Path):
        """Initialize the workbook version control system.
        
        Args:
            repository_directory (Path): Directory to store workbook versions
        """
        pass
    
    def commit_workbook(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Commit a workbook file and create a new version.
        
        Args:
            file_path (Path): Path to the workbook file
            metadata (Dict[str, Any], optional): Additional metadata
            
        Returns:
            str: Version ID of the committed workbook
            
        Raises:
            FileNotFoundError: If the workbook file is not found
        """
        pass
    
    def get_latest_version(self, workbook_name: str) -> Optional[WorkbookVersion]:
        """Get the latest version of a workbook.
        
        Args:
            workbook_name (str): Name of the workbook
            
        Returns:
            Optional[WorkbookVersion]: Latest version or None if not found
        """
        pass
    
    def get_version_history(self, workbook_name: str) -> List[WorkbookVersion]:
        """Get version history for a workbook.
        
        Args:
            workbook_name (str): Name of the workbook
            
        Returns:
            List[WorkbookVersion]: List of versions
        """
        pass
    
    def restore_version(self, version_id: str, target_path: Path) -> bool:
        """Restore a specific version of a workbook.
        
        Args:
            version_id (str): Version ID to restore
            target_path (Path): Path to restore the workbook to
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    def compare_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """Compare two versions of a workbook.
        
        Args:
            version_id1 (str): First version ID
            version_id2 (str): Second version ID
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        pass
```

### security.py

Security module providing comprehensive security capabilities including input sanitization, role-based access control, audit trail tracking, and secure configuration storage.

#### InputSanitizer
```python
class InputSanitizer:
    def __init__(self, logger=None):
        """Initialize the input sanitizer.
        
        Args:
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def sanitize_string_input(self, value, max_length=1000):
        """Sanitize string input to prevent injection attacks.
        
        Args:
            value (str): String value to sanitize
            max_length (int): Maximum allowed length
            
        Returns:
            str: Sanitized string
            
        Raises:
            ValidationError: If input is invalid
        """
        pass
    
    def sanitize_file_path(self, file_path):
        """Sanitize file path to prevent directory traversal attacks.
        
        Args:
            file_path (str): File path to sanitize
            
        Returns:
            str: Sanitized file path
            
        Raises:
            ValidationError: If path is invalid
        """
        pass
    
    def sanitize_excel_cell_reference(self, cell_ref):
        """Sanitize Excel cell reference.
        
        Args:
            cell_ref (str): Cell reference to sanitize
            
        Returns:
            str: Sanitized cell reference
            
        Raises:
            ValidationError: If cell reference is invalid
        """
        pass
    
    def sanitize_sheet_name(self, sheet_name):
        """Sanitize Excel sheet name.
        
        Args:
            sheet_name (str): Sheet name to sanitize
            
        Returns:
            str: Sanitized sheet name
            
        Raises:
            ValidationError: If sheet name is invalid
        """
        pass
```

#### Role
```python
class Role:
    def __init__(self, name, permissions):
        """Initialize a role.
        
        Args:
            name (str): Role name
            permissions (Set[str]): Set of permissions for this role
        """
        pass
    
    def has_permission(self, permission):
        """Check if role has a specific permission.
        
        Args:
            permission (str): Permission to check
            
        Returns:
            bool: True if role has permission, False otherwise
        """
        pass
    
    def add_permission(self, permission):
        """Add a permission to the role.
        
        Args:
            permission (str): Permission to add
        """
        pass
    
    def remove_permission(self, permission):
        """Remove a permission from the role.
        
        Args:
            permission (str): Permission to remove
        """
        pass
```

#### User
```python
class User:
    def __init__(self, username, roles=None):
        """Initialize a user.
        
        Args:
            username (str): Username
            roles (List[Role]): List of roles for this user
        """
        pass
    
    def has_permission(self, permission):
        """Check if user has a specific permission.
        
        Args:
            permission (str): Permission to check
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        pass
    
    def add_role(self, role):
        """Add a role to the user.
        
        Args:
            role (Role): Role to add
        """
        pass
    
    def remove_role(self, role):
        """Remove a role from the user.
        
        Args:
            role (Role): Role to remove
        """
        pass
```

#### AccessControlManager
```python
class AccessControlManager:
    def __init__(self, logger=None):
        """Initialize the access control manager.
        
        Args:
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def authenticate_user(self, username, password=None):
        """Authenticate a user.
        
        Args:
            username (str): Username
            password (str): Password (optional for demo purposes)
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        pass
    
    def logout_user(self):
        """Log out the current user."""
        pass
    
    def require_permission(self, permission):
        """Decorator to require a specific permission for a function.
        
        Args:
            permission (str): Required permission
            
        Returns:
            function: Decorator function
        """
        pass
    
    def add_user_to_role(self, username, role_name):
        """Add a user to a role.
        
        Args:
            username (str): Username
            role_name (str): Role name
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    def get_user_permissions(self, username):
        """Get all permissions for a user.
        
        Args:
            username (str): Username
            
        Returns:
            Set[str]: Set of permissions
        """
        pass
```

#### AuditTrail
```python
class AuditTrail:
    def __init__(self, log_file=None, logger=None):
        """Initialize the audit trail.
        
        Args:
            log_file (str): File to store audit logs (optional)
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def log_event(self, event_type, user, resource, details=None, success=True):
        """Log a security-relevant event.
        
        Args:
            event_type (str): Type of event (e.g., 'login', 'access', 'modification')
            user (str): Username (if authenticated)
            resource (str): Resource being accessed or modified
            details (str): Additional details about the event
            success (bool): Whether the event was successful
        """
        pass
    
    def get_events(self, user=None, event_type=None, start_time=None, end_time=None):
        """Get audit events matching criteria.
        
        Args:
            user (str): Filter by username
            event_type (str): Filter by event type
            start_time (str): Filter by start time (ISO format)
            end_time (str): Filter by end time (ISO format)
            
        Returns:
            List[Dict[str, Any]]: List of matching events
        """
        pass
    
    def clear_events(self):
        """Clear all audit events."""
        pass
```

#### SecureConfigStorage
```python
class SecureConfigStorage:
    def __init__(self, config_file, encryption_key=None, logger=None):
        """Initialize secure configuration storage.
        
        Args:
            config_file (str): Path to configuration file
            encryption_key (str): Encryption key (optional)
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def save_config(self, config_data):
        """Save configuration data securely.
        
        Args:
            config_data (Dict[str, Any]): Configuration data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    def load_config(self):
        """Load configuration data securely.
        
        Returns:
            Dict[str, Any]: Configuration data, or None if failed
        """
        pass
```

#### setup_standard_security
```python
def setup_standard_security(logger=None):
    """Set up standard security components.
    
    Args:
        logger (logging.Logger): Logger instance (optional)
        
    Returns:
        tuple: Tuple of (InputSanitizer, AccessControlManager, AuditTrail, SecureConfigStorage)
    """
    pass
```

### monitoring.py

Monitoring and observability system for genomics microcosting analysis.

#### HealthCheckError
```python
class HealthCheckError(Exception):
    """Custom exception for health check failures."""
    pass
```

#### SystemHealthChecker
```python
class SystemHealthChecker:
    def __init__(self, logger=None):
        """Initialize the system health checker.
        
        Args:
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def register_health_check(self, name, check_function):
        """Register a health check function.
        
        Args:
            name (str): Name of the health check
            check_function (function): Function that performs the health check
        """
        pass
    
    def run_health_check(self):
        """Run all registered health checks.
        
        Returns:
            Dict[str, Any]: Dictionary with health check results
        """
        pass
    
    def check_disk_space(self, min_free_gb=1.0):
        """Check available disk space.
        
        Args:
            min_free_gb (float): Minimum free space in GB
            
        Returns:
            Dict[str, Any]: Dictionary with disk space information
        """
        pass
    
    def check_memory_usage(self, max_percent=90.0):
        """Check system memory usage.
        
        Args:
            max_percent (float): Maximum memory usage percentage
            
        Returns:
            Dict[str, Any]: Dictionary with memory usage information
        """
        pass
    
    def check_cpu_usage(self, max_percent=95.0):
        """Check CPU usage.
        
        Args:
            max_percent (float): Maximum CPU usage percentage
            
        Returns:
            Dict[str, Any]: Dictionary with CPU usage information
        """
        pass
    
    def check_data_availability(self, data_dir="data/prepared"):
        """Check if required data files are available.
        
        Args:
            data_dir (str): Path to prepared data directory
            
        Returns:
            Dict[str, Any]: Dictionary with data availability information
        """
        pass
```

#### PerformanceMetricsCollector
```python
class PerformanceMetricsCollector:
    def __init__(self, max_history=1000, logger=None):
        """Initialize the performance metrics collector.
        
        Args:
            max_history (int): Maximum number of metrics to store
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def record_metric(self, metric_name, value, tags=None):
        """Record a performance metric.
        
        Args:
            metric_name (str): Name of the metric
            value (float): Metric value
            tags (Dict[str, str]): Optional tags for the metric
        """
        pass
    
    def get_metric_history(self, metric_name):
        """Get historical data for a metric.
        
        Args:
            metric_name (str): Name of the metric
            
        Returns:
            List[Dict[str, Any]]: List of metric data points
        """
        pass
    
    def get_current_metrics(self):
        """Get current metrics.
        
        Returns:
            Dict[str, Any]: Dictionary of current metrics
        """
        pass
    
    def get_metrics_summary(self):
        """Get a summary of all metrics.
        
        Returns:
            Dict[str, Any]: Dictionary with metrics summary
        """
        pass
```

#### UsageAnalytics
```python
class UsageAnalytics:
    def __init__(self, log_file="logs/usage.log", logger=None):
        """Initialize the usage analytics tracker.
        
        Args:
            log_file (str): File to store usage logs
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def log_user_action(self, user_id, action, resource, details=None):
        """Log a user action.
        
        Args:
            user_id (str): User identifier
            action (str): Action performed
            resource (str): Resource acted upon
            details (Dict[str, Any]): Additional details about the action
        """
        pass
    
    def get_usage_statistics(self, start_time=None, end_time=None):
        """Get usage statistics.
        
        Args:
            start_time (str): Start time for statistics (ISO format)
            end_time (str): End time for statistics (ISO format)
            
        Returns:
            Dict[str, Any]: Dictionary with usage statistics
        """
        pass
```

#### AlertManager
```python
class AlertManager:
    def __init__(self, alert_file="logs/alerts.log", logger=None):
        """Initialize the alert manager.
        
        Args:
            alert_file (str): File to store alerts
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def send_alert(self, alert_type, message, severity="warning", details=None):
        """Send an alert.
        
        Args:
            alert_type (str): Type of alert
            message (str): Alert message
            severity (str): Severity level (info, warning, error, critical)
            details (Dict[str, Any]): Additional details about the alert
        """
        pass
    
    def get_recent_alerts(self, hours=24):
        """Get recent alerts.
        
        Args:
            hours (int): Number of hours to look back
            
        Returns:
            List[Dict[str, Any]]: List of recent alerts
        """
        pass
```

#### MonitoringMiddleware
```python
class MonitoringMiddleware:
    def __init__(self, metrics_collector=None, logger=None):
        """Initialize the monitoring middleware.
        
        Args:
            metrics_collector (PerformanceMetricsCollector): Performance metrics collector
            logger (logging.Logger): Logger instance (optional)
        """
        pass
    
    def monitor_execution_time(self, metric_name=None):
        """Decorator to monitor execution time of functions.
        
        Args:
            metric_name (str): Name for the timing metric (defaults to function name)
            
        Returns:
            function: Decorator function
        """
        pass
```

#### setup_standard_monitoring
```python
def setup_standard_monitoring(logger=None):
    """Set up standard monitoring components.
    
    Args:
        logger (logging.Logger): Logger instance (optional)
        
    Returns:
        tuple: Tuple of (SystemHealthChecker, PerformanceMetricsCollector, 
                       UsageAnalytics, AlertManager, MonitoringMiddleware)
    """
    pass