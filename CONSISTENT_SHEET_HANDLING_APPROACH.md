# Consistent Sheet Handling Approach for Microcosting Analysis

This document describes the standardized approach implemented for handling all sheets in the microcosting analysis, ensuring consistent treatment regardless of their source or purpose.

## Overview

The implementation provides a unified framework for:

1. **Consistent Data Handling**: All sheets are processed using the same methods and saved in standardized formats
2. **Systematic Validation**: Comprehensive validation of all sheets to ensure proper translation
3. **Extensible Architecture**: Framework designed for future expansion and adaptation
4. **Scenario Analysis Standardization**: Consistent approach to DSA, PSA, and custom scenario analyses

## Key Components

### 1. DataManager Class

The [DataManager](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/data_manager.py#L16-L215) class provides a unified interface for all data operations:

- **Consistent Loading/Saving**: All sheets are loaded and saved using standardized methods
- **Multiple Format Support**: Data is saved in both Parquet (for efficiency) and CSV (for accessibility) formats
- **Publication-Ready Output**: Automatic generation of data dictionaries and metadata for publication
- **Error Handling**: Comprehensive error handling and logging

### 2. Standardized Preparation Script

The [prepare_all_sheets.py](file:///Users/doughnut/GitHub/microcosting_genomics/scripts/prepare_all_sheets.py) script ensures all sheets are processed consistently:

- **Uniform Processing**: All configured sheets are processed using the same workflow
- **Metadata Generation**: Automatic creation of metadata for each sheet
- **Publication Preparation**: Consistent formatting for publication-ready outputs

### 3. Systematic Validation Framework

The [validate_all_sheets.py](file:///Users/doughnut/GitHub/microcosting_genomics/scripts/validate_all_sheets.py) script provides comprehensive validation:

- **Integrity Checking**: Validation of data structure and content
- **Format Consistency**: Verification that different formats contain equivalent data
- **Cross-Reference Validation**: Checking that references between sheets are properly resolved

### 4. Scenario Analysis Standardization

The [analyze_scenarios.py](file:///Users/doughnut/GitHub/microcosting_genomics/scripts/analyze_scenarios.py) script provides a consistent approach to sensitivity and scenario analyses:

- **DSA Standardization**: Uniform handling of Deterministic Sensitivity Analysis
- **PSA Framework**: Consistent Probabilistic Sensitivity Analysis implementation
- **Custom Scenario Support**: Extensible framework for custom scenarios

## Implementation Details

### Data Format Standardization

All sheets are now handled consistently:

1. **Prepared Directory**: All sheets saved as both `.parquet` and `.csv` files
2. **Publication Directory**: All sheets saved as `.csv` with accompanying data dictionaries and metadata
3. **Naming Convention**: Standardized file naming based on sheet names
4. **Metadata**: Automatic generation of metadata for all sheets

### Validation Process

Comprehensive validation ensures all sheets have been properly translated:

1. **Integrity Validation**: Checking data structure, null values, and basic statistics
2. **Consistency Validation**: Ensuring different formats contain equivalent data
3. **Cross-Reference Validation**: Verifying that inter-sheet references work correctly

### Scenario Analysis Framework

Standardized approach to sensitivity and scenario analyses:

1. **DSA Handling**: Consistent processing of deterministic sensitivity parameters
2. **PSA Implementation**: Standardized probabilistic analysis framework
3. **Custom Scenarios**: Extensible system for custom scenario definition and analysis

## Benefits of This Approach

### 1. Consistency
- All sheets treated uniformly regardless of their purpose or source
- Standardized file formats and naming conventions
- Consistent metadata and documentation

### 2. Extensibility
- Framework designed for easy addition of new sheets
- Modular architecture supports future enhancements
- Standardized interfaces for new functionality

### 3. Validation
- Systematic verification of all sheets
- Comprehensive error detection and reporting
- Quality assurance for all data products

### 4. Reproducibility
- Standardized workflows ensure consistent results
- Clear documentation of all processes
- Traceable data lineage

## Files Created

1. [src/unimelb_phd_phase_1/data_manager.py](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/data_manager.py) - Unified data management class
2. [scripts/prepare_all_sheets.py](file:///Users/doughnut/GitHub/microcosting_genomics/scripts/prepare_all_sheets.py) - Standardized preparation script
3. [scripts/validate_all_sheets.py](file:///Users/doughnut/GitHub/microcosting_genomics/scripts/validate_all_sheets.py) - Systematic validation script
4. [scripts/analyze_scenarios.py](file:///Users/doughnut/GitHub/microcosting_genomics/scripts/analyze_scenarios.py) - Standardized scenario analysis script
5. [CONSISTENT_SHEET_HANDLING_APPROACH.md](file:///Users/doughnut/GitHub/microcosting_genomics/CONSISTENT_SHEET_HANDLING_APPROACH.md) - This documentation

## Usage Instructions

### Preparing All Sheets
```bash
python scripts/prepare_all_sheets.py
```

### Validating All Sheets
```bash
python scripts/validate_all_sheets.py
```

### Performing Scenario Analyses
```bash
python scripts/analyze_scenarios.py
```

## Future Extensions

This framework is designed to support future extensions:

1. **Additional Sheet Types**: Easy addition of new sheet categories
2. **Enhanced Validation**: More sophisticated validation rules
3. **Advanced Analytics**: Integration with machine learning and advanced statistical methods
4. **Web Interface**: API endpoints for web-based access to sheet data
5. **Real-time Processing**: Streaming data processing capabilities

## Conclusion

This implementation provides a robust, consistent framework for handling all sheets in the microcosting analysis. The standardized approach ensures that all data is processed uniformly, validated systematically, and prepared for both current analysis needs and future extensions. The modular design supports the long-term goal of adapting and extending the genomic microcosting model while maintaining the rigor and reproducibility required for academic research.