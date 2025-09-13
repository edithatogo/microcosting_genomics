"""Data Quality Assurance module for genomics microcosting analysis.

This module provides comprehensive data quality assurance capabilities including
automated anomaly detection, cross-sheet consistency validation, missing data handling,
and data integrity verification.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from pathlib import Path
import logging
from datetime import datetime
import json
import warnings

from .data_manager import DataManager
from .data_consistency_validator import DataConsistencyValidator
from .logging_config import get_logger
from .input_validation import InputValidator, ValidationError

logger = get_logger(__name__)


class DataQualityMetrics:
    """Data quality metrics container."""
    
    def __init__(self, sheet_name: str):
        """Initialize data quality metrics.
        
        Args:
            sheet_name: Name of the sheet being analyzed
        """
        self.sheet_name = sheet_name
        self.timestamp = datetime.now()
        self.null_percentage = 0.0
        self.duplicate_rows = 0
        self.anomalies_detected = []
        self.consistency_issues = []
        self.missing_data_patterns = []
        self.data_type_issues = []
        self.range_violations = []
        self.integrity_violations = []


class DataAnomalyDetector:
    """Automated data anomaly detection for cost values and other metrics."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the anomaly detector.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)
    
    def detect_cost_anomalies(self, df: pd.DataFrame, cost_columns: List[str]) -> List[Dict[str, Any]]:
        """Detect anomalies in cost-related columns.
        
        Args:
            df: DataFrame to analyze
            cost_columns: List of column names containing cost data
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for col in cost_columns:
            if col not in df.columns:
                continue
                
            col_data = df[col]
            
            # Skip non-numeric columns
            if not pd.api.types.is_numeric_dtype(col_data):
                continue
            
            # Remove NaN values for analysis
            clean_data = col_data.dropna()
            if len(clean_data) == 0:
                continue
            
            # Statistical anomaly detection
            mean_val = clean_data.mean()
            std_val = clean_data.std()
            
            # Z-score based anomaly detection (values > 3 std dev from mean)
            if std_val > 0:
                z_scores = np.abs((clean_data - mean_val) / std_val)
                anomaly_indices = clean_data[z_scores > 3].index
                
                for idx in anomaly_indices:
                    anomalies.append({
                        "type": "statistical_outlier",
                        "column": col,
                        "value": clean_data.loc[idx],
                        "z_score": z_scores.loc[idx],
                        "description": f"Statistical outlier in {col}: {clean_data.loc[idx]} (Z-score: {z_scores.loc[idx]:.2f})"
                    })
            
            # Negative cost detection
            negative_costs = col_data[col_data < 0]
            for idx, value in negative_costs.items():
                anomalies.append({
                    "type": "negative_cost",
                    "column": col,
                    "value": value,
                    "description": f"Negative cost value in {col}: {value}"
                })
            
            # Zero cost detection (may be valid but worth noting)
            zero_costs = col_data[col_data == 0]
            if len(zero_costs) > len(col_data) * 0.1:  # More than 10% zeros
                anomalies.append({
                    "type": "high_zero_percentage",
                    "column": col,
                    "count": len(zero_costs),
                    "percentage": (len(zero_costs) / len(col_data)) * 100,
                    "description": f"High percentage of zero values in {col}: {len(zero_costs)}/{len(col_data)} ({(len(zero_costs) / len(col_data)) * 100:.1f}%)"
                })
        
        self.logger.info(f"Detected {len(anomalies)} cost anomalies")
        return anomalies
    
    def detect_pattern_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in data patterns.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            List of detected pattern anomalies
        """
        anomalies = []
        
        # Check for suspicious text patterns
        text_columns = df.select_dtypes(include=['object']).columns
        for col in text_columns:
            col_data = df[col].dropna().astype(str)
            
            # Look for suspicious patterns like repeated characters
            for idx, value in col_data.items():
                if len(value) > 10 and len(set(value)) < 3:  # Mostly repeated characters
                    anomalies.append({
                        "type": "repeated_characters",
                        "column": col,
                        "value": value,
                        "description": f"Suspicious repeated characters in {col}: {value}"
                    })
        
        # Check for inconsistent data types within columns
        for col in df.columns:
            col_data = df[col].dropna()
            if len(col_data) > 0:
                # Check if numeric column has text values
                if pd.api.types.is_numeric_dtype(col_data):
                    non_numeric = col_data[~pd.to_numeric(col_data, errors='coerce').notna()]
                    if len(non_numeric) > 0:
                        anomalies.append({
                            "type": "inconsistent_data_type",
                            "column": col,
                            "count": len(non_numeric),
                            "description": f"Found {len(non_numeric)} non-numeric values in numeric column {col}"
                        })
        
        self.logger.info(f"Detected {len(anomalies)} pattern anomalies")
        return anomalies


class MissingDataHandler:
    """Handle missing data patterns and provide strategies for dealing with them."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the missing data handler.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def analyze_missing_data_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze patterns in missing data.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with missing data analysis results
        """
        results = {
            "total_cells": df.shape[0] * df.shape[1],
            "missing_cells": df.isnull().sum().sum(),
            "missing_percentage": 0.0,
            "columns_with_missing": {},
            "rows_with_missing": {},
            "patterns": []
        }
        
        if results["total_cells"] > 0:
            results["missing_percentage"] = (results["missing_cells"] / results["total_cells"]) * 100
        
        # Analyze missing data by column
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                results["columns_with_missing"][col] = {
                    "count": missing_count,
                    "percentage": (missing_count / len(df)) * 100
                }
        
        # Analyze missing data by row
        row_missing = df.isnull().sum(axis=1)
        rows_with_missing = row_missing[row_missing > 0]
        for idx, count in rows_with_missing.items():
            results["rows_with_missing"][idx] = {
                "count": count,
                "percentage": (count / len(df.columns)) * 100
            }
        
        # Identify patterns (completely missing columns/rows)
        completely_missing_cols = [col for col, info in results["columns_with_missing"].items() 
                                 if info["percentage"] == 100.0]
        if completely_missing_cols:
            results["patterns"].append({
                "type": "completely_missing_columns",
                "columns": completely_missing_cols,
                "description": f"Columns with 100% missing data: {completely_missing_cols}"
            })
        
        self.logger.info(f"Analyzed missing data patterns: {results['missing_percentage']:.2f}% missing")
        return results
    
    def suggest_missing_data_strategies(self, missing_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest strategies for handling missing data based on analysis.
        
        Args:
            missing_analysis: Results from analyze_missing_data_patterns
            
        Returns:
            List of suggested strategies
        """
        strategies = []
        
        missing_percentage = missing_analysis["missing_percentage"]
        
        if missing_percentage == 0:
            strategies.append({
                "strategy": "no_action_needed",
                "description": "No missing data detected"
            })
        elif missing_percentage < 5:
            strategies.append({
                "strategy": "drop_missing",
                "description": "Low percentage of missing data - consider dropping rows with missing values"
            })
        elif missing_percentage < 20:
            strategies.append({
                "strategy": "imputation",
                "description": "Moderate missing data - consider imputation strategies"
            })
            strategies.append({
                "strategy": "mean_imputation",
                "description": "For numeric columns, use mean imputation",
                "applicable_to": "numeric_columns"
            })
            strategies.append({
                "strategy": "mode_imputation",
                "description": "For categorical columns, use mode imputation",
                "applicable_to": "categorical_columns"
            })
        else:
            strategies.append({
                "strategy": "advanced_imputation",
                "description": "High percentage of missing data - consider advanced imputation or separate analysis"
            })
            strategies.append({
                "strategy": "multiple_imputation",
                "description": "Use multiple imputation techniques for robust results"
            })
        
        # Specific column strategies
        for col, info in missing_analysis["columns_with_missing"].items():
            if info["percentage"] > 50:
                strategies.append({
                    "strategy": "column_review",
                    "column": col,
                    "description": f"Column '{col}' has {info['percentage']:.1f}% missing data - review necessity"
                })
        
        return strategies


class DataIntegrityVerifier:
    """Verify data integrity through various checks."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the integrity verifier.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)
    
    def verify_cost_integrity(self, df: pd.DataFrame, cost_columns: List[str]) -> List[Dict[str, Any]]:
        """Verify integrity of cost-related data.
        
        Args:
            df: DataFrame to verify
            cost_columns: List of column names containing cost data
            
        Returns:
            List of integrity violations
        """
        violations = []
        
        for col in cost_columns:
            if col not in df.columns:
                continue
                
            col_data = df[col]
            
            # Validate numeric values
            try:
                # Check if column is numeric
                if not pd.api.types.is_numeric_dtype(col_data):
                    violations.append({
                        "type": "non_numeric_cost_column",
                        "column": col,
                        "description": f"Cost column {col} is not numeric"
                    })
                    continue
                
                # Validate individual values
                for idx, value in col_data.items():
                    if pd.notna(value):  # Only check non-null values
                        try:
                            self.validator.validate_numeric_value(value, min_value=0)
                        except ValidationError as e:
                            violations.append({
                                "type": "invalid_cost_value",
                                "column": col,
                                "row": idx,
                                "value": value,
                                "description": f"Invalid cost value in {col} at row {idx}: {value} - {str(e)}"
                            })
            except Exception as e:
                violations.append({
                    "type": "cost_validation_error",
                    "column": col,
                    "description": f"Error validating cost column {col}: {str(e)}"
                })
        
        self.logger.info(f"Verified cost integrity, found {len(violations)} violations")
        return violations
    
    def verify_cross_sheet_integrity(self, data_manager: DataManager, 
                                   sheet_dependencies: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Verify integrity of cross-sheet references.
        
        Args:
            data_manager: DataManager instance
            sheet_dependencies: Dictionary mapping sheet names to their dependencies
            
        Returns:
            List of cross-sheet integrity violations
        """
        violations = []
        
        for sheet_name, dependencies in sheet_dependencies.items():
            # Load the main sheet
            main_df = data_manager.load_sheet(sheet_name)
            if main_df is None:
                violations.append({
                    "type": "sheet_not_found",
                    "sheet": sheet_name,
                    "description": f"Main sheet {sheet_name} not found"
                })
                continue
            
            # Check each dependency
            for dep_sheet in dependencies:
                dep_df = data_manager.load_sheet(dep_sheet)
                if dep_df is None:
                    violations.append({
                        "type": "dependency_missing",
                        "sheet": sheet_name,
                        "dependency": dep_sheet,
                        "description": f"Dependency sheet {dep_sheet} required by {sheet_name} not found"
                    })
        
        self.logger.info(f"Verified cross-sheet integrity, found {len(violations)} violations")
        return violations


class DataQualityAssurance:
    """Comprehensive data quality assurance system."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the data quality assurance system.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.anomaly_detector = DataAnomalyDetector(self.logger)
        self.missing_data_handler = MissingDataHandler(self.logger)
        self.integrity_verifier = DataIntegrityVerifier(self.logger)
        self.consistency_validator = DataConsistencyValidator(data_manager)
        self.quality_reports: List[DataQualityMetrics] = []
    
    def assess_data_quality(self, sheet_name: str, 
                          cost_columns: Optional[List[str]] = None,
                          expected_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
                          unique_columns: Optional[List[str]] = None) -> DataQualityMetrics:
        """Assess overall data quality for a sheet.
        
        Args:
            sheet_name: Name of the sheet to assess
            cost_columns: List of column names containing cost data (optional)
            expected_ranges: Dictionary mapping column names to (min, max) tuples (optional)
            unique_columns: List of column names that should be unique (optional)
            
        Returns:
            DataQualityMetrics object with assessment results
        """
        self.logger.info(f"Assessing data quality for sheet: {sheet_name}")
        
        # Load data
        df = self.data_manager.load_sheet(sheet_name)
        if df is None:
            raise ValueError(f"Could not load sheet: {sheet_name}")
        
        # Create quality metrics object
        metrics = DataQualityMetrics(sheet_name)
        
        # Basic integrity validation
        integrity_results = self.consistency_validator.validate_sheet_integrity(sheet_name, df)
        if not integrity_results["passed"]:
            metrics.integrity_violations.extend(integrity_results["errors"])
            metrics.integrity_violations.extend(integrity_results["warnings"])
        
        # Null percentage
        metrics.null_percentage = integrity_results["metrics"]["null_percentage"]
        
        # Duplicate rows
        metrics.duplicate_rows = integrity_results["metrics"]["duplicate_rows"]
        
        # Anomaly detection
        if cost_columns:
            cost_anomalies = self.anomaly_detector.detect_cost_anomalies(df, cost_columns)
            metrics.anomalies_detected.extend(cost_anomalies)
        
        # Pattern anomalies
        pattern_anomalies = self.anomaly_detector.detect_pattern_anomalies(df)
        metrics.anomalies_detected.extend(pattern_anomalies)
        
        # Missing data analysis
        missing_analysis = self.missing_data_handler.analyze_missing_data_patterns(df)
        metrics.missing_data_patterns.append(missing_analysis)
        
        # Data integrity verification
        if cost_columns:
            integrity_violations = self.integrity_verifier.verify_cost_integrity(df, cost_columns)
            metrics.integrity_violations.extend(integrity_violations)
        
        # Range validation if provided
        if expected_ranges:
            range_results = self.consistency_validator.validate_data_ranges(
                sheet_name, df, expected_ranges)
            if not range_results["passed"]:
                metrics.range_violations.extend(range_results["warnings"])
        
        # Unique constraint validation if provided
        if unique_columns:
            unique_results = self.consistency_validator.validate_unique_constraints(
                sheet_name, df, unique_columns)
            if not unique_results["passed"]:
                metrics.integrity_violations.extend(unique_results["errors"])
        
        # Store the metrics
        self.quality_reports.append(metrics)
        
        self.logger.info(f"Data quality assessment complete for {sheet_name}: "
                        f"{len(metrics.anomalies_detected)} anomalies, "
                        f"{len(metrics.integrity_violations)} violations")
        
        return metrics
    
    def generate_quality_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive data quality report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        self.logger.info("Generating comprehensive data quality report")
        
        report = []
        report.append("# Genomics Microcosting Data Quality Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## Executive Summary")
        report.append("This report presents the results of comprehensive data quality assessment "
                     "across all sheets in the genomics microcosting analysis.")
        report.append("")
        
        total_anomalies = 0
        total_violations = 0
        sheets_with_issues = 0
        
        for metrics in self.quality_reports:
            sheet_anomalies = len(metrics.anomalies_detected)
            sheet_violations = len(metrics.integrity_violations)
            
            if sheet_anomalies > 0 or sheet_violations > 0:
                sheets_with_issues += 1
            
            total_anomalies += sheet_anomalies
            total_violations += sheet_violations
        
        report.append(f"- Total sheets analyzed: {len(self.quality_reports)}")
        report.append(f"- Sheets with data quality issues: {sheets_with_issues}")
        report.append(f"- Total anomalies detected: {total_anomalies}")
        report.append(f"- Total integrity violations: {total_violations}")
        report.append("")
        
        report.append("## Detailed Results by Sheet")
        report.append("")
        
        for metrics in self.quality_reports:
            report.append(f"### {metrics.sheet_name}")
            report.append(f"Analysis timestamp: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # Basic metrics
            report.append("**Basic Quality Metrics:**")
            report.append(f"- Null percentage: {metrics.null_percentage:.2f}%")
            report.append(f"- Duplicate rows: {metrics.duplicate_rows}")
            report.append("")
            
            # Anomalies
            if metrics.anomalies_detected:
                report.append("**Detected Anomalies:**")
                for anomaly in metrics.anomalies_detected[:10]:  # Limit to first 10
                    report.append(f"- {anomaly.get('description', 'Unknown anomaly')}")
                if len(metrics.anomalies_detected) > 10:
                    report.append(f"- ... and {len(metrics.anomalies_detected) - 10} more anomalies")
                report.append("")
            else:
                report.append("**No anomalies detected**")
                report.append("")
            
            # Integrity violations
            if metrics.integrity_violations:
                report.append("**Integrity Violations:**")
                for violation in metrics.integrity_violations[:10]:  # Limit to first 10
                    report.append(f"- {violation.get('description', 'Unknown violation')}")
                if len(metrics.integrity_violations) > 10:
                    report.append(f"- ... and {len(metrics.integrity_violations) - 10} more violations")
                report.append("")
            else:
                report.append("**No integrity violations detected**")
                report.append("")
            
            # Missing data patterns
            if metrics.missing_data_patterns:
                report.append("**Missing Data Analysis:**")
                for pattern_analysis in metrics.missing_data_patterns:
                    report.append(f"- Missing data percentage: {pattern_analysis['missing_percentage']:.2f}%")
                    if pattern_analysis['patterns']:
                        report.append("  Patterns detected:")
                        for pattern in pattern_analysis['patterns']:
                            report.append(f"  - {pattern.get('description', 'Unknown pattern')}")
                report.append("")
        
        report.append("## Recommendations")
        report.append("")
        
        if total_anomalies > 0:
            report.append("### Anomaly Handling")
            report.append("- Review all detected anomalies for data entry errors")
            report.append("- Investigate statistical outliers to determine if they represent valid extreme values")
            report.append("- Address negative cost values as these typically indicate data issues")
            report.append("")
        
        if sheets_with_issues > 0:
            report.append("### Data Quality Improvement")
            report.append("- Implement data validation rules at data entry points")
            report.append("- Establish regular data quality monitoring")
            report.append("- Create data quality dashboards for ongoing monitoring")
            report.append("- Develop data cleaning procedures for common issues")
            report.append("")
        
        report_str = "\n".join(report)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report_str)
                self.logger.info(f"Data quality report saved to {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to save data quality report: {e}")
        
        return report_str
    
    def get_quality_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all quality metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_sheets": len(self.quality_reports),
            "sheets_with_anomalies": 0,
            "sheets_with_violations": 0,
            "total_anomalies": 0,
            "total_violations": 0,
            "average_null_percentage": 0.0,
            "sheets": []
        }
        
        null_percentages = []
        
        for metrics in self.quality_reports:
            has_anomalies = len(metrics.anomalies_detected) > 0
            has_violations = len(metrics.integrity_violations) > 0
            
            if has_anomalies:
                summary["sheets_with_anomalies"] += 1
            if has_violations:
                summary["sheets_with_violations"] += 1
            
            summary["total_anomalies"] += len(metrics.anomalies_detected)
            summary["total_violations"] += len(metrics.integrity_violations)
            null_percentages.append(metrics.null_percentage)
            
            summary["sheets"].append({
                "sheet_name": metrics.sheet_name,
                "anomalies": len(metrics.anomalies_detected),
                "violations": len(metrics.integrity_violations),
                "null_percentage": metrics.null_percentage,
                "duplicate_rows": metrics.duplicate_rows
            })
        
        if null_percentages:
            summary["average_null_percentage"] = sum(null_percentages) / len(null_percentages)
        
        return summary


# Example usage:
if __name__ == "__main__":
    # This would typically be run through the main application
    pass