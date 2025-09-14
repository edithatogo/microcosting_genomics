"""Test cases for the Data Quality Assurance module."""

import unittest
import sys
import pandas as pd
from unittest.mock import Mock, patch
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.data_quality_assurance import (  # noqa: E402
    DataQualityAssurance,
    DataAnomalyDetector,
    MissingDataHandler,
    DataIntegrityVerifier,
    DataQualityMetrics
)
from genomics_microcosting.data_manager import DataManager  # noqa: E402


class TestDataQualityAssurance(unittest.TestCase):
    """Test cases for the DataQualityAssurance class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.quality_assurance = DataQualityAssurance(self.mock_data_manager)
        
    def test_init(self):
        """Test DataQualityAssurance initialization."""
        self.assertIsInstance(self.quality_assurance, DataQualityAssurance)
        self.assertEqual(self.quality_assurance.data_manager, self.mock_data_manager)
        self.assertIsInstance(self.quality_assurance.anomaly_detector, DataAnomalyDetector)
        self.assertIsInstance(self.quality_assurance.missing_data_handler, MissingDataHandler)
        self.assertIsInstance(self.quality_assurance.integrity_verifier, DataIntegrityVerifier)
        
    def test_assess_data_quality(self):
        """Test data quality assessment."""
        # Create test DataFrame
        df = pd.DataFrame({
            'cost': [100, 200, 300, 400, 500],
            'quantity': [1, 2, 3, 4, 5],
            'description': ['A', 'B', 'C', 'D', 'E']
        })
        
        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df
        
        with patch('genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity') as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0
                }
            }
            
            # Assess data quality
            metrics = self.quality_assurance.assess_data_quality(
                "Test Sheet", 
                cost_columns=['cost'],
                expected_ranges={'cost': (0, 1000)},
                unique_columns=['description']
            )
            
            # Check results
            self.assertIsInstance(metrics, DataQualityMetrics)
            self.assertEqual(metrics.sheet_name, "Test Sheet")
            self.assertGreater(len(self.quality_assurance.quality_reports), 0)
            
    def test_assess_data_quality_with_anomalies(self):
        """Test data quality assessment with anomalies."""
        # Create test DataFrame with anomalies
        df = pd.DataFrame({
            'cost': [100, 200, 300, 400, 50000],  # Last value is an outlier
            'quantity': [1, 2, 3, 4, 5],
            'description': ['A', 'B', 'C', 'D', 'E']
        })
        
        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df
        
        with patch('genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity') as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0
                }
            }
            
            # Assess data quality
            metrics = self.quality_assurance.assess_data_quality(
                "Test Sheet", 
                cost_columns=['cost']
            )
            
            # Check results
            self.assertIsInstance(metrics, DataQualityMetrics)
            
    def test_generate_quality_report(self):
        """Test quality report generation."""
        # Create test DataFrame
        df = pd.DataFrame({
            'cost': [100, 200, 300, 400, 500],
            'quantity': [1, 2, 3, 4, 5],
            'description': ['A', 'B', 'C', 'D', 'E']
        })
        
        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df
        
        with patch('genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity') as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0
                }
            }
            
            # Assess data quality
            self.quality_assurance.assess_data_quality("Test Sheet", cost_columns=['cost'])
            
            # Generate report
            report = self.quality_assurance.generate_quality_report()
            
            # Check that report is generated
            self.assertIsInstance(report, str)
            self.assertGreater(len(report), 0)
            self.assertIn("Genomics Microcosting Data Quality Report", report)
            self.assertIn("Test Sheet", report)
            
    def test_get_quality_metrics_summary(self):
        """Test quality metrics summary."""
        # Create test DataFrame
        df = pd.DataFrame({
            'cost': [100, 200, 300, 400, 500],
            'quantity': [1, 2, 3, 4, 5],
            'description': ['A', 'B', 'C', 'D', 'E']
        })
        
        # Mock the data manager and consistency validator
        self.mock_data_manager.load_sheet.return_value = df
        
        with patch('genomics_microcosting.data_consistency_validator.DataConsistencyValidator.validate_sheet_integrity') as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "errors": [],
                "warnings": [],
                "metrics": {
                    "null_percentage": 0.0,
                    "duplicate_rows": 0
                }
            }
            
            # Assess data quality
            self.quality_assurance.assess_data_quality("Test Sheet", cost_columns=['cost'])
            
            # Get summary
            summary = self.quality_assurance.get_quality_metrics_summary()
            
            # Check summary
            self.assertIsInstance(summary, dict)
            self.assertEqual(summary["total_sheets"], 1)
            self.assertEqual(summary["sheets_with_anomalies"], 0)
            self.assertEqual(summary["sheets_with_violations"], 0)
            self.assertEqual(len(summary["sheets"]), 1)


class TestDataAnomalyDetector(unittest.TestCase):
    """Test cases for the DataAnomalyDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.anomaly_detector = DataAnomalyDetector()
        
    def test_detect_cost_anomalies(self):
        """Test cost anomaly detection."""
        # Create test DataFrame with anomalies
        df = pd.DataFrame({
            'cost': [100, 200, 300, 400, -50],  # Negative value
            'other_cost': [50, 60, 70, 80, -10]   # Negative value
        })
        
        anomalies = self.anomaly_detector.detect_cost_anomalies(df, ['cost', 'other_cost'])
        
        # Check that anomalies were detected
        self.assertIsInstance(anomalies, list)
        self.assertGreater(len(anomalies), 0)
        
        # Check for specific anomaly types
        anomaly_types = [a['type'] for a in anomalies]
        self.assertIn('negative_cost', anomaly_types)
        
    def test_detect_pattern_anomalies(self):
        """Test pattern anomaly detection."""
        # Create test DataFrame with pattern anomalies
        df = pd.DataFrame({
            'text_col': ['aaaaaa', 'bbbbb', 'normal', 'cccccc'],  # Repeated characters
            'numeric_col': [1, 2, 3, 4]  # All numeric
        })
        
        anomalies = self.anomaly_detector.detect_pattern_anomalies(df)
        
        # Check that anomalies were detected
        self.assertIsInstance(anomalies, list)


