# Plugin System Documentation

The Plugin System provides a flexible and extensible architecture for adding functionality to the microcosting analysis toolkit.

## Overview

The plugin system enables researchers and developers to extend the toolkit's capabilities without modifying the core codebase. It supports dynamic loading of plugins, metadata management, and dependency handling.

## Architecture

The plugin system follows a modular architecture with the following key components:

### Core Classes

1. **EnhancedPluginSystem** - Main plugin management class
2. **AnalysisPlugin** - Base class for all plugins
3. **PluginManager** - Handles plugin loading and execution
4. **PluginRegistry** - Maintains registry of available plugins

### Design Principles

- **Modularity**: Plugins are self-contained and independent
- **Extensibility**: Easy to add new plugin types and functionality
- **Metadata Support**: Rich plugin metadata and configuration
- **Dependency Management**: Support for plugin dependencies and versioning

## Key Features

### Dynamic Plugin Loading
Plugins are dynamically discovered and loaded at runtime:

```python
from unimelb_phd_phase_1.enhanced_plugin_system import EnhancedPluginSystem

# Initialize plugin system
plugin_system = EnhancedPluginSystem()

# Discover and load plugins
plugin_system.discover_plugins()

# List available plugins
plugins = plugin_system.list_plugins()
for plugin in plugins:
    print(f"Plugin: {plugin.name} v{plugin.version}")
```

### Plugin Metadata
Rich metadata support for plugins:
- Name, version, and description
- Author and contact information
- Tags and categories
- Dependencies and requirements
- Configuration options

### Plugin Dependencies
Support for plugin dependencies:
- Version constraints
- Optional dependencies
- Circular dependency detection
- Dependency resolution

### Configuration Management
Plugin-specific configuration:
- Default configuration values
- User override support
- Configuration validation
- Persistent storage

## Usage

### Creating a Custom Plugin

```python
# plugins/custom_analysis.py
import pandas as pd
from typing import Any, Dict
from unimelb_phd_phase_1.plugin_system import AnalysisPlugin

class CustomAnalysisPlugin(AnalysisPlugin):
    """Plugin for custom cost analysis functionality."""
    
    def __init__(self):
        super().__init__(
            name="custom_analysis",
            version="1.0.0",
            description="Custom cost analysis plugin for microcosting data",
            tags=["analysis", "custom"],
            dependencies=[]
        )
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform custom analysis on microcosting data.
        
        Args:
            data (pd.DataFrame): Microcosting data
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Data must be a pandas DataFrame")
        
        # Perform custom analysis
        results = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "numeric_columns": len(data.select_dtypes(include=['number']).columns),
            "memory_usage_mb": data.memory_usage(deep=True).sum() / 1024 / 1024
        }
        
        # Add custom calculations
        numeric_data = data.select_dtypes(include=['number'])
        if not numeric_data.empty:
            results["cost_statistics"] = {
                "mean_cost": numeric_data.mean().to_dict(),
                "median_cost": numeric_data.median().to_dict(),
                "std_cost": numeric_data.std().to_dict()
            }
        
        return results
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin with user-provided settings.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        super().configure(config)
        # Apply custom configuration
```

### Using Plugins

```python
from unimelb_phd_phase_1.enhanced_plugin_system import EnhancedPluginSystem
from unimelb_phd_phase_1.data_manager import DataManager

# Initialize components
plugin_system = EnhancedPluginSystem()
dm = DataManager()

# Load data
data = dm.load_sheet("Detailed Table")

# Discover and load plugins
plugin_system.discover_plugins()

# Get a specific plugin
plugin = plugin_system.get_plugin("custom_analysis")
if plugin:
    # Configure plugin if needed
    plugin.configure({"threshold": 1000})
    
    # Run analysis
    results = plugin.analyze(data)
    print(f"Analysis results: {results}")
    
    # Save results
    dm.save_sheet("Custom_Analysis_Results", pd.DataFrame([results]))
```

### Plugin Management Scripts

The system includes standardized scripts for plugin management:

```bash
# Demonstrate plugin system functionality
python scripts/demonstrate_plugins.py

# List available plugins
python scripts/demonstrate_plugins.py --list

# Run specific plugin
python scripts/demonstrate_plugins.py --plugin custom_analysis
```

## Plugin Types

### Analysis Plugins
Plugins that perform data analysis:

```python
class AnalysisPlugin(Plugin):
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform analysis on data."""
        pass
```

### Visualization Plugins
Plugins that generate visualizations:

```python
class VisualizationPlugin(Plugin):
    def visualize(self, data: pd.DataFrame) -> Any:
        """Generate visualization from data."""
        pass
```

### Export Plugins
Plugins that export data in specific formats:

```python
class ExportPlugin(Plugin):
    def export(self, data: pd.DataFrame, filepath: str) -> None:
        """Export data to specific format."""
        pass
```

### Validation Plugins
Plugins that validate data quality:

```python
class ValidationPlugin(Plugin):
    def validate(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data quality."""
        pass
```

## Plugin Configuration

### Default Configuration
Plugins can define default configuration values:

