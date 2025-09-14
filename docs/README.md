# Microcosting Genomics Analysis Toolkit - Documentation

This documentation provides comprehensive information about the `unimelb-phd-phase_1` Python library, which is designed to reverse-engineer and replicate a complex Excel-based microcosting model for rare disease genomics research.

## Table of Contents

1. [Quick Start Guide](../QUICK_START.md) - Get up and running in under 10 minutes
2. [Project Overview](../README.md) - Main project documentation
3. [Repository Structure](REPOSITORY_STRUCTURE.md) - Detailed repository organization
4. [Development Guide](DEVELOPMENT_GUIDE.md) - Guide for developers
5. [API Reference](API_REFERENCE.md) - Detailed API documentation
6. [Calculation Engine](CALCULATION_ENGINE.md) - Core calculation logic and formula parsing
7. [Data Management](DATA_MANAGEMENT.md) - Unified data handling and preparation
8. [Data Manager](DATA_MANAGER.md) - Data manager implementation details
9. [Configuration](CONFIG.md) - Configuration management
10. [Scenario Analysis](SCENARIO_ANALYSIS.md) - Deterministic and probabilistic sensitivity analysis
11. [Plugin System](PLUGIN_SYSTEM.md) - Extensible plugin architecture
12. [Models](MODELS.md) - Microcosting model descriptions
13. [Table Overview](table_overview.md) - Detailed workbook table descriptions

## Core Modules

The library is organized into the following core modules:

### Calculation and Data Processing
- **`calculation_engine.py`**: Contains the `CalculationEngine` class, which is responsible for parsing and executing Excel formulas.
- **`sheet_manager.py`**: Contains the `SheetManager` class, which handles loading and managing data from Excel sheets and Parquet files.
- **`data_manager.py`**: Provides unified data management with consistent handling across all sheet types.
- **`formula_parser.py`**: Provides functions for parsing Excel formulas into a structured format.
- **`strategies.py`**: Implements the Strategy pattern for different types of Excel formulas (e.g., `SUM`, `IF`, `VLOOKUP`).

### Analysis and Modeling
- **`advanced_scenario_modeling.py`**: Advanced deterministic and probabilistic sensitivity analysis capabilities.
- **`advanced_visualization.py`**: Enhanced visualization tools with interactive Plotly charts.
- **`performance.py`**: Performance profiling and optimization tools.
- **`data_management.py`**: Additional data management utilities.

### System and Utilities
- **`config.py`**: Loads and manages the configuration from the `config.yaml` file.
- **`utils.py`**: Contains utility functions used throughout the library.
- **`logging_config.py`**: Centralized logging configuration.
- **`excel_utils.py`**: Excel file handling utilities.
- **`excel_version_control.py`**: Version control system for Excel workbooks.

### Plugin System
- **`plugin_system.py`**: Base plugin system implementation.
- **`enhanced_plugin_system.py`**: Enhanced plugin system with metadata and configuration support.
- **`plugins/`**: Directory containing example plugins.

### Web Interface
- **`web.py`**: Main web application for data exploration.
- **`web_viz.py`**: Web-based visualization utilities.
- **`templates/`**: HTML templates for the web interface.
- **`static/`**: CSS, JavaScript, and other static assets.

## Usage Patterns

### Basic Usage

To use the library, first create an instance of the `SheetManager` class, pointing it to the Excel workbook you want to analyze. Then, create an instance of the `CalculationEngine`, passing the `SheetManager` instance to it. You can then use the `run_engine` method of the `CalculationEngine` to execute the formulas on a specific sheet.

```python
from src.genomics_microcosting.sheet_manager import SheetManager
from src.genomics_microcosting.calculation_engine import CalculationEngine

# Create a SheetManager to handle data loading
sheet_manager = SheetManager("path/to/your/workbook.xlsx")

# Create a CalculationEngine with the SheetManager
engine = CalculationEngine(sheet_manager)

# Run the engine on a specific sheet
results_df, errors = engine.run_engine("Detailed Table")

# View the results
print(results_df)
```

### Data Management

The unified data management system provides consistent handling of all sheets:

```python
from src.genomics_microcosting.data_manager import DataManager

# Initialize data manager
dm = DataManager()

# Load any sheet
df = dm.load_sheet("Detailed Table")

# Save in multiple formats
dm.save_sheet("Detailed Table", df, formats=["parquet", "csv"])

# Save for publication
dm.save_for_publication("Detailed Table", df, metadata={"version": "1.0"})
```

### Scenario Analysis

Perform sensitivity analyses using the advanced scenario modeling:

```python
from src.genomics_microcosting.advanced_scenario_modeling import AdvancedScenarioAnalyzer

# Initialize analyzer
analyzer = AdvancedScenarioAnalyzer()

# Perform deterministic sensitivity analysis
dsa_results = analyzer.perform_deterministic_analysis(
    baseline_data=baseline_df,
    parameters=dsa_parameters
)

# Perform probabilistic sensitivity analysis
psa_results = analyzer.perform_probabilistic_analysis(
    baseline_data=baseline_df,
    parameters=psa_parameters,
    simulation_count=1000
)
```

### Plugin System

Extend functionality using the plugin system:

```python
from src.genomics_microcosting.enhanced_plugin_system import EnhancedPluginSystem

# Initialize plugin system
plugin_system = EnhancedPluginSystem()

# Discover and load plugins
plugin_system.discover_plugins()

# Use a specific plugin
plugin = plugin_system.get_plugin("custom_analysis")
if plugin:
    results = plugin.analyze(data)
```

## Development Guidelines

### Code Structure
- Follow PEP8 style guide
- Use type hints where possible
- Write comprehensive docstrings for all public functions and classes
- Include unit tests for new functionality

### Testing
- Run `pytest` to execute the test suite
- Use `pre-commit` hooks to ensure code quality
- Write tests for new features and bug fixes

### Documentation
- Update relevant documentation when adding new features
- Write clear docstrings for all public APIs
- Include usage examples in documentation

## Contributing

Contributions to the microcosting analysis toolkit are welcome. Please follow these steps:

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes
4. Add tests for your changes
5. Update documentation as needed
6. Run the test suite to ensure everything works
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.