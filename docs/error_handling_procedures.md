# Error Handling Procedures for Genomics Microcosting Analysis

## Overview

This document describes the error handling procedures implemented in the genomics microcosting project. The system provides comprehensive error handling with graceful degradation capabilities and detailed tracing for debugging and monitoring purposes.

## Error Handling Architecture

The error handling system consists of several key components:

1. **ErrorHandler** - Main error handling class that coordinates all error management activities
2. **DetailedErrorLogger** - Enhanced logging system with detailed tracing capabilities
3. **ErrorContext** - Context information container for errors
4. **ErrorSeverity** - Standardized severity levels for categorizing errors
5. **DataDegradationStrategies** - Predefined strategies for handling common data issues

## Detailed Error Logging

The enhanced error logging system captures comprehensive information about errors to facilitate debugging and monitoring:

### Error Record Structure

Each detailed error record contains the following information:

- **id**: Unique identifier for the error
- **timestamp**: Unix timestamp when the error occurred
- **datetime**: ISO format datetime string
- **operation**: Name of the operation that failed
- **module**: Module where the error occurred
- **data_source**: Data source involved in the error
- **error_type**: Type of exception (e.g., ValueError, FileNotFoundError)
- **error_message**: Human-readable error message
- **severity**: Error severity level (critical, high, medium, low)
- **parameters**: Operation parameters at the time of error
- **traceback**: Full stack trace of the error
- **frame_info**: Information about the code frame where the error occurred
- **resolved**: Whether the error has been resolved
- **recovery_attempts**: Number of recovery attempts made

### Logging by Severity

Errors are logged at different levels based on their severity:

- **Critical**: System-level errors that prevent continuation
- **High**: Serious errors that may affect results
- **Medium**: Warnings that should be investigated
- **Low**: Informational messages

## Graceful Degradation

The system implements graceful degradation strategies to continue operation when non-critical errors occur:

### Decorator Usage

```python
@error_handler.graceful_degradation(
    operation="data_loading",
    default_value=[],
    data_source="sample_data.csv",
    module="data_loader"
)
def load_data(file_path: str):
    """Load data that might fail."""
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File {file_path} not found")
    return ["data1", "data2", "data3"]
```

### Manual Error Handling

```python
try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    context = ErrorContext(
        operation="risky_operation",
        data_source="input_data",
        module="data_processor"
    )
    error_info = error_handler.handle_error(e, context, ErrorSeverity.MEDIUM)
```

## Standard Degradation Strategies

The system includes predefined strategies for common error scenarios:

1. **Missing Sheet Strategy** - Handle missing Excel sheets by using default values
2. **Missing Cell Strategy** - Handle missing cells by using zero values
3. **Formula Error Strategy** - Handle formula errors by skipping calculations

## Error Log Management

### Retrieving Error Logs

```python
# Get simple error log
simple_log = error_handler.get_error_log()

# Get detailed error log with tracing information
detailed_log = error_handler.get_detailed_error_log()
```

### Saving Error Logs

```python
# Save simple error log to file
error_handler.save_error_log("error_log.json")

# Save detailed error log to file
error_handler.save_detailed_error_log("detailed_error_log.json")
```

### Clearing Error Logs

```python
# Clear simple error log
error_handler.clear_error_log()

# Clear detailed error log
error_handler.clear_detailed_error_log()
```

## Checkpoint/Restart Capabilities

The system provides checkpoint/restart capabilities for long-running analyses:

### Creating Checkpoints

```python
# Create a checkpoint with data
error_handler.create_checkpoint("analysis_step_1", intermediate_data)
```

### Restoring Checkpoints

```python
# Restore data from a checkpoint
restored_data = error_handler.restore_checkpoint("analysis_step_1")
```

## Integration with Calculation Engine

The error handling system is integrated with the calculation engine to provide robust error management:

```python
class CalculationEngine:
    def __init__(self):
        self.error_handler = setup_standard_error_handling()
    
    @error_handler.graceful_degradation(
        operation="get_cell_value",
        default_value=0,
        data_source="excel_sheet",
        module="calculation_engine"
    )
    def get_cell_value(self, sheet_name: str, cell_address: str) -> float:
        """Get cell value with graceful degradation."""
        # Implementation that might fail
        pass
```

## Best Practices

1. **Always provide context** - Include operation name, data source, and module information
2. **Use appropriate severity levels** - Classify errors correctly for proper handling
3. **Implement fallback strategies** - Provide default values or alternative approaches
4. **Log detailed information** - Capture sufficient information for debugging
5. **Test error scenarios** - Verify that error handling works as expected
6. **Monitor error logs** - Regularly review error logs for patterns and issues

## Monitoring and Alerting

The detailed error logs can be used for monitoring system health and triggering alerts for critical issues. The structured format makes it easy to parse and analyze errors programmatically.