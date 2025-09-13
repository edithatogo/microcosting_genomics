# Data Quality Assurance Procedures

## Overview

This document outlines the procedures for implementing and using the Data Quality Assurance system in the Genomics Microcosting Project. The system provides comprehensive data validation capabilities including automated anomaly detection, cross-sheet consistency validation, missing data handling strategies, and data integrity verification.

## System Components

### 1. DataQualityAssurance Class

The main orchestrator class that coordinates all data quality assurance activities.

#### Key Methods:
- `assess_data_quality()`: Performs comprehensive quality assessment on a sheet
- `generate_quality_report()`: Generates a detailed quality report
- `get_quality_metrics_summary()`: Provides summary statistics

### 2. DataAnomalyDetector Class

Detects anomalies in cost data and other metrics.

#### Key Methods:
- `detect_cost_anomalies()`: Identifies statistical outliers and negative costs
- `detect_pattern_anomalies()`: Finds suspicious data patterns

### 3. MissingDataHandler Class

Analyzes missing data patterns and suggests handling strategies.

#### Key Methods:
- `analyze_missing_data_patterns()`: Identifies missing data patterns
- `suggest_missing_data_strategies()`: Recommends handling approaches

### 4. DataIntegrityVerifier Class

Verifies data integrity through various checks.

#### Key Methods:
- `verify_cost_integrity()`: Validates cost data integrity
- `verify_cross_sheet_integrity()`: Ensures cross-sheet references are valid

## Implementation Procedures

### 1. Automated Data Anomaly Detection

The system automatically detects anomalies in cost-related data through:

1. **Statistical Outlier Detection**: Uses Z-score analysis to identify values more than 3 standard deviations from the mean
2. **Negative Cost Detection**: Flags negative cost values which typically indicate data entry errors
3. **Zero Value Analysis**: Identifies unusually high percentages of zero values
4. **Pattern Anomaly Detection**: Finds suspicious repeated characters and inconsistent data types

#### Implementation Example:
```python
from unimelb_phd_phase_1.data_quality_assurance import DataAnomalyDetector
import pandas as pd

# Create detector
detector = DataAnomalyDetector()

# Create test data with anomalies
df = pd.DataFrame({
    'cost': [100, 200, 300, 400, 50000],  # Last value is an outlier
    'other_cost': [50, 60, 70, 80, -10]   # Negative value
})

# Detect anomalies
anomalies = detector.detect_cost_anomalies(df, ['cost', 'other_cost'])
print(f"Detected {len(anomalies)} anomalies")
```

### 2. Cross-Sheet Consistency Validation

Ensures data consistency across related sheets by validating cross-sheet references.

#### Implementation Example:
```python
from unimelb_phd_phase_1.data_quality_assurance import DataIntegrityVerifier
from unimelb_phd_phase_1.data_manager import DataManager

# Create verifier
verifier = DataIntegrityVerifier()
data_manager = DataManager()

# Define sheet dependencies
sheet_dependencies = {
    "Main Analysis": ["Labor Prices", "Equipment Costs"],
    "Sensitivity Analysis": ["Main Analysis", "Scenario Parameters"]
}

# Verify cross-sheet integrity
violations = verifier.verify_cross_sheet_integrity(data_manager, sheet_dependencies)
if violations:
    print(f"Found {len(violations)} integrity violations")
```

### 3. Missing Data Handling Strategies

Analyzes missing data patterns and provides appropriate handling recommendations:

1. **Low Missing Data (< 5%)**: Suggests dropping rows with missing values
2. **Moderate Missing Data (5-20%)**: Recommends imputation strategies
3. **High Missing Data (> 20%)**: Suggests advanced imputation techniques
4. **Completely Missing Columns**: Recommends reviewing column necessity

#### Implementation Example:
```python
from unimelb_phd_phase_1.data_quality_assurance import MissingDataHandler
import pandas as pd

# Create handler
handler = MissingDataHandler()

# Create test data with missing values
df = pd.DataFrame({
    'A': [1, 2, None, 4, 5],
    'B': [None, None, None, None, None],  # Completely missing
    'C': [1, 2, 3, 4, 5]
})

# Analyze missing data patterns
analysis = handler.analyze_missing_data_patterns(df)
print(f"Missing data percentage: {analysis['missing_percentage']:.2f}%")

# Get handling strategies
strategies = handler.suggest_missing_data_strategies(analysis)
for strategy in strategies:
    print(f"Strategy: {strategy['strategy']} - {strategy['description']}")
```

### 4. Data Integrity Verification

Verifies data integrity through multiple checks:

1. **Cost Value Validation**: Ensures cost values are non-negative and numeric
2. **Cross-Sheet Reference Validation**: Confirms referenced sheets exist
3. **Range Validation**: Checks that values fall within expected ranges
4. **Unique Constraint Validation**: Ensures specified columns maintain uniqueness

