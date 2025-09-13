# Model Transformation Report
Generated: 2025-09-13 19:36:07

## Summary
- **Models Processed**: 5
- **Successfully Transformed**: 4
- **Success Rate**: 80.0%
- **Total Transformations Applied**: 2387

## Model Transformation Results
### Panel - ✅ PASS
- **Original Rows**: 256
- **Transformed Rows**: 256
- **Transformations Applied**: 556
- **Transformation Details**:
  - Columns Reordered: 1
  - Missing Columns Added: 11
  - Data Types Converted: 15
  - Default Values Applied: 529
- **Warnings**:
  - Non-standard categories present: 
  - Column 'Unit Cost (AUD $/unit)' has 201 null values
- **Output File**: data/standardized/Panel_standardized.csv

### WES (P) - ✅ PASS
- **Original Rows**: 264
- **Transformed Rows**: 264
- **Transformations Applied**: 570
- **Transformation Details**:
  - Columns Reordered: 1
  - Missing Columns Added: 11
  - Data Types Converted: 15
  - Default Values Applied: 543
- **Warnings**:
  - Non-standard categories present: 
  - Column 'Unit Cost (AUD $/unit)' has 211 null values
- **Output File**: data/standardized/WES_P_standardized.csv

### WES (T) - ✅ PASS
- **Original Rows**: 300
- **Transformed Rows**: 300
- **Transformations Applied**: 651
- **Transformation Details**:
  - Columns Reordered: 1
  - Missing Columns Added: 11
  - Data Types Converted: 15
  - Default Values Applied: 624
- **Warnings**:
  - Non-standard categories present: 
  - Column 'Unit Cost (AUD $/unit)' has 239 null values
- **Output File**: data/standardized/WES_T_standardized.csv

### WGS - ❌ FAIL
- **Original Rows**: 0
- **Transformed Rows**: 0
- **Transformations Applied**: 0
- **Errors**:
  - Could not load original model data

### WGS (T) - ✅ PASS
- **Original Rows**: 271
- **Transformed Rows**: 271
- **Transformations Applied**: 610
- **Transformation Details**:
  - Columns Reordered: 1
  - Missing Columns Added: 11
  - Data Types Converted: 15
  - Default Values Applied: 583
- **Warnings**:
  - Non-standard categories present: 
  - Column 'Unit Cost (AUD $/unit)' has 190 null values
- **Output File**: data/standardized/WGS_T_standardized.csv

## Overall Assessment
⚠️ **1 model(s) failed transformation**
Failed models: WGS
Review the errors above and adjust the templates or transformation rules as needed.

## Transformation Statistics
- **Columns Reordered**: 4
- **Data Types Converted**: 60
- **Default Values Applied**: 2279
- **Missing Columns Added**: 44