# Data Manager Documentation

The Data Manager provides a unified interface for loading, saving, and managing all data sheets in the microcosting analysis.

## Overview

The [data_manager.py](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/data_manager.py) module implements the `DataManager` class, which provides consistent data handling across all sheets regardless of their source or purpose. It ensures standardized processing, validation, and output formats throughout the toolkit.

## Key Features

### Unified Data Interface
The DataManager provides a single interface for all data operations:

```python
from unimelb_phd_phase_1.data_manager import DataManager

# Initialize data manager
dm = DataManager()

# Load any sheet
df = dm.load_sheet("Detailed Table")

# Save data in multiple formats
dm.save_sheet("Detailed Table", df, formats=["parquet", "csv"])
```

### Format Support
The system supports multiple data formats:
- **Parquet**: Efficient binary format for performance
- **CSV**: Human-readable format for accessibility

### Automatic Metadata Generation
Metadata is automatically generated for all sheets:
- Column information and data types
- Null value counts
- Memory usage statistics
- Data sample values

### Publication-Ready Outputs
The system generates publication-ready outputs:
- Standardized CSV files
- Data dictionaries
- Metadata files in JSON format

### Duplicate Column Handling
Automatic resolution of duplicate column names:
- MultiIndex column flattening
- Unique column name generation
- Data integrity preservation

## Usage

### Basic Data Management

```python
from unimelb_phd_phase_1.data_manager import DataManager

# Initialize data manager
dm = DataManager()

# List available sheets
sheets = dm.get_sheet_names()
print(f"Available sheets: {sheets}")

# Load a sheet
df = dm.load_sheet("Detailed Table")
if df is not None:
    print(f"Loaded shape: {df.shape}")

# Save a sheet in multiple formats
dm.save_sheet("Detailed Table", df, formats=["parquet", "csv"])
```

### Advanced Data Management

```python
# Save for publication
metadata = {
    "source": "Excel workbook",
    "processing_date": "2023-12-01",
    "version": "1.0",
}
dm.save_for_publication("Detailed Table", df, metadata)

# List all available sheets and formats
available_sheets = dm.list_available_sheets()
for sheet_name, formats in available_sheets.items():
    print(f"{sheet_name}: {', '.join(formats)}")
```

### Data Preparation Scripts

The system includes standardized scripts for data preparation:

```bash
# Prepare all sheets consistently
python scripts/prepare_all_sheets.py

# Validate all sheets
python scripts/validate_all_sheets.py
```

## API Reference

### DataManager Class

#### `__init__(data_dir: Optional[Path] = None)`
Initialize the DataManager.

**Parameters:**
- `data_dir` (Path, optional): Base data directory. If None, uses default location.

#### `get_sheet_names() -> List[str]`
Get list of all available sheet names from configuration.

**Returns:**
- `List[str]`: List of sheet names configured for processing

#### `load_sheet(sheet_name: str, format: str = "parquet") -> Optional[pd.DataFrame]`
Load a specific sheet in the specified format.

**Parameters:**
- `sheet_name` (str): Name of the sheet to load
- `format` (str, optional): Format to load ('parquet' or 'csv'). Defaults to 'parquet'.

**Returns:**
- `Optional[pd.DataFrame]`: DataFrame containing the sheet data, or None if not found

#### `save_sheet(sheet_name: str, df: pd.DataFrame, formats: Optional[List[str]] = None) -> bool`
Save a sheet in specified formats with consistent naming.

**Parameters:**
- `sheet_name` (str): Name of the sheet to save
- `df` (pd.DataFrame): DataFrame containing the sheet data
- `formats` (List[str], optional): Formats to save ('parquet', 'csv'). If None, saves in all supported formats.

**Returns:**
- `bool`: True if successfully saved, False otherwise

#### `save_for_publication(sheet_name: str, df: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> bool`
Save a sheet and its metadata for publication with consistent formatting.

**Parameters:**
- `sheet_name` (str): Name of the sheet to save
- `df` (pd.DataFrame): DataFrame containing the sheet data
- `metadata` (Dict[str, Any], optional): Metadata about the sheet

**Returns:**
- `bool`: True if successfully saved, False otherwise

## Data Validation

### Integrity Checks
Built-in validation for data integrity:
- Null value percentage monitoring
- Duplicate row detection
- Data type consistency
- Size limit warnings

### Format Consistency
Validation between different formats:
- Cross-format data equivalence
- Column name consistency
- Value accuracy preservation

### Cross-Reference Validation
Validation of inter-sheet references:
- Formula parsing for cross-sheet references
- Reference resolution verification
- Error reporting for broken links

## Performance Considerations

### Memory Efficiency
- Lazy loading of data when possible
- Efficient DataFrame operations
- Memory usage monitoring

### Processing Speed
- Batch operations for multiple sheets
- Parallel processing capabilities
- Caching of frequently accessed data

### Storage Optimization
- Parquet format for efficient storage
- Compression where appropriate
- Standardized naming conventions

## Integration with Other Components

### Calculation Engine
The data management system integrates with the calculation engine:
- Provides data for formula execution
- Stores calculation results
- Manages ground truth datasets

### Visualization Tools
Data is prepared for visualization:
- Cleaned data formats
- Metadata for chart labeling
- Sample data for previews

### Reporting System
The system supports the reporting system:
- Data export in multiple formats
- Metadata for report generation
- Validation results for quality assurance

## Testing

The data management system includes comprehensive tests covering:
- Data loading and saving operations
- Format conversion accuracy
- Error handling for missing files
- Metadata generation correctness
- Publication output validation