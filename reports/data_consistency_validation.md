# Data Consistency Validation Report

## Executive Summary

This report presents the results of data consistency validation across all sheets.

## Validation Results by Sheet

### detailed_table

**Integrity Validation:**

- Passed: True

- Warnings: Found 777 duplicate rows

**Format Consistency Validation:**

- Passed: False

- Errors: Shape mismatch: Parquet (1313, 27) vs CSV (1339, 1301), Column names mismatch between formats



### process

**Integrity Validation:**

- Passed: True

- Warnings: High null percentage: 100.00%, Found 37 duplicate rows

**Format Consistency Validation:**

- Passed: False

- Errors: Column names mismatch between formats



### dsa__test_throughput

**Integrity Validation:**

- Passed: True

- Warnings: Found 38 duplicate rows

**Format Consistency Validation:**

- Passed: True

- Warnings: Data mismatch in column 'unnamed_32': 4/80 values differ, Data mismatch in column 'unnamed_1': 4/80 values differ, Data mismatch in column 'unnamed_24': 15/80 values differ



### detailed_table_values

**Integrity Validation:**

- Passed: True

- Warnings: Found 657 duplicate rows



### detailed_table_formulas

**Integrity Validation:**

- Passed: True

- Warnings: Found 416 duplicate rows, No numeric columns found



### ground_truth

**Integrity Validation:**

- Passed: True

- Warnings: Found 778 duplicate rows



### dsa__labour_prices

**Integrity Validation:**

- Passed: True

- Warnings: Found 39 duplicate rows

**Format Consistency Validation:**

- Passed: True

- Warnings: Data mismatch in column 'unnamed_32': 7/80 values differ, Data mismatch in column 'unnamed_34': 5/80 values differ, Data mismatch in column 'unnamed_42': 9/80 values differ



### sheet1

**Integrity Validation:**

- Passed: True

- Warnings: Found 19 duplicate rows

**Format Consistency Validation:**

- Passed: False

- Errors: Column names mismatch between formats



## Key Findings

- Data integrity validation ensures sheets are properly structured

- Format consistency validation ensures parquet and CSV formats match

- Cross-sheet reference validation ensures dependencies are maintained

- Range validation ensures data values fall within expected bounds

- Unique constraint validation ensures data integrity rules are followed
