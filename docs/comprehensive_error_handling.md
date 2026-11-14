# Comprehensive Error Handling for Genomics Microcosting Analysis

## Overview

This document provides comprehensive documentation for the error handling system implemented in the genomics microcosting project. The system provides robust error handling with graceful degradation, detailed logging, checkpoint/restart capabilities, and comprehensive input validation.

## System Architecture

The error handling system consists of several integrated components:

1. **ErrorHandler** - Main error handling class with graceful degradation capabilities
2. **DetailedErrorLogger** - Enhanced logging with detailed tracing information
3. **CheckpointManager** - Checkpoint/restart functionality for long-running analyses
4. **InputValidator** - Comprehensive input validation for all system inputs
5. **DataDegradationStrategies** - Predefined strategies for common error scenarios

## ErrorHandler Class

The `ErrorHandler` class is the central component of the error handling system.

### Key Features
- Graceful degradation with fallback strategies
- Detailed error logging with tracing
- Checkpoint/restart capabilities
- Integration with input validation

### Initialization
```python
from unimelb_phd_phase_1.error_handling import setup_standard_error_handling

# Create error handler with optional checkpoint directory
error_handler = setup_standard_error_handling(
    logger=logger, checkpoint_dir="./checkpoints"
)
```

### Graceful Degradation Decorator
The `@graceful_degradation` decorator provides automatic error handling for functions:

```python
@error_handler.graceful_degradation(
    operation="load_data",
    default_value=[],
    data_source="input_data.xlsx",
    module="data_loader",
)
def load_data(file_path):
    """Load data that might fail."""
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File {file_path} not found")
    return ["data1", "data2", "data3"]
```

### Manual Error Handling
For complex error scenarios, manual error handling is available:

```python
try:
    result = risky_operation()
except Exception as e:
    context = ErrorContext(
        operation="risky_operation", data_source="input_data", module="data_processor"
    )
    error_info = error_handler.handle_error(e, context, ErrorSeverity.MEDIUM)
```

## Detailed Error Logging

The system provides enhanced error logging with detailed tracing information.

### Error Record Structure
Each detailed error record contains:
- **id**: Unique identifier
- **timestamp**: Unix timestamp
- **datetime**: ISO format datetime
- **operation**: Operation that failed
- **module**: Module where error occurred
- **data_source**: Data source involved
- **error_type**: Type of exception
- **error_message**: Human-readable message
- **severity**: Error severity level
- **parameters**: Operation parameters
- **traceback**: Full stack trace
- **frame_info**: Code frame information
- **resolved**: Resolution status
- **recovery_attempts**: Recovery attempts count

### Logging by Severity
Errors are logged at different levels:
- **Critical**: System-level errors
- **High**: Serious errors affecting results
- **Medium**: Warnings requiring attention
- **Low**: Informational messages

## Checkpoint/Restart Capabilities

The system provides robust checkpoint/restart functionality for long-running analyses.

### Creating Checkpoints
```python
# Create checkpoint with data and metadata
checkpoint_id = error_handler.create_checkpoint(
    "analysis_step_1",
    analysis_data,
    {"step": "initial_processing", "status": "completed"},
)
```

### Restoring Checkpoints
```python
# Restore from memory
restored_data = error_handler.restore_checkpoint(checkpoint_id)

# Restore from disk (persistent)
restored_data = error_handler.restore_checkpoint(checkpoint_id, from_disk=True)
```

### Persistent Checkpoints
Checkpoints can be stored persistently to disk for recovery after application restart:

```python
# Initialize with checkpoint directory
error_handler = setup_standard_error_handling(checkpoint_dir="./analysis_checkpoints")

# Create persistent checkpoint
checkpoint_id = error_handler.create_checkpoint("persistent_checkpoint", data)

# After restart, create new handler with same directory
new_handler = setup_standard_error_handling(checkpoint_dir="./analysis_checkpoints")

# Restore from persistent storage
restored_data = new_handler.restore_checkpoint(checkpoint_id, from_disk=True)
```

## Input Validation

The system includes comprehensive input validation for all system inputs.

### Validation Types
- **Sheet Name Validation**: Excel sheet name format validation
- **Cell Reference Validation**: Excel cell reference format validation
- **DataFrame Validation**: pandas DataFrame structure validation
- **Numeric Value Validation**: Numeric value range validation
- **String Value Validation**: String length and pattern validation
- **File Path Validation**: File path and extension validation
- **Configuration Validation**: Configuration structure validation

### Usage Examples
```python
from unimelb_phd_phase_1.input_validation import InputValidator

validator = InputValidator()

# Validate sheet name
validator.validate_sheet_name("Detailed Table")

# Validate cell reference
validator.validate_cell_reference("A1")

# Validate DataFrame
validator.validate_dataframe(df, expected_columns=["Test", "Cost"])

# Validate numeric value
validator.validate_numeric_value(50000, min_value=0)

# Validate string value
validator.validate_string_value("test", max_length=100)

# Validate file path
validator.validate_file_path("./data/input.xlsx", must_exist=True)
```

