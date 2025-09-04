# Configuration Module Documentation

The configuration module provides utilities for loading and managing the YAML configuration file that defines the project settings.

## Overview

The config module is responsible for loading the [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml) file that contains all the project configuration settings. This includes workbook paths, sheet definitions, and other project-level settings.

## Key Features

### Flexible Configuration Loading
The module supports multiple configuration file locations for backward compatibility:

1. Repository root: `config.yaml`
2. Source directory: `src/config.yaml` (legacy support)

### YAML Parsing
The module uses PyYAML to parse the configuration file and provides error handling for common issues.

### Type Safety
The module includes proper type hints for better code reliability.

## Usage

### Basic Usage

```python
from unimelb_phd_phase_1.config import load_config

# Load configuration with default settings
config = load_config()

# Access configuration values
workbook_path = config["workbooks"]["main"]["path"]
sheet_names = list(config["workbooks"]["main"]["sheets"].keys())
```

### Custom Configuration Path

```python
from unimelb_phd_phase_1.config import load_config

# Load configuration from a specific path
config = load_config("/path/to/custom/config.yaml")
```

## API Reference

### load_config

```python
def load_config(config_path: str | Path | None = None) -> dict
```

Load the YAML configuration file.

**Parameters:**
- `config_path` (str | Path | None, optional): Path to the configuration file. If None, tries default locations.

**Returns:**
- `dict`: The loaded configuration data.

**Raises:**
- `FileNotFoundError`: If the configuration file cannot be found.
- `ValueError`: If there is an error parsing the YAML file.

## Configuration File Structure

The configuration file follows this structure:

```yaml
default_workbook: main
workbooks:
  main:
    path: "data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx"
    sheets:
      "Detailed Table":
        header_rows: 4
        data_starts_at: 5
        string_columns: ["Test", "Category", "Sub-Category", "Step"]
      "2. Labor Prices":
        header_rows: 1
        data_starts_at: 2
      "3. Estimates":
        header_rows: 1
        data_starts_at: 2
```

## Error Handling

The module provides comprehensive error handling:

1. **File Not Found**: Raises `FileNotFoundError` if the configuration file cannot be located
2. **YAML Parsing Errors**: Raises `ValueError` with detailed information if the YAML file is malformed

## Testing

The configuration module is tested to ensure:
- Correct loading from default locations
- Proper error handling for missing files
- Accurate parsing of YAML content
- Backward compatibility with legacy paths