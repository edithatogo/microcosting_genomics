# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Data Quality Assurance module."""

import unittest
from unittest.mock import Mock, patch

import polars as pl

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.data_quality_assurance import (
    DataAnomalyDetector,
    DataIntegrityVerifier,
    DataQualityAssurance,
    DataQualityMetrics,
    MissingDataHandler,
    MissingDataPercentages,
)
from tests.checks import require_runtime_instance


class TestDataQualityAssurance(unittest.TestCase):
    """Test cases for the DataQualityAssurance class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.quality_assurance = DataQualityAssurance(self.mock_data_manager)

    def test_init(self) -> None:
        """Test DataQualityAssurance initialization."""
        require_runtime_instance(self.quality_assurance, DataQualityAssurance)
        if not ((self.quality_assurance.data_manager) == (self.mock_data_manager)):
            raise AssertionError
        require_runtime_instance(
            self.quality_assurance.anomaly_detector,
            DataAnomalyDetector,
        )
        require_runtime_instance(
            self.quality_assurance.missing_data_handler,
            MissingDataHandler,
        )
        require_runtime_instance(
            self.quality_assurance.integrity_verifier,
            DataIntegrityVerifier,
        )

    def test_assess_data_quality(self) -> None:
        """Test data quality assessment."""
        # Create test DataFrame
        df = pl.DataFrame(
            {
                "cost": [100, 200, 300, 400, 500],
                "quantity": [1, 2, 3, 4, 5],
                "description": ["A", "B", "C", "D", "E"],
            },
            strict=False,
        )

        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df

        with patch(
            "genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity",
        ) as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0,
                },
            }

            # Assess data quality
            metrics = self.quality_assurance.assess_data_quality(
                "Test Sheet",
                cost_columns=["cost"],
                expected_ranges={"cost": (0, 1000)},
                unique_columns=["description"],
            )

            # Check results
            require_runtime_instance(metrics, DataQualityMetrics)
            if not ((metrics.sheet_name) == ("Test Sheet")):
                raise AssertionError
            if not ((len(self.quality_assurance.quality_reports)) > (0)):
                raise AssertionError

    def test_assess_data_quality_with_anomalies(self) -> None:
        """Test data quality assessment with anomalies."""
        # Create test DataFrame with anomalies
        df = pl.DataFrame(
            {
                "cost": [100, 200, 300, 400, 50000],  # Last value is an outlier
                "quantity": [1, 2, 3, 4, 5],
                "description": ["A", "B", "C", "D", "E"],
            },
            strict=False,
        )

        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df

        with patch(
            "genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity",
        ) as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0,
                },
            }

            # Assess data quality
            metrics = self.quality_assurance.assess_data_quality(
                "Test Sheet",
                cost_columns=["cost"],
            )

            # Check results
            require_runtime_instance(metrics, DataQualityMetrics)

    def test_generate_quality_report(self) -> None:
        """Test quality report generation."""
        # Create test DataFrame
        df = pl.DataFrame(
            {
                "cost": [100, 200, 300, 400, 500],
                "quantity": [1, 2, 3, 4, 5],
                "description": ["A", "B", "C", "D", "E"],
            },
            strict=False,
        )

        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df

        with patch(
            "genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity",
        ) as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0,
                },
            }

            # Assess data quality
            self.quality_assurance.assess_data_quality(
                "Test Sheet",
                cost_columns=["cost"],
            )

            # Generate report
            report = self.quality_assurance.generate_quality_report()

            # Check that report is generated
            require_runtime_instance(report, str)
            if not ((len(report)) > (0)):
                raise AssertionError
            if ("Genomics Microcosting Data Quality Report") not in (report):
                raise AssertionError
            if ("Test Sheet") not in (report):
                raise AssertionError

    def test_get_quality_metrics_summary(self) -> None:
        """Test quality metrics summary."""
        # Create test DataFrame
        df = pl.DataFrame(
            {
                "cost": [100, 200, 300, 400, 500],
                "quantity": [1, 2, 3, 4, 5],
                "description": ["A", "B", "C", "D", "E"],
            },
            strict=False,
        )

        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df

        with patch(
            "genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity",
        ) as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0,
                },
            }

            # Assess data quality
            self.quality_assurance.assess_data_quality(
                "Test Sheet",
                cost_columns=["cost"],
            )

            # Get summary
            summary = self.quality_assurance.get_quality_metrics_summary()

            # Check summary
            require_runtime_instance(summary, dict)
            if not ((summary["total_sheets"]) == (1)):
                raise AssertionError
            if not ((summary["sheets_with_anomalies"]) == (0)):
                raise AssertionError
            if not ((summary["sheets_with_violations"]) == (0)):
                raise AssertionError
            if not ((len(summary["sheets"])) == (1)):
                raise AssertionError


class TestDataAnomalyDetector(unittest.TestCase):
    """Test cases for the DataAnomalyDetector class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.anomaly_detector = DataAnomalyDetector()

    def test_detect_cost_anomalies(self) -> None:
        """Test cost anomaly detection."""
        # Create test DataFrame with anomalies
        df = pl.DataFrame(
            {
                "cost": [100, 200, 300, 400, -50],  # Negative value
                "other_cost": [50, 60, 70, 80, -10],  # Negative value
            },
            strict=False,
        )

        anomalies = self.anomaly_detector.detect_cost_anomalies(
            df,
            ["cost", "other_cost"],
        )

        # Check that anomalies were detected
        require_runtime_instance(anomalies, list)
        if not ((len(anomalies)) > (0)):
            raise AssertionError

        # Check for specific anomaly types
        anomaly_types = [a["type"] for a in anomalies]
        if ("negative_cost") not in (anomaly_types):
            raise AssertionError

    def test_detect_pattern_anomalies(self) -> None:
        """Test pattern anomaly detection."""
        # Create test DataFrame with pattern anomalies
        df = pl.DataFrame(
            {
                "text_col": [
                    "aaaaaa",
                    "bbbbb",
                    "normal",
                    "cccccc",
                ],  # Repeated characters
                "numeric_col": [1, 2, 3, 4],  # All numeric
            },
            strict=False,
        )

        anomalies = self.anomaly_detector.detect_pattern_anomalies(df)

        # Check that anomalies were detected
        require_runtime_instance(anomalies, list)


class TestMissingDataHandler(unittest.TestCase):
    """Test cases for the MissingDataHandler class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.missing_data_handler = MissingDataHandler()

    def test_analyze_missing_data_patterns(self) -> None:
        """Test missing data pattern analysis."""
        # Create test DataFrame with missing data
        df = pl.DataFrame(
            {
                "A": [1, 2, None, 4, 5],
                "B": [None, None, None, None, None],  # Completely missing
                "C": [1, 2, 3, 4, 5],
            },
            strict=False,
        )

        analysis = self.missing_data_handler.analyze_missing_data_patterns(df)

        # Check analysis results
        require_runtime_instance(analysis, dict)
        if not ((analysis["missing_percentage"]) > (0)):
            raise AssertionError
        if ("B") not in (analysis["columns_with_missing"]):
            raise AssertionError
        if not ((len(analysis["patterns"])) > (0)):
            raise AssertionError

    def test_suggest_missing_data_strategies(self) -> None:
        """Test missing data strategy suggestions."""
        # Create mock analysis with high missing percentage
        mock_analysis: MissingDataPercentages = {
            "missing_percentage": 25.0,
            "columns_with_missing": {
                "A": {"count": 2, "percentage": 20.0},
                "B": {"count": 10, "percentage": 100.0},  # Completely missing
            },
        }

        strategies = self.missing_data_handler.suggest_missing_data_strategies(
            mock_analysis,
        )

        # Check strategies
        require_runtime_instance(strategies, list)
        if not ((len(strategies)) > (0)):
            raise AssertionError

        # Check for specific strategies
        strategy_names = [s["strategy"] for s in strategies]
        if ("advanced_imputation") not in (strategy_names):
            raise AssertionError


class TestDataIntegrityVerifier(unittest.TestCase):
    """Test cases for the DataIntegrityVerifier class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.integrity_verifier = DataIntegrityVerifier()

    def test_verify_cost_integrity(self) -> None:
        """Test cost integrity verification."""
        # Create test DataFrame with invalid cost data
        df = pl.DataFrame(
            {
                "cost": [
                    100,
                    200,
                    -50,
                    400,
                    "invalid",
                ],  # Negative and non-numeric values
                "other_cost": [50, 60, 70, 80, 90],
            },
            strict=False,
        )

        violations = self.integrity_verifier.verify_cost_integrity(
            df,
            ["cost", "other_cost"],
        )

        # Check violations
        require_runtime_instance(violations, list)
        if not ((len(violations)) > (0)):
            raise AssertionError

        # Check for specific violation types
        violation_types = [v["type"] for v in violations]
        if ("non_numeric_cost_column") not in (violation_types):
            raise AssertionError

    def test_verify_cross_sheet_integrity(self) -> None:
        """Test cross-sheet integrity verification."""
        # Create mock data manager
        mock_data_manager = Mock(spec=DataManager)
        mock_data_manager.load_sheet.side_effect = [
            pl.DataFrame({"A": [1, 2, 3]}),  # Found sheet
            None,  # Missing sheet
            pl.DataFrame({"A": [1, 2, 3]}),  # Found sheet
            None,  # Missing sheet
        ]

        # Test dependencies
        sheet_dependencies = {
            "Main Sheet": ["Found Sheet", "Missing Sheet"],
        }

        violations = self.integrity_verifier.verify_cross_sheet_integrity(
            mock_data_manager,
            sheet_dependencies,
        )

        # Check violations
        require_runtime_instance(violations, list)
        if not ((len(violations)) > (0)):
            raise AssertionError

        # Check for specific violation types
        violation_types = [v["type"] for v in violations]
        if ("dependency_missing") not in (violation_types):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