### Predefined Validators
Specialized validators for common use cases:
- **validate_cost_value**: Non-negative cost validation
- **validate_percentage**: 0-100 percentage validation
- **validate_positive_integer**: Positive integer validation

## Data Degradation Strategies

The system includes predefined strategies for common error scenarios:

### Missing Sheet Strategy
Handles missing Excel sheets by using default values.

### Missing Cell Strategy
Handles missing cells by using zero values.

### Formula Error Strategy
Handles formula errors by skipping calculations.

### Custom Strategies
Custom degradation strategies can be registered:

```python
def custom_degradation_strategy(error, context):
    """Custom degradation strategy."""
    return {
        "action": "custom_recovery",
        "default_value": None,
        "message": f"Custom recovery for {error}",
    }


error_handler.register_degradation_strategy("CustomError", custom_degradation_strategy)
```

## Error Recovery Scenarios

The system handles various error recovery scenarios:

### Missing Data Sources
Graceful degradation with default values or alternative data sources.

### Invalid Inputs
Input validation with graceful error handling.

### Calculation Errors
Recovery from mathematical errors (division by zero, etc.).

### Resource Exhaustion
Recovery from memory or other resource limitations.

### Data Quality Issues
Handling of data anomalies and inconsistencies.

### Nested Errors
Recovery from errors in nested function calls.

## Integration Examples

### Calculation Engine Integration
```python
class CalculationEngine:
    def __init__(self, sheet_manager):
        self.error_handler = setup_standard_error_handling()
        self.validator = InputValidator()

    def get_cell_value(self, sheet_name, cell_ref):
        """Get cell value with error handling."""

        @self.error_handler.graceful_degradation(
            operation="get_cell_value", default_value=None, data_source="sheet_data"
        )
        def _get_cell_value(sheet_name, cell_ref):
            # Validate inputs
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_cell_reference(cell_ref)

            # Process data
            # ... implementation ...

        return _get_cell_value(sheet_name, cell_ref)
```

### Data Manager Integration
```python
class DataManager:
    def __init__(self):
        self.validator = InputValidator()

    def load_sheet(self, sheet_name, format="parquet"):
        """Load sheet with validation."""
        try:
            self.validator.validate_sheet_name(sheet_name)
            self.validator.validate_string_value(format, pattern=r"^(parquet|csv)$")
        except ValidationError as e:
            logger.error(f"Invalid input: {e}")
            return None
        # ... rest of implementation ...
```

## Best Practices

### Error Handling Strategy
1. **Use Decorators for Common Cases** - Apply `@graceful_degradation` for standard error handling
2. **Manual Handling for Complex Cases** - Use manual error handling for complex recovery scenarios
3. **Checkpoint Frequently** - Create checkpoints at major analysis milestones
4. **Validate Early** - Validate inputs as early as possible to prevent errors
5. **Log Everything** - Maintain detailed logs for debugging and monitoring

### Recovery Planning
1. **Identify Critical Points** - Determine where errors are most likely to occur
2. **Plan Recovery Paths** - Define how to recover from each type of error
3. **Test Recovery Scenarios** - Regularly test error recovery procedures
4. **Monitor Error Patterns** - Track common errors to improve recovery strategies
5. **Document Recovery Procedures** - Maintain clear documentation of recovery processes

## Testing and Validation

The system includes comprehensive tests for all error handling components:

### Test Coverage
- Detailed error logging
- Checkpoint/restart capabilities
- Input validation
- Error recovery scenarios
- Graceful degradation

### Running Tests
```bash
# Run error handling tests
python -m pytest tests/test_detailed_error_logging.py -v
python -m pytest tests/test_checkpoint_restart.py -v
python -m pytest tests/test_input_validation.py -v
python -m pytest tests/test_error_recovery_scenarios.py -v
```

## Monitoring and Alerting

### Error Metrics
- Error frequency by type
- Recovery success rates
- Checkpoint creation and restoration rates
- Resource usage during error handling

### Alerting
- Critical errors that cannot be recovered
- High-frequency error patterns
- Resource exhaustion events
- Checkpoint failure events

## Troubleshooting

### Common Issues

1. **Recovery Failures**
   - Check checkpoint integrity
   - Verify error handling configuration
   - Review recovery logic

2. **Performance Impact**
   - Profile error handling code
   - Optimize checkpoint creation
   - Review validation overhead

3. **Data Consistency**
   - Verify checkpoint data integrity
   - Check error recovery completeness
   - Monitor data quality metrics

### Diagnostic Information
- Check detailed error logs
- Review checkpoint metadata
- Monitor recovery success rates
- Analyze error patterns and trends

## Conclusion

The comprehensive error handling system provides robust protection against various error scenarios while maintaining system availability and data integrity. The system's modular design allows for easy extension and customization to meet specific project requirements.