class TestMissingDataHandler(unittest.TestCase):
    """Test cases for the MissingDataHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.missing_data_handler = MissingDataHandler()
        
    def test_analyze_missing_data_patterns(self):
        """Test missing data pattern analysis."""
        # Create test DataFrame with missing data
        df = pd.DataFrame({
            'A': [1, 2, None, 4, 5],
            'B': [None, None, None, None, None],  # Completely missing
            'C': [1, 2, 3, 4, 5]
        })
        
        analysis = self.missing_data_handler.analyze_missing_data_patterns(df)
        
        # Check analysis results
        self.assertIsInstance(analysis, dict)
        self.assertGreater(analysis['missing_percentage'], 0)
        self.assertIn('B', analysis['columns_with_missing'])
        self.assertGreater(len(analysis['patterns']), 0)
        
    def test_suggest_missing_data_strategies(self):
        """Test missing data strategy suggestions."""
        # Create mock analysis with high missing percentage
        mock_analysis = {
            "missing_percentage": 25.0,
            "columns_with_missing": {
                "A": {"percentage": 20.0},
                "B": {"percentage": 100.0}  # Completely missing
            },
            "patterns": []
        }
        
        strategies = self.missing_data_handler.suggest_missing_data_strategies(mock_analysis)
        
        # Check strategies
        self.assertIsInstance(strategies, list)
        self.assertGreater(len(strategies), 0)
        
        # Check for specific strategies
        strategy_names = [s['strategy'] for s in strategies]
        self.assertIn('advanced_imputation', strategy_names)


class TestDataIntegrityVerifier(unittest.TestCase):
    """Test cases for the DataIntegrityVerifier class."""

    def setUp(self):
        """Set up test fixtures."""
        self.integrity_verifier = DataIntegrityVerifier()
        
    def test_verify_cost_integrity(self):
        """Test cost integrity verification."""
        # Create test DataFrame with invalid cost data
        df = pd.DataFrame({
            'cost': [100, 200, -50, 400, 'invalid'],  # Negative and non-numeric values
            'other_cost': [50, 60, 70, 80, 90]
        })
        
        violations = self.integrity_verifier.verify_cost_integrity(df, ['cost', 'other_cost'])
        
        # Check violations
        self.assertIsInstance(violations, list)
        self.assertGreater(len(violations), 0)
        
        # Check for specific violation types
        violation_types = [v['type'] for v in violations]
        self.assertIn('non_numeric_cost_column', violation_types)
        
    def test_verify_cross_sheet_integrity(self):
        """Test cross-sheet integrity verification."""
        # Create mock data manager
        mock_data_manager = Mock(spec=DataManager)
        mock_data_manager.load_sheet.side_effect = [
            pd.DataFrame({'A': [1, 2, 3]}),  # Found sheet
            None,  # Missing sheet
            pd.DataFrame({'A': [1, 2, 3]}),  # Found sheet
            None   # Missing sheet
        ]
        
        # Test dependencies
        sheet_dependencies = {
            "Main Sheet": ["Found Sheet", "Missing Sheet"]
        }
        
        violations = self.integrity_verifier.verify_cross_sheet_integrity(
            mock_data_manager, sheet_dependencies)
        
        # Check violations
        self.assertIsInstance(violations, list)
        self.assertGreater(len(violations), 0)
        
        # Check for specific violation types
        violation_types = [v['type'] for v in violations]
        self.assertIn('dependency_missing', violation_types)


if __name__ == '__main__':
    unittest.main()