#### Implementation Example:
```python
from unimelb_phd_phase_1.data_quality_assurance import DataIntegrityVerifier
import pandas as pd

# Create verifier
verifier = DataIntegrityVerifier()

# Create test data with integrity issues
df = pd.DataFrame({
    'cost': [100, 200, -50, 400, 'invalid'],  # Negative and non-numeric values
    'id': [1, 2, 3, 3, 5]  # Duplicate ID
})

# Verify cost integrity
violations = verifier.verify_cost_integrity(df, ['cost'])
print(f"Found {len(violations)} cost integrity violations")

# Verify unique constraints
# This would typically be done through the DataConsistencyValidator
```

## Data Quality Metrics

The system tracks several key metrics to assess data quality:

1. **Null Percentage**: Percentage of missing values in the dataset
2. **Duplicate Rows**: Number of duplicate rows detected
3. **Anomalies Detected**: Count of various data anomalies
4. **Consistency Issues**: Cross-sheet consistency problems
5. **Integrity Violations**: Data integrity rule violations

## Quality Report Generation

The system can generate comprehensive data quality reports that include:

1. **Executive Summary**: Overview of data quality findings
2. **Detailed Results by Sheet**: Per-sheet analysis results
3. **Anomaly Details**: Specific anomalies detected
4. **Integrity Violations**: Data integrity issues found
5. **Missing Data Analysis**: Patterns in missing data
6. **Recommendations**: Suggestions for improving data quality

#### Implementation Example:
```python
from unimelb_phd_phase_1.data_quality_assurance import DataQualityAssurance
from unimelb_phd_phase_1.data_manager import DataManager

# Create quality assurance system
data_manager = DataManager()
qa_system = DataQualityAssurance(data_manager)

# Assess data quality for a sheet
metrics = qa_system.assess_data_quality(
    sheet_name="Detailed Table",
    cost_columns=['Total Cost', 'Labor Cost', 'Equipment Cost'],
    expected_ranges={'Total Cost': (0, 1000000)},
    unique_columns=['Test ID']
)

# Generate quality report
report = qa_system.generate_quality_report("data_quality_report.md")
print("Quality report generated successfully")

# Get summary metrics
summary = qa_system.get_quality_metrics_summary()
print(f"Analyzed {summary['total_sheets']} sheets")
print(f"Found {summary['total_anomalies']} anomalies")
```

## Best Practices

### 1. Regular Data Quality Monitoring
- Schedule regular data quality assessments
- Monitor key metrics over time
- Set up alerts for significant quality degradation

### 2. Proactive Anomaly Detection
- Run anomaly detection on new data before analysis
- Review statistical outliers to determine validity
- Address negative cost values immediately

### 3. Missing Data Management
- Identify missing data patterns early in the process
- Apply appropriate handling strategies based on missing data percentage
- Document decisions about handling missing data

### 4. Integrity Verification
- Validate cross-sheet references regularly
- Check data ranges against expected values
- Ensure unique constraints are maintained

## Integration with Other Systems

### Error Handling Integration
The data quality assurance system integrates with the error handling framework to provide graceful degradation when data quality issues are detected.

### Logging Integration
All data quality assessments are logged through the standard logging system for audit and debugging purposes.

### Configuration Integration
The system can be configured with expected data ranges and other quality parameters through the configuration system.

## Testing Procedures

### Unit Testing
Each component has comprehensive unit tests that verify functionality:

1. **DataAnomalyDetector Tests**: Verify anomaly detection accuracy
2. **MissingDataHandler Tests**: Confirm missing data analysis and strategy suggestions
3. **DataIntegrityVerifier Tests**: Validate integrity checking mechanisms
4. **DataQualityAssurance Tests**: Test overall coordination and reporting

### Integration Testing
Integration tests verify that the data quality assurance system works correctly with the data manager and other components.

## Troubleshooting

### Common Issues

1. **No Anomalies Detected**: Check that the data actually contains anomalies or adjust detection thresholds
2. **High Missing Data Percentage**: Review data collection processes and consider alternative handling strategies
3. **Cross-Sheet Reference Failures**: Verify that all referenced sheets exist and are properly named
4. **Performance Issues**: For very large datasets, consider sampling or optimizing detection algorithms

### Diagnostic Procedures

1. **Check Logs**: Review detailed logs for specific error messages
2. **Validate Inputs**: Ensure all input data is properly formatted
3. **Review Configuration**: Verify that expected ranges and other parameters are correctly set
4. **Test Components Individually**: Isolate issues by testing individual components

## Future Enhancements

### Planned Improvements
1. **Machine Learning-Based Anomaly Detection**: Implement more sophisticated anomaly detection algorithms
2. **Automated Data Cleaning**: Add capabilities for automatic data cleaning based on detected issues
3. **Real-Time Monitoring**: Implement real-time data quality monitoring for streaming data
4. **Advanced Visualization**: Add more sophisticated data quality dashboards

### Extensibility Points
1. **Custom Anomaly Detectors**: Allow for domain-specific anomaly detection algorithms
2. **Pluggable Strategy Handlers**: Enable custom missing data handling strategies
3. **Extended Integrity Checks**: Add more comprehensive integrity verification rules