```python
class ConfigurablePlugin(AnalysisPlugin):
    def __init__(self):
        super().__init__(
            name="configurable_analysis",
            version="1.0.0",
            description="Configurable analysis plugin"
        )
        
        # Define default configuration
        self.default_config = {
            "threshold": 100,
            "include_statistics": True,
            "output_format": "json"
        }
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure plugin with user settings."""
        super().configure(config)
        
        # Apply configuration with defaults
        self.threshold = config.get("threshold", self.default_config["threshold"])
        self.include_statistics = config.get("include_statistics", 
                                           self.default_config["include_statistics"])
        self.output_format = config.get("output_format", 
                                      self.default_config["output_format"])
```

### User Configuration
Users can provide custom configuration:

```python
# User configuration
user_config = {
    "threshold": 500,
    "include_statistics": False,
    "output_format": "csv"
}

# Apply configuration
plugin.configure(user_config)
```

## Plugin Dependencies

### Defining Dependencies
Plugins can declare dependencies:

```python
class DependentPlugin(AnalysisPlugin):
    def __init__(self):
        super().__init__(
            name="dependent_analysis",
            version="1.0.0",
            description="Plugin with dependencies",
            dependencies=[
                {"name": "custom_analysis", "version": ">=1.0.0"},
                {"name": "statistical_tools", "version": ">=2.1.0"}
            ]
        )
```

### Dependency Resolution
The plugin system handles dependency resolution:

```python
# Check dependencies
missing_deps = plugin_system.check_dependencies(plugin)
if missing_deps:
    print(f"Missing dependencies: {missing_deps}")
else:
    print("All dependencies satisfied")
```

## Plugin Tags and Categories

### Tag-based Filtering
Plugins can be organized by tags:

```python
# List plugins by tag
analysis_plugins = plugin_system.list_plugins_by_tag("analysis")
visualization_plugins = plugin_system.list_plugins_by_tag("visualization")

# List plugins by category
plugins = plugin_system.list_plugins_by_category("cost_analysis")
```

### Custom Categories
Plugins can define custom categories:

```python
class CategorizedPlugin(AnalysisPlugin):
    def __init__(self):
        super().__init__(
            name="categorized_analysis",
            version="1.0.0",
            description="Categorized analysis plugin",
            tags=["analysis", "cost", "detailed"],
            categories=["cost_analysis", "microcosting"]
        )
```

## Performance Considerations

### Plugin Loading
- Lazy loading of plugins to reduce startup time
- Caching of plugin metadata
- Parallel discovery of plugins

### Memory Management
- Efficient plugin instance management
- Garbage collection of unused plugins
- Memory usage monitoring

### Execution Optimization
- Batch processing of plugin operations
- Caching of plugin results
- Progress tracking for long-running plugins

## Extensibility

### Adding New Plugin Types
To add support for new plugin types:

1. Create a new base class extending `AnalysisPlugin`
2. Implement the required methods
3. Register the new plugin type
4. Add validation logic if needed

### Custom Plugin Managers
Custom plugin managers can be implemented:

```python
class CustomPluginManager(PluginManager):
    def load_plugin(self, plugin_path: str) -> Plugin:
        """Custom plugin loading logic."""
        # Implement custom loading
        pass
```

## Integration with Other Components

### Data Management
The plugin system integrates with the data management system:
- Plugins receive standardized data inputs
- Plugin results are saved in consistent formats
- Metadata is generated for plugin outputs

### Scenario Analysis
Plugins can be used in scenario analysis:
- Custom analysis plugins for scenario evaluation
- Visualization plugins for scenario results
- Export plugins for scenario reporting

### Reporting System
Support for the reporting system:
- Plugin results can be included in reports
- Custom export formats through export plugins
- Visualization integration

## Testing

The plugin system includes comprehensive tests covering:
- Plugin loading and discovery
- Metadata handling
- Dependency management
- Configuration processing
- Plugin execution

Run tests with:
```bash
python -m pytest tests/test_plugin_system.py
```

## API Reference

### EnhancedPluginSystem Class

#### `__init__(plugin_directories=None)`
Initialize the EnhancedPluginSystem.

**Parameters:**
- `plugin_directories` (List[str], optional): Directories to search for plugins

#### `discover_plugins()`
Discover and load available plugins.

#### `list_plugins()`
List all available plugins.

**Returns:**
- List of plugin instances

#### `get_plugin(plugin_name)`
Get a specific plugin by name.

**Parameters:**
- `plugin_name` (str): Name of the plugin

**Returns:**
- Plugin instance or None if not found

#### `list_plugins_by_tag(tag)`
List plugins filtered by tag.

**Parameters:**
- `tag` (str): Tag to filter by

**Returns:**
- List of plugin instances

#### `check_dependencies(plugin)`
Check if all dependencies for a plugin are satisfied.

**Parameters:**
- `plugin` (Plugin): Plugin to check

**Returns:**
- List of missing dependencies

### AnalysisPlugin Class

#### `__init__(name, version, description, tags=None, dependencies=None, categories=None)`
Initialize the AnalysisPlugin.

**Parameters:**
- `name` (str): Plugin name
- `version` (str): Plugin version
- `description` (str): Plugin description
- `tags` (List[str], optional): Plugin tags
- `dependencies` (List[Dict], optional): Plugin dependencies
- `categories` (List[str], optional): Plugin categories

#### `analyze(data)`
Perform analysis on data.

**Parameters:**
- `data` (pd.DataFrame): Input data

**Returns:**
- Analysis results

#### `configure(config)`
Configure the plugin with user settings.

**Parameters:**
- `config` (Dict[str, Any]): Configuration dictionary