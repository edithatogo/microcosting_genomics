# Input Validation Procedures for Genomics Microcosting Analysis

## Overview

This document describes the input validation procedures implemented in the genomics microcosting project. The system provides comprehensive input validation capabilities to ensure data integrity and prevent errors throughout the analysis pipeline.

## Input Validation Architecture

The input validation system consists of several key components:

1. **InputValidator** - Main validation class with methods for different types of validation
2. **ValidationError** - Custom exception for validation errors
3. **Predefined Validators** - Specialized validators for common use cases
4. **Integration Points** - Where validation is applied throughout the system

## Validation Types

### Sheet Name Validation
Validates Excel sheet names according to Excel restrictions:
- Must be a string
- Cannot be empty
- Maximum 255 characters
- Cannot contain invalid characters: `\`, `/`, `*`, `[`, `]`, `:`, `?`

```python
from unimelb_phd_phase_1.input_validation import InputValidator

validator = InputValidator()
validator.validate_sheet_name("Detailed Table")  # Valid
```

### Cell Reference Validation
Validates Excel cell references:
- Must follow Excel format (e.g., "A1", "BZ999")
- Column range: A to XFD (1 to 16384)
- Row range: 1 to 1048576

```python
validator.validate_cell_reference("A1")      # Valid
validator.validate_cell_reference("XFD1048576")  # Valid (maximum values)
```

### DataFrame Validation
Validates pandas DataFrames:
- Correct type (pandas.DataFrame)
- Expected columns presence
- Row count constraints
- Data quality checks (excessive null values)

```python
import pandas as pd
df = pd.DataFrame({'Test': ['Panel'], 'Cost': [50000]})

validator.validate_dataframe(
    df, 
    expected_columns=['Test', 'Cost'],
    min_rows=1,
    max_rows=1000
)
```

### Numeric Value Validation
Validates numeric values with range checking:
- Correct type (int, float, numpy equivalents)
- Minimum and maximum value constraints
- Special value handling (NaN, infinity)

```python
# Validate cost value (non-negative)
validator.validate_numeric_value(50000, min_value=0)

# Validate percentage (0-100)
validator.validate_numeric_value(75.5, min_value=0, max_value=100)
```

### String Value Validation
Validates string values with length and pattern checking:
- Maximum length constraints
- Regular expression pattern matching
- Empty string handling

```python
# Validate string with maximum length
validator.validate_string_value("test string", max_length=50)

# Validate string with pattern (e.g., digits only)
validator.validate_string_value("12345", pattern=r'^\d+$')
```

### File Path Validation
Validates file paths:
- Correct type (string or Path)
- File existence checking
- Extension validation
- Invalid character checking

```python
from pathlib import Path

validator.validate_file_path(
    "./data/input.xlsx",
    must_exist=True,
    allowed_extensions=['.xlsx', '.xls']
)
```

### Configuration Validation
Validates configuration dictionaries:
- Correct structure
- Required key presence
- Value type checking
- Nested validation

```python
config = {
    "workbooks": {
        "main": {
            "path": "data/file.xlsx",
            "sheets": {
                "Detailed Table": {
                    "header_rows": 4,
                    "data_starts_at": 5
                }
            }
        }
    }
}

validator.validate_configuration(config, required_keys=["workbooks"])
```

## Predefined Validators

The system includes specialized validators for common use cases:

### Cost Value Validator
Validates non-negative numeric values for cost data:

```python
from unimelb_phd_phase_1.input_validation import validate_cost_value

validate_cost_value(50000)    # Valid
validate_cost_value(0)        # Valid
validate_cost_value(-5)       # Raises ValidationError
```

### Percentage Validator
Validates percentage values (0-100 range):

```python
from unimelb_phd_phase_1.input_validation import validate_percentage

validate_percentage(75.5)     # Valid
validate_percentage(0)        # Valid
validate_percentage(100)      # Valid
validate_percentage(105)      # Raises ValidationError
```

### Positive Integer Validator
Validates positive integer values:

```python
from unimelb_phd_phase_1.input_validation import validate_positive_integer

validate_positive_integer(5)      # Valid
validate_positive_integer("10")   # Valid (string conversion)
validate_positive_integer(0)      # Raises ValidationError
```

## Integration Examples

### Calculation Engine Integration
The calculation engine integrates input validation for sheet names and cell references:

```python
class CalculationEngine:
    def __init__(self, sheet_manager):
        self.validator = InputValidator()
        # ... other initialization ...
    
    def get_cell_value(self, sheet_name, cell_ref):
        # Validate inputs before processing
        try:
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_cell_reference(cell_ref)
        except ValidationError as e:
            self.logger.warning(f"Input validation failed: {e}")
            return None
        # ... rest of method ...
```

### Data Manager Integration
The data manager can use validation for file paths and configuration:

```python
class DataManager:
    def __init__(self):
        self.validator = InputValidator()
        # ... other initialization ...
    
    def load_sheet(self, sheet_name, format="parquet"):
        try:
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_string_value(
                format, 
                pattern=r'^(parquet|csv)$'
            )
        except ValidationError as e:
            self.logger.error(f"Invalid input: {e}")
            return None
        # ... rest of method ...
```

## Best Practices

### Validation Placement
- Validate inputs at entry points (APIs, user interfaces)
- Validate data before critical operations
- Validate configuration at startup
- Use appropriate validation levels (strict vs lenient)

### Error Handling
- Use ValidationError exceptions for consistent error handling
- Provide meaningful error messages
- Log validation failures for debugging
- Implement graceful degradation where appropriate

### Performance Considerations
- Cache validation results when appropriate
- Use efficient validation algorithms
- Avoid redundant validations
- Consider validation overhead in performance-critical paths

### Testing
- Test valid and invalid inputs for each validator
- Test edge cases and boundary conditions
- Test integration with error handling systems
- Include validation in automated test suites

## Extending Validation

### Custom Validators
Create custom validators by extending the InputValidator class:

```python
class CustomValidator(InputValidator):
    def validate_genomic_test_name(self, test_name: str) -> bool:
        """Validate genomic test name format."""
        self.validate_string_value(test_name, max_length=100)
        
        # Custom pattern for genomic test names
        pattern = r'^[A-Z0-9\s\-\(\)]+$'
        if not re.match(pattern, test_name):
            raise ValidationError(f"Invalid test name format: {test_name}")
        
        return True
```

### Validation Rules
Define validation rules as configuration:

```python
VALIDATION_RULES = {
    "cost_value": {
        "type": "numeric",
        "min_value": 0,
        "max_value": 1000000
    },
    "percentage": {
        "type": "numeric",
        "min_value": 0,
        "max_value": 100
    },
    "sheet_name": {
        "type": "string",
        "max_length": 255,
        "pattern": r'^[^\\\/\*\[\]:\?]$'
    }
}
```

## Troubleshooting

### Common Issues

1. **Validation Failures**
   - Check input data formats and types
   - Verify validation rule constraints
   - Review error messages for specific issues

2. **Performance Impact**
   - Profile validation code for bottlenecks
   - Consider caching for expensive validations
   - Optimize regular expressions

3. **Integration Problems**
   - Ensure validators are properly instantiated
   - Check error handling integration
   - Verify logging configuration

### Diagnostic Information
- Check application logs for validation error messages
- Use debug logging to trace validation execution
- Monitor validation metrics for performance impact