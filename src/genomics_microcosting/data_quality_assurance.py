# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Data Quality Assurance module for genomics microcosting analysis.

This module provides comprehensive data quality assurance capabilities including
automated anomaly detection, cross-sheet consistency validation, missing data handling,
and data integrity verification.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Required, TypedDict
lazy import logging

import numpy as np
import polars as pl
import polars.selectors as cs

from .data_consistency_validator import DataConsistencyValidator
from .input_validation import InputValidator, ValidationError
from .logging_config import get_logger
lazy from .data_manager import DataManager

logger = get_logger(__name__)
_OUTLIER_STANDARD_DEVIATIONS = 3
_REPEATED_TEXT_MINIMUM_LENGTH = 10
_REPEATED_TEXT_MAXIMUM_DISTINCT_CHARACTERS = 2
_FULL_PERCENTAGE = 100
_LOW_MISSING_PERCENTAGE = 5
_MODERATE_MISSING_PERCENTAGE = 20
_COLUMN_REVIEW_PERCENTAGE = 50
_REPORT_FINDING_LIMIT = 10


class QualityFinding(TypedDict, total=False):
    """Retain anomaly values and source row ordinals without an untyped record."""

    type: Required[str]
    column: str
    row: int
    value: object
    z_score: float
    description: str
    count: int
    percentage: float
    sheet: str
    dependency: str


class MissingCount(TypedDict):
    """Describe a missing count with its explicit percentage denominator."""

    count: int
    percentage: float


class MissingPattern(TypedDict):
    """Describe a completely missing set of fields."""

    type: str
    columns: list[str]
    description: str


class MissingDataPercentages(TypedDict):
    """Measurements consumed when selecting a missing-data strategy."""

    missing_percentage: float
    columns_with_missing: dict[str, MissingCount]


class MissingAnalysis(MissingDataPercentages):
    """Keep field and row missingness measurements in a typed structure."""

    total_cells: int
    missing_cells: int
    rows_with_missing: dict[int, MissingCount]
    patterns: list[MissingPattern]


class SheetQualitySummary(TypedDict):
    """Summarise observed findings for one source sheet."""

    sheet_name: str
    anomalies: int
    violations: int
    null_percentage: float
    duplicate_rows: int


class QualitySummary(TypedDict):
    """Aggregate quality measurements without an untyped summary dictionary."""

    total_sheets: int
    sheets_with_anomalies: int
    sheets_with_violations: int
    total_anomalies: int
    total_violations: int
    average_null_percentage: float
    sheets: list[SheetQualitySummary]


class DataQualityMetrics:
    """Data quality metrics container."""

    def __init__(self, sheet_name: str) -> None:
        """Initialize data quality metrics.

        Args:
            sheet_name: Name of the sheet being analyzed

        """
        self.sheet_name = sheet_name
        self.timestamp = datetime.now(UTC)
        self.null_percentage = 0.0
        self.duplicate_rows = 0
        self.anomalies_detected: list[QualityFinding] = []
        self.consistency_issues: list[str] = []
        self.missing_data_patterns: list[MissingAnalysis] = []
        self.data_type_issues: list[str] = []
        self.range_violations: list[str] = []
        self.integrity_violations: list[str | QualityFinding] = []


class DataAnomalyDetector:
    """Automated data anomaly detection for cost values and other metrics."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the anomaly detector.

        Args:
            logger: Logger instance (optional)

        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)

    def detect_cost_anomalies(
        self,
        df: pl.DataFrame,
        cost_columns: list[str],
    ) -> list[QualityFinding]:
        """Detect anomalies in cost-related columns.

        Args:
            df: DataFrame to analyze
            cost_columns: List of column names containing cost data

        Returns:
            List of detected anomalies

        """
        df = df.with_columns(cs.float().fill_nan(None))
        anomalies: list[QualityFinding] = []

        for col in cost_columns:
            if col not in df.columns:
                continue

            col_data = df[col]

            # Skip non-numeric columns
            if not col_data.dtype.is_numeric():
                continue

            # Remove NaN values for analysis
            clean_data = col_data.drop_nulls()
            if len(clean_data) == 0:
                continue

            # Statistical calculations use a numerical boundary, retaining source
            # values.
            source_rows = [
                idx for idx, value in enumerate(col_data.to_list()) if value is not None
            ]
            numeric = np.asarray(clean_data.to_list(), dtype=float)
            mean_val = float(numeric.mean())
            std_val = float(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0
            if std_val > 0:
                z_scores = np.abs((numeric - mean_val) / std_val)
                for position in np.flatnonzero(z_scores > _OUTLIER_STANDARD_DEVIATIONS):
                    value = clean_data[int(position)]
                    score = float(z_scores[position])
                    anomalies.append(
                        {
                            "type": "statistical_outlier",
                            "row": source_rows[int(position)],
                            "column": col,
                            "value": value,
                            "z_score": score,
                            "description": (
                                f"Statistical outlier in {col}: "
                                f"{value} (Z-score: {score:.2f})"
                            ),
                        },
                    )
            negative_costs = col_data.filter(col_data < 0)
            anomalies.extend(
                {
                    "type": "negative_cost",
                    "column": col,
                    "value": value,
                    "description": f"Negative cost value in {col}: {value}",
                }
                for value in negative_costs
            )

            # Zero cost detection (may be valid but worth noting)
            zero_costs = col_data.filter(col_data == 0)
            if len(zero_costs) > len(col_data) * 0.1:  # More than 10% zeros
                percentage = (len(zero_costs) / len(col_data)) * 100
                anomalies.append(
                    {
                        "type": "high_zero_percentage",
                        "column": col,
                        "count": len(zero_costs),
                        "percentage": percentage,
                        "description": (
                            f"High percentage of zero values in {col}: "
                            f"{len(zero_costs)}/{len(col_data)} ({percentage:.1f}%)"
                        ),
                    },
                )

        self.logger.info("Detected %s cost anomalies", len(anomalies))
        return anomalies

    def detect_pattern_anomalies(self, df: pl.DataFrame) -> list[QualityFinding]:
        """Detect anomalies in data patterns.

        Args:
            df: DataFrame to analyze

        Returns:
            List of detected pattern anomalies

        """
        df = df.with_columns(cs.float().fill_nan(None))
        anomalies: list[QualityFinding] = []

        # Check for suspicious text patterns
        text_columns = df.select(cs.string()).columns
        for col in text_columns:
            col_data = df[col].drop_nulls().cast(pl.String)

            # Look for suspicious patterns like repeated characters
            for _idx, value in enumerate(col_data.to_list()):
                if (
                    len(value) > _REPEATED_TEXT_MINIMUM_LENGTH
                    and len(set(value)) <= _REPEATED_TEXT_MAXIMUM_DISTINCT_CHARACTERS
                ):  # Mostly repeated characters
                    anomalies.append(
                        {
                            "type": "repeated_characters",
                            "column": col,
                            "value": value,
                            "description": (
                                f"Suspicious repeated characters in {col}: {value}"
                            ),
                        },
                    )

        # Check for inconsistent data types within columns
        for col in df.columns:
            col_data = df[col].drop_nulls()
            # Check if a populated numeric column has text values.
            if len(col_data) > 0 and col_data.dtype.is_numeric():
                non_numeric = col_data.filter(
                    col_data.cast(pl.Float64, strict=False).is_null(),
                )
                if len(non_numeric) > 0:
                    anomalies.append(
                        {
                            "type": "inconsistent_data_type",
                            "column": col,
                            "count": len(non_numeric),
                            "description": (
                                f"Found {len(non_numeric)} non-numeric "
                                f"values in numeric column {col}"
                            ),
                        },
                    )

        self.logger.info("Detected %s pattern anomalies", len(anomalies))
        return anomalies


class MissingDataHandler:
    """Handle missing data patterns and provide strategies for dealing with them."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the missing data handler.

        Args:
            logger: Logger instance (optional)

        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")

    def analyze_missing_data_patterns(self, df: pl.DataFrame) -> MissingAnalysis:
        """Analyze patterns in missing data.

        Args:
            df: DataFrame to analyze

        Returns:
            Dictionary with missing data analysis results

        """
        df = df.with_columns(cs.float().fill_nan(None))
        results: MissingAnalysis = {
            "total_cells": df.shape[0] * df.shape[1],
            "missing_cells": sum(df.null_count().row(0)),
            "missing_percentage": 0.0,
            "columns_with_missing": {},
            "rows_with_missing": {},
            "patterns": [],
        }

        if results["total_cells"] > 0:
            results["missing_percentage"] = (
                results["missing_cells"] / results["total_cells"]
            ) * 100

        # Analyze missing data by column
        for col in df.columns:
            missing_count = df[col].null_count()
            if missing_count > 0:
                results["columns_with_missing"][col] = {
                    "count": missing_count,
                    "percentage": (missing_count / len(df)) * 100,
                }

        # Analyze missing data by row
        row_missing = (
            df.select(pl.sum_horizontal(pl.all().is_null())).to_series()
            if df.width
            else pl.Series([], dtype=pl.Int64)
        )
        for idx, count in enumerate(row_missing.to_list()):
            if count > 0:
                results["rows_with_missing"][idx] = {
                    "count": count,
                    "percentage": count / df.width * 100,
                }

        # Identify patterns (completely missing columns/rows)
        completely_missing_cols = [
            col
            for col, info in results["columns_with_missing"].items()
            if info["percentage"] == _FULL_PERCENTAGE
        ]
        if completely_missing_cols:
            results["patterns"].append(
                {
                    "type": "completely_missing_columns",
                    "columns": completely_missing_cols,
                    "description": (
                        f"Columns with 100% missing data: {completely_missing_cols}"
                    ),
                },
            )

        self.logger.info(
            "Analyzed missing data patterns: %s%% missing",
            format(results["missing_percentage"], ".2f"),
        )
        return results

    def suggest_missing_data_strategies(
        self,
        missing_analysis: MissingDataPercentages,
    ) -> list[dict[str, str]]:
        """Suggest strategies for handling missing data based on analysis.

        Args:
            missing_analysis: Results from analyze_missing_data_patterns

        Returns:
            List of suggested strategies

        """
        strategies: list[dict[str, str]] = []

        missing_percentage = missing_analysis["missing_percentage"]

        if missing_percentage == 0:
            strategies.append(
                {
                    "strategy": "no_action_needed",
                    "description": "No missing data detected",
                },
            )
        elif missing_percentage < _LOW_MISSING_PERCENTAGE:
            strategies.append(
                {
                    "strategy": "drop_missing",
                    "description": (
                        "Low percentage of missing data - consider dropping rows with "
                        "missing values"
                    ),
                },
            )
        elif missing_percentage < _MODERATE_MISSING_PERCENTAGE:
            strategies.append(
                {
                    "strategy": "imputation",
                    "description": (
                        "Moderate missing data - consider imputation strategies"
                    ),
                },
            )
            strategies.append(
                {
                    "strategy": "mean_imputation",
                    "description": "For numeric columns, use mean imputation",
                    "applicable_to": "numeric_columns",
                },
            )
            strategies.append(
                {
                    "strategy": "mode_imputation",
                    "description": "For categorical columns, use mode imputation",
                    "applicable_to": "categorical_columns",
                },
            )
        else:
            strategies.append(
                {
                    "strategy": "advanced_imputation",
                    "description": (
                        "High percentage of missing data - consider advanced imputation"
                        " or separate analysis"
                    ),
                },
            )
            strategies.append(
                {
                    "strategy": "multiple_imputation",
                    "description": (
                        "Use multiple imputation techniques for robust results"
                    ),
                },
            )

        # Specific column strategies
        for col, info in missing_analysis["columns_with_missing"].items():
            if info["percentage"] > _COLUMN_REVIEW_PERCENTAGE:
                strategies.append(
                    {
                        "strategy": "column_review",
                        "column": col,
                        "description": (
                            f"Column '{col}' has {info['percentage']:.1f}% "
                            f"missing data - review necessity"
                        ),
                    },
                )

        return strategies


class DataIntegrityVerifier:
    """Verify data integrity through various checks."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the integrity verifier.

        Args:
            logger: Logger instance (optional)

        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)

    def verify_cost_integrity(
        self,
        df: pl.DataFrame,
        cost_columns: list[str],
    ) -> list[QualityFinding]:
        """Verify integrity of cost-related data.

        Args:
            df: DataFrame to verify
            cost_columns: List of column names containing cost data

        Returns:
            List of integrity violations

        """
        df = df.with_columns(cs.float().fill_nan(None))
        violations: list[QualityFinding] = []

        for col in cost_columns:
            if col not in df.columns:
                continue

            col_data = df[col]

            # Validate numeric values
            try:
                # Check if column is numeric
                if not col_data.dtype.is_numeric():
                    violations.append(
                        {
                            "type": "non_numeric_cost_column",
                            "column": col,
                            "description": f"Cost column {col} is not numeric",
                        },
                    )
                    continue

                # Validate individual values
                for idx, value in enumerate(col_data.to_list()):
                    if value is not None:  # Only check non-null values
                        try:
                            self.validator.validate_numeric_value(value, min_value=0)
                        except ValidationError as e:
                            violations.append(
                                {
                                    "type": "invalid_cost_value",
                                    "column": col,
                                    "row": idx,
                                    "value": value,
                                    "description": (
                                        f"Invalid cost value in {col} "
                                        f"at row {idx}: {value} - {e!s}"
                                    ),
                                },
                            )
            except (ValueError, TypeError, pl.exceptions.PolarsError) as e:
                violations.append(
                    {
                        "type": "cost_validation_error",
                        "column": col,
                        "description": f"Error validating cost column {col}: {e!s}",
                    },
                )

        self.logger.info(
            "Verified cost integrity, found %s violations",
            len(violations),
        )
        return violations

    def verify_cross_sheet_integrity(
        self,
        data_manager: DataManager,
        sheet_dependencies: dict[str, list[str]],
    ) -> list[QualityFinding]:
        """Verify integrity of cross-sheet references.

        Args:
            data_manager: DataManager instance
            sheet_dependencies: Dictionary mapping sheet names to their dependencies

        Returns:
            List of cross-sheet integrity violations

        """
        violations: list[QualityFinding] = []

        for sheet_name, dependencies in sheet_dependencies.items():
            # Load the main sheet
            main_df = data_manager.load_sheet(sheet_name)
            if main_df is None:
                violations.append(
                    {
                        "type": "sheet_not_found",
                        "sheet": sheet_name,
                        "description": f"Main sheet {sheet_name} not found",
                    },
                )
                continue

            # Check each dependency
            for dep_sheet in dependencies:
                dep_df = data_manager.load_sheet(dep_sheet)
                if dep_df is None:
                    violations.append(
                        {
                            "type": "dependency_missing",
                            "sheet": sheet_name,
                            "dependency": dep_sheet,
                            "description": (
                                f"Dependency sheet {dep_sheet} "
                                f"required by {sheet_name} not found"
                            ),
                        },
                    )

        self.logger.info(
            "Verified cross-sheet integrity, found %s violations",
            len(violations),
        )
        return violations


class DataQualityAssurance:
    """Comprehensive data quality assurance system."""

    def __init__(self, data_manager: DataManager) -> None:
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
        self.quality_reports: list[DataQualityMetrics] = []

    def assess_data_quality(
        self,
        sheet_name: str,
        cost_columns: list[str] | None = None,
        expected_ranges: dict[str, tuple[float, float]] | None = None,
        unique_columns: list[str] | None = None,
    ) -> DataQualityMetrics:
        """Assess overall data quality for a sheet.

        Args:
            sheet_name: Name of the sheet to assess
            cost_columns: List of column names containing cost data (optional)
            expected_ranges: Optional bounds by column as (min, max) pairs.
            unique_columns: List of column names that should be unique (optional)

        Returns:
            DataQualityMetrics object with assessment results

        """
        self.logger.info("Assessing data quality for sheet: %s", sheet_name)

        # Load data
        df = self.data_manager.load_sheet(sheet_name)
        if df is None:
            message = f"Could not load sheet: {sheet_name}"
            raise ValueError(message)

        # Create quality metrics object
        metrics = DataQualityMetrics(sheet_name)

        # Basic integrity validation
        integrity_results = self.consistency_validator.validate_sheet_integrity(
            sheet_name,
            df,
        )
        if not integrity_results["passed"]:
            metrics.integrity_violations.extend(integrity_results["errors"])
            metrics.integrity_violations.extend(integrity_results["warnings"])

        # Null percentage
        metrics.null_percentage = integrity_results["metrics"]["null_percentage"]

        # Duplicate rows
        metrics.duplicate_rows = integrity_results["metrics"]["duplicate_rows"]

        # Anomaly detection
        if cost_columns:
            cost_anomalies = self.anomaly_detector.detect_cost_anomalies(
                df,
                cost_columns,
            )
            metrics.anomalies_detected.extend(cost_anomalies)

        # Pattern anomalies
        pattern_anomalies = self.anomaly_detector.detect_pattern_anomalies(df)
        metrics.anomalies_detected.extend(pattern_anomalies)

        # Missing data analysis
        missing_analysis = self.missing_data_handler.analyze_missing_data_patterns(df)
        metrics.missing_data_patterns.append(missing_analysis)

        # Data integrity verification
        if cost_columns:
            integrity_violations = self.integrity_verifier.verify_cost_integrity(
                df,
                cost_columns,
            )
            metrics.integrity_violations.extend(integrity_violations)

        # Range validation if provided
        if expected_ranges:
            range_results = self.consistency_validator.validate_data_ranges(
                sheet_name,
                df,
                expected_ranges,
            )
            metrics.range_violations.extend(range_results["warnings"])

        # Unique constraint validation if provided
        if unique_columns:
            unique_results = self.consistency_validator.validate_unique_constraints(
                sheet_name,
                df,
                unique_columns,
            )
            if not unique_results["passed"]:
                metrics.integrity_violations.extend(unique_results["errors"])

        # Store the metrics
        self.quality_reports.append(metrics)

        self.logger.info(
            "Data quality assessment complete for %s: %s anomalies, %s violations",
            sheet_name,
            len(metrics.anomalies_detected),
            len(metrics.integrity_violations),
        )

        return metrics

    def generate_quality_report(self, output_file: str | None = None) -> str:
        """Generate a comprehensive data quality report.

        Args:
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        self.logger.info("Generating comprehensive data quality report")

        report: list[str] = []
        report.append("# Genomics Microcosting Data Quality Report")
        generated_at = datetime.now(UTC).astimezone()
        report.append(f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## Executive Summary")
        report.append(
            "This report presents the results of comprehensive data quality assessment "
            "across all sheets in the genomics microcosting analysis.",
        )
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
            report.extend(self._sheet_quality_report(metrics))

        report.append("## Recommendations")
        report.append("")

        if total_anomalies > 0:
            report.append("### Anomaly Handling")
            report.append("- Review all detected anomalies for data entry errors")
            report.append(
                (
                    "- Investigate statistical outliers to determine if they represent "
                    "valid extreme values"
                ),
            )
            report.append(
                (
                    "- Address negative cost values as these typically indicate data "
                    "issues"
                ),
            )
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
                with Path(output_file).open("w") as f:
                    f.write(report_str)
                self.logger.info("Data quality report saved to %s", output_file)
            except Exception:
                self.logger.exception("Failed to save data quality report")

        return report_str

    @staticmethod
    def _sheet_quality_report(metrics: DataQualityMetrics) -> list[str]:
        report: list[str] = []
        report.append(f"### {metrics.sheet_name}")
        report.append(
            (f"Analysis timestamp: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"),
        )
        report.append("")

        # Basic metrics
        report.append("**Basic Quality Metrics:**")
        report.append(f"- Null percentage: {metrics.null_percentage:.2f}%")
        report.append(f"- Duplicate rows: {metrics.duplicate_rows}")
        report.append("")

        # Anomalies
        if metrics.anomalies_detected:
            report.append("**Detected Anomalies:**")
            report.extend(
                f"- {anomaly.get('description', 'Unknown anomaly')}"
                for anomaly in metrics.anomalies_detected[:_REPORT_FINDING_LIMIT]
            )
            remaining = len(metrics.anomalies_detected) - _REPORT_FINDING_LIMIT
            if remaining > 0:
                report.append(
                    (f"- ... and {remaining} more anomalies"),
                )
            report.append("")
        else:
            report.append("**No anomalies detected**")
            report.append("")

        # Integrity violations
        if metrics.integrity_violations:
            report.append("**Integrity Violations:**")
            report.extend(
                f"- {violation}"
                if isinstance(violation, str)
                else f"- {violation.get('description', 'Unknown violation')}"
                for violation in metrics.integrity_violations[:_REPORT_FINDING_LIMIT]
            )
            remaining = len(metrics.integrity_violations) - _REPORT_FINDING_LIMIT
            if remaining > 0:
                report.append(
                    (f"- ... and {remaining} more violations"),
                )
            report.append("")
        else:
            report.append("**No integrity violations detected**")
            report.append("")

        # Missing data patterns
        if metrics.missing_data_patterns:
            report.append("**Missing Data Analysis:**")
            for pattern_analysis in metrics.missing_data_patterns:
                report.append(
                    (
                        f"- Missing data percentage: "
                        f"{pattern_analysis['missing_percentage']:.2f}%"
                    ),
                )
                if pattern_analysis["patterns"]:
                    report.append("  Patterns detected:")
                    report.extend(
                        f"  - {pattern.get('description', 'Unknown pattern')}"
                        for pattern in pattern_analysis["patterns"]
                    )
            report.append("")
        return report

    def get_quality_metrics_summary(self) -> QualitySummary:
        """Get a summary of all quality metrics.

        Returns:
            Dictionary with summary statistics

        """
        summary: QualitySummary = {
            "total_sheets": len(self.quality_reports),
            "sheets_with_anomalies": 0,
            "sheets_with_violations": 0,
            "total_anomalies": 0,
            "total_violations": 0,
            "average_null_percentage": 0.0,
            "sheets": [],
        }

        null_percentages: list[float] = []

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

            summary["sheets"].append(
                {
                    "sheet_name": metrics.sheet_name,
                    "anomalies": len(metrics.anomalies_detected),
                    "violations": len(metrics.integrity_violations),
                    "null_percentage": metrics.null_percentage,
                    "duplicate_rows": metrics.duplicate_rows,
                },
            )

        if null_percentages:
            summary["average_null_percentage"] = sum(null_percentages) / len(
                null_percentages,
            )

        return summary


# Example usage:
if __name__ == "__main__":
    # This would typically be run through the main application
    pass
