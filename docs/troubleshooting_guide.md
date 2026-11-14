# Troubleshooting Guide

This guide provides solutions for common issues encountered when using the Genomics Microcosting Project.

## Table of Contents
1. [Data Preparation Issues](#data-preparation-issues)
2. [Analysis Execution Problems](#analysis-execution-problems)
3. [Validation Failures](#validation-failures)
4. [Performance Issues](#performance-issues)
5. [Security Problems](#security-problems)
6. [Web Interface Issues](#web-interface-issues)
7. [Configuration Problems](#configuration-problems)
8. [Installation Issues](#installation-issues)

## Data Preparation Issues

### Problem: "File not found" errors during data preparation

**Symptoms**: 
```
FileNotFoundError: [Errno 2] No such file or directory: 'path/to/workbook.xlsx'
```

**Causes**:
- Incorrect path in [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml)
- File permissions issues
- File is open in another application

**Solutions**:
1. Verify the file path in [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml) is correct and absolute
2. Check that the file exists and is readable
3. Close the Excel file in any other applications
4. Ensure the user has read permissions for the file

### Problem: "Sheet not found" errors

**Symptoms**:
```
KeyError: "Sheet 'Detailed Table' not found"
```

**Causes**:
- Sheet name misspelling in [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml)
- Sheet doesn't exist in the workbook
- Workbook is corrupted

**Solutions**:
1. Verify sheet names match exactly (including case sensitivity)
2. Open the Excel file and confirm sheet names
3. Try opening the workbook in Excel to check for corruption

### Problem: Data parsing errors

**Symptoms**:
```
ValueError: Cannot convert non-finite values (NA or inf) to integer
```

**Causes**:
- Non-numeric data in numeric columns
- Empty cells in required fields
- Special characters in data

**Solutions**:
1. Check the raw Excel data for non-numeric values in numeric columns
2. Use the data quality assurance tools to identify anomalies
3. Clean the data manually or adjust the parsing logic

## Analysis Execution Problems

### Problem: "No valid unit cost data found"

**Symptoms**:
```
No valid unit cost data found to perform analysis.
```

**Causes**:
- No "Unit Cost" columns found in the data
- All unit cost values are NaN or invalid
- Wrong sheet being processed

**Solutions**:
1. Verify that the "Detailed Table" contains "Unit Cost" columns
2. Check that unit cost values are numeric
3. Confirm the correct sheet is being processed in [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml)

### Problem: Analysis hangs or takes too long

**Symptoms**:
- Process appears to freeze
- High CPU usage for extended periods
- No output for minutes

**Causes**:
- Very large dataset
- Infinite loop in calculation engine
- Memory exhaustion

**Solutions**:
1. Monitor memory usage with the performance tools
2. Try with a smaller sample of data first
3. Check for circular references in formulas
4. Use the checkpoint/restart feature for long-running analyses

### Problem: "MemoryError" during analysis

**Symptoms**:
```
MemoryError: Unable to allocate X.YY GiB for an array with shape ...
```

**Causes**:
- Dataset too large for available memory
- Inefficient data structures
- Memory leak in code

**Solutions**:
1. Use the memory optimization features
2. Process data in chunks rather than loading everything at once
3. Convert data types to more memory-efficient formats
4. Increase available system memory or use a machine with more RAM

## Validation Failures

### Problem: Significant errors in validation

**Symptoms**:
```
Significant Errors (difference > 0.01):
   ground_truth  calculated  difference  percentage_error
0         10.50       10.45        0.05             0.48
```

**Causes**:
- Differences in calculation logic between versions
- Changes in input data
- Rounding errors in calculations
- Bugs in the calculation engine

**Solutions**:
1. Review recent code changes that might affect calculations
2. Verify that input data matches the ground truth version
3. Check for precision settings in calculations
4. Run unit tests to isolate the issue

### Problem: "No valid values to compare"

**Symptoms**:
```
No valid values to compare. This is expected if required sheets are not available.
```

**Causes**:
- Missing required sheets
- Data format mismatch between calculated and ground truth
- All values are NaN or invalid

**Solutions**:
1. Ensure all required sheets are available and properly formatted
2. Check that column names match between calculated results and ground truth
3. Verify data preparation was successful

## Performance Issues

### Problem: Slow data preparation

**Symptoms**:
- Data preparation takes hours to complete
- High disk I/O during processing
- Progress appears stalled

**Causes**:
- Very large Excel files
- Slow disk storage
- Inefficient parsing algorithms

**Solutions**:
1. Use SSD storage instead of HDD
2. Process files in parallel where possible
3. Optimize Excel file structure (remove unnecessary formatting)
4. Consider using more efficient file formats

### Problem: High memory usage

**Symptoms**:
- System becomes unresponsive
- Process is killed by OOM killer
- Swap usage is high

**Causes**:
- Loading entire datasets into memory
- Memory leaks in pandas operations
- Inefficient data structures

**Solutions**:
1. Use chunked processing for large datasets
2. Monitor memory usage with the built-in tools
3. Optimize data types (use appropriate int/float sizes)
4. Release unused dataframes from memory

## Security Problems

### Problem: "Permission denied" errors

**Symptoms**:
```
SecurityError: User researcher lacks permission: configure_system
```

**Causes**:
- User doesn't have required role
- Role doesn't have required permission
- User not properly authenticated

**Solutions**:
1. Check that user is assigned to appropriate role
2. Verify role has required permissions
3. Ensure user is properly authenticated

### Problem: Audit trail not working

**Symptoms**:
- No audit events are logged
- Audit file is not created
- Permission errors when writing audit logs

**Causes**:
- Incorrect log file path
- Insufficient file permissions
- Disk full

**Solutions**:
1. Verify audit log file path is correct and writable
2. Check file permissions for the log directory
3. Ensure sufficient disk space is available

### Problem: Configuration encryption issues

**Symptoms**:
- Unable to load encrypted configuration
- Decryption produces garbled data
- Encryption key mismatch

**Causes**:
- Wrong encryption key
- Corrupted configuration file
- Algorithm mismatch

**Solutions**:
1. Verify encryption key is correct
2. Recreate configuration file
3. Ensure consistent encryption/decryption algorithms

## Web Interface Issues

### Problem: "Connection refused" when accessing web interface

**Symptoms**:
- Browser shows "Unable to connect" error
- curl returns "Connection refused"
- Server process not running

**Causes**:
- Web server not started
- Port already in use
- Firewall blocking connection

**Solutions**:
1. Start the web server with `python -m unimelb_phd_phase_1.web`
2. Check if another process is using port 5000
3. Verify firewall settings allow connections

### Problem: Blank pages or missing data in web interface

**Symptoms**:
- Tables show no data
- Charts are empty
- Error messages in browser console

**Causes**:
- Required data files not available
- JavaScript errors
- API endpoints not working

**Solutions**:
1. Verify data preparation was successful
2. Check browser console for JavaScript errors
3. Test API endpoints directly with curl

### Problem: Slow web interface response

**Symptoms**:
- Pages take seconds to load
- Charts render slowly
- User interface feels unresponsive

**Causes**:
- Large datasets being loaded
- Inefficient database queries
- Network latency

**Solutions**:
1. Implement data pagination
2. Optimize database queries
3. Use caching for frequently accessed data

## Configuration Problems

### Problem: "KeyError" when loading configuration

**Symptoms**:
```
KeyError: 'workbooks'
```

**Causes**:
- Missing required configuration keys
- Malformed YAML syntax
- Wrong configuration file

**Solutions**:
1. Check [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml) for required keys
2. Validate YAML syntax (use online YAML validator)
3. Verify correct configuration file is being loaded

### Problem: Configuration values not taking effect

**Symptoms**:
- Changes to [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml) have no effect
- Default values are used instead of configured values
- Configuration appears to be ignored

**Causes**:
- Configuration file not being reloaded
- Caching of configuration values
- Wrong configuration file being used

**Solutions**:
1. Restart the application to reload configuration
2. Clear any configuration caches
3. Verify the correct configuration file path

## Installation Issues

### Problem: "Module not found" errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'genomics_microcosting'
```

**Causes**:
- Package not installed
- Incorrect Python environment
- Path issues

**Solutions**:
1. Install the package with `uv sync --locked --python 3.15.1`.
2. Confirm `.venv/bin/python --version` reports Python 3.15.1.
3. Run the command through the interpreter or entry point in `.venv/bin`.

### Problem: Dependency installation failures

**Symptoms**:
```
ERROR: Could not build wheels for scipy
```

**Causes**:
- Missing system dependencies
- Incompatible Python version
- Network issues

**Solutions**:
1. Install system dependencies (BLAS, LAPACK for scipy)
2. Use compatible Python version (3.8+)
3. Check network connectivity

### Problem: Version conflicts

**Symptoms**:
```
pkg_resources.ContextualVersionConflict
```

**Causes**:
- Incompatible package versions
- Multiple versions of same package
- Pinned dependency conflicts

**Solutions**:
1. Use a virtual environment
2. Update dependencies to compatible versions
3. Resolve version conflicts manually

## General Debugging Tips

### Enable Debug Logging

Set the logging level to DEBUG for more detailed information:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

### Run Unit Tests

Execute specific test suites to isolate issues:

```bash
python -m pytest tests/test_module.py::TestClass::test_method -v
```

### Check System Resources

Monitor system resources during execution:

```bash
# Monitor memory usage
watch -n 1 free -h

# Monitor CPU usage
top

# Monitor disk I/O
iostat -x 1
```

### Validate Data Quality

Use the data quality assurance tools to identify issues:

```bash
python -m unimelb_phd_phase_1.data_quality_assurance
```

## Getting Additional Help

If you're unable to resolve an issue using this guide:

1. Check the project documentation in the `docs/` directory
2. Search existing issues on the project repository
3. Run the unit tests to verify component functionality
4. Contact the development team with:
   - Detailed error messages
   - Steps to reproduce the issue
   - System information (OS, Python version, etc.)
   - Relevant log files
