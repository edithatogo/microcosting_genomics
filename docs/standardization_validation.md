# Standardization Validation Report
Generated: 2025-09-13 19:30:49

**Note**: This validation focuses on structural consistency rather than cost accuracy
due to Excel formula references in the source data.

## Summary
- **Models Validated**: 5
- **Valid Models**: 4
- **Success Rate**: 80.0%

## Model Validation Results
### Panel - ✅ PASS
- **Original Complexity**: 385 cost cells
- **Standardized Complexity**: 385 cost cells
- **Warnings**:
  - Model has 27 columns
  - Found 2 cost-related columns
  - No standard categories detected in model

### WES (P) - ✅ PASS
- **Original Complexity**: 402 cost cells
- **Standardized Complexity**: 402 cost cells
- **Warnings**:
  - Model has 27 columns
  - Found 2 cost-related columns
  - No standard categories detected in model

### WES (T) - ✅ PASS
- **Original Complexity**: 451 cost cells
- **Standardized Complexity**: 451 cost cells
- **Warnings**:
  - Model has 27 columns
  - Found 2 cost-related columns
  - No standard categories detected in model

### WGS - ❌ FAIL
- **Original Complexity**: 0 cost cells
- **Standardized Complexity**: 0 cost cells
- **Errors**:
  - Model data is empty or could not be loaded

### WGS (T) - ✅ PASS
- **Original Complexity**: 357 cost cells
- **Standardized Complexity**: 357 cost cells
- **Warnings**:
  - Model has 27 columns
  - Found 2 cost-related columns
  - No standard categories detected in model

## Recommendations
### Failed Models
- **WGS**: Model data is empty or could not be loaded

### Successful Models
- **Panel**: Structure validation passed
- **WES (P)**: Structure validation passed
- **WES (T)**: Structure validation passed
- **WGS (T)**: Structure validation passed

### Overall Assessment
⚠️ **1 model(s) failed validation**
Review the failed models and adjust standardization rules as needed.