"""Test error recovery scenarios for genomics microcosting analysis.

This module tests various error recovery scenarios to ensure the system can
gracefully handle and recover from different types of errors.
"""

import unittest
import sys
import logging
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.error_handling import (  # noqa: E402
    ErrorContext, 
    ErrorSeverity,
    setup_standard_error_handling
)
from genomics_microcosting.input_validation import InputValidator  # noqa: E402


class TestErrorRecoveryScenarios(unittest.TestCase):
    """Test error recovery scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a logger for testing
        self.logger = logging.getLogger('test_error_recovery')
        self.logger.setLevel(logging.DEBUG)
        
        # Create temporary directory for checkpoints
        self.temp_checkpoint_dir = tempfile.mkdtemp()
        
        # Create error handler with checkpoint directory
        self.error_handler = setup_standard_error_handling(
            logger=self.logger, 
            checkpoint_dir=self.temp_checkpoint_dir
        )
        
        # Create input validator
        self.validator = InputValidator(self.logger)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary checkpoint directory
        try:
            shutil.rmtree(self.temp_checkpoint_dir)
        except (OSError, FileNotFoundError):
            pass
    
    def test_missing_data_source_recovery(self):
        """Test recovery from missing data source errors."""
        # Create a function that might fail due to missing data
        @self.error_handler.graceful_degradation(
            operation="load_analysis_data",
            default_value=pd.DataFrame(),
            data_source="missing_analysis_data.xlsx"
        )
        def load_analysis_data(file_path):
            """Simulate loading analysis data that might fail."""
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Analysis data file not found: {file_path}")
            # Simulate successful loading
            return pd.DataFrame({"test": [1, 2, 3]})
        
        # This will fail gracefully and return default value
        result = load_analysis_data("nonexistent_file.xlsx")
        
        # Verify default value is returned
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        
        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        self.assertEqual(len(error_logs), 1)
        self.assertEqual(error_logs[0]['error_type'], 'FileNotFoundError')
        self.assertEqual(error_logs[0]['operation'], 'load_analysis_data')
    
    def test_invalid_input_recovery(self):
        """Test recovery from invalid input errors."""
        # Create a function that validates input and handles validation errors
        @self.error_handler.graceful_degradation(
            operation="process_cost_data",
            default_value=0.0,
            data_source="cost_calculation"
        )
        def process_cost_data(cost_value):
            """Process cost data with validation."""
            # Validate input
            self.validator.validate_numeric_value(cost_value, min_value=0)
            # Process the cost value
            return cost_value * 1.1  # Add 10% markup
        
        # Test with valid input
        result = process_cost_data(1000)
        self.assertEqual(result, 1100.0)
        
        # Test with invalid input (negative value)
        result = process_cost_data(-500)
        # Should return default value due to validation error
        self.assertEqual(result, 0.0)
        
        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        self.assertGreaterEqual(len(error_logs), 1)
        # Find the validation error
        validation_errors = [e for e in error_logs if 'ValidationError' in str(e.get('error_type', '')) or 'less than minimum' in str(e.get('error_message', ''))]
        self.assertGreaterEqual(len(validation_errors), 1)
    
    def test_calculation_error_recovery(self):
        """Test recovery from calculation errors."""
        # Create a function that might have calculation errors
        @self.error_handler.graceful_degradation(
            operation="calculate_ratio",
            default_value=1.0,
            data_source="ratio_calculation"
        )
        def calculate_ratio(numerator, denominator):
            """Calculate ratio with potential division by zero."""
            if denominator == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return numerator / denominator
        
        # Test normal calculation
        result = calculate_ratio(10, 2)
        self.assertEqual(result, 5.0)
        
        # Test division by zero recovery
        result = calculate_ratio(10, 0)
        # Should return default value due to ZeroDivisionError
        self.assertEqual(result, 1.0)
        
        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        zero_div_errors = [e for e in error_logs if e.get('error_type') == 'ZeroDivisionError']
        self.assertGreaterEqual(len(zero_div_errors), 1)
    
    def test_checkpoint_recovery_scenario(self):
        """Test recovery using checkpoints after an error."""
        # Simulate a multi-step analysis process
        analysis_steps = [
            {"step": "data_loading", "data": {"samples": 100}},
            {"step": "preprocessing", "data": {"samples": 100, "features": 50}},
            {"step": "analysis", "data": {"results": [1, 2, 3, 4, 5]}},
            {"step": "reporting", "data": {"summary": "Analysis complete"}}
        ]
        
        completed_steps = []
        
        # Process each step and create checkpoints
        for i, step in enumerate(analysis_steps):
            try:
                # Simulate step processing
                if step["step"] == "analysis" and i == 2:
                    # Simulate an error in the analysis step
                    raise RuntimeError("Analysis failed due to resource constraints")
                
                # Create checkpoint for successful step
                checkpoint_id = self.error_handler.create_checkpoint(
                    f"analysis_step_{i}",
                    step["data"],
                    {"step_name": step["step"], "status": "completed"}
                )
                completed_steps.append((step["step"], checkpoint_id))
                
            except Exception as e:
                context = ErrorContext(
                    operation=f"analysis_step_{i}",
                    data_source=step["step"],
                    parameters={"step_data": step}
                )
                self.error_handler.handle_error(e, context, ErrorSeverity.HIGH)
                
                # Try to recover using last successful checkpoint
                if completed_steps:
                    last_step_name, last_checkpoint_id = completed_steps[-1]
                    recovered_data = self.error_handler.restore_checkpoint(last_checkpoint_id)
                    self.assertIsNotNone(recovered_data)
                    # Log recovery information
                    self.logger.info(f"Recovered from checkpoint {last_checkpoint_id} for step {last_step_name}")
                break
        
        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        runtime_errors = [e for e in error_logs if e.get('error_type') == 'RuntimeError']
        self.assertGreaterEqual(len(runtime_errors), 1)
        
        # Verify checkpoints were created
        checkpoints = self.error_handler.list_checkpoints()
        self.assertGreaterEqual(len(checkpoints), 2)  # At least 2 successful steps
    
    def test_data_quality_error_recovery(self):
        """Test recovery from data quality issues."""
        # Create test data with quality issues
        test_data = pd.DataFrame({
            'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS', None],  # Missing value
            'Cost': [50000, 75000, 40000, 60000, -1000],  # Negative value
            'Quantity': [100, 200, np.nan, 150, 80]  # NaN value
        })
        
        # Function to process data with quality checks
        @self.error_handler.graceful_degradation(
            operation="process_genomic_data",
            default_value=pd.DataFrame(),
            data_source="genomic_cost_data"
        )
        def process_genomic_data(df):
            """Process genomic data with quality validation."""
            # Validate data structure
            self.validator.validate_dataframe(df, min_rows=1)
            
            # Check for negative costs
            negative_costs = df[df['Cost'] < 0]
            if not negative_costs.empty:
                raise ValueError(f"Found {len(negative_costs)} negative cost values")
            
            # Check for missing test names
            missing_tests = df[df['Test'].isnull()]
            if not missing_tests.empty:
                raise ValueError(f"Found {len(missing_tests)} missing test names")
            
            # Process valid data
            processed_df = df.copy()
            processed_df['Total_Cost'] = processed_df['Cost'] * processed_df['Quantity'].fillna(1)
            return processed_df
        
        # Test with problematic data
        result = process_genomic_data(test_data)
        
        # Should return default value due to data quality issues
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        
        # Verify errors were logged
        error_logs = self.error_handler.get_error_log()
        value_errors = [e for e in error_logs if e.get('error_type') == 'ValueError']
        self.assertGreaterEqual(len(value_errors), 1)
    
    def test_nested_error_recovery(self):
        """Test recovery from nested error scenarios."""
        # Create nested functions that might fail
        @self.error_handler.graceful_degradation(
            operation="outer_calculation",
            default_value=0,
            data_source="nested_calculation"
        )
        def outer_calculation(x, y):
            """Outer calculation that calls inner calculation."""
            intermediate_result = inner_calculation(x)
            return intermediate_result + y
        
        @self.error_handler.graceful_degradation(
            operation="inner_calculation",
            default_value=1,
            data_source="nested_calculation"
        )
        def inner_calculation(x):
            """Inner calculation that might fail."""
            if x < 0:
                raise ValueError("Input must be non-negative")
            return x * 2
        
        # Test normal operation
        result = outer_calculation(5, 3)
        self.assertEqual(result, 13)  # (5 * 2) + 3
        
        # Test error in inner calculation
        result = outer_calculation(-5, 3)
        # Should recover using default values: (1) + 3 = 4
        self.assertEqual(result, 4)
        
        # Verify errors were logged
        error_logs = self.error_handler.get_error_log()
        value_errors = [e for e in error_logs if e.get('error_type') == 'ValueError']
        self.assertGreaterEqual(len(value_errors), 1)
    
    def test_resource_exhaustion_recovery(self):
        """Test recovery from resource exhaustion errors."""
        # Simulate memory-intensive operation
        @self.error_handler.graceful_degradation(
            operation="memory_intensive_operation",
            default_value=[],
            data_source="large_dataset"
        )
        def memory_intensive_operation(size):
            """Simulate memory-intensive operation."""
            if size > 1000000:
                # Simulate MemoryError
                raise MemoryError("Not enough memory to process large dataset")
            
            # Simulate successful operation
            return list(range(min(size, 1000)))  # Limit to prevent actual memory issues
        
        # Test normal operation
        result = memory_intensive_operation(100)
        self.assertEqual(len(result), 100)
        
        # Test memory exhaustion recovery
        result = memory_intensive_operation(2000000)
        # Should return default value due to MemoryError
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        
        # Verify error was logged
        error_logs = self.error_handler.get_error_log()
        memory_errors = [e for e in error_logs if 'Memory' in str(e.get('error_type', ''))]
        self.assertGreaterEqual(len(memory_errors), 1)
    
    def test_persistent_recovery_scenario(self):
        """Test recovery using persistent checkpoints after application restart."""
        # Simulate long-running analysis with persistent checkpoints
        analysis_phases = [
            {"phase": "data_ingestion", "progress": 25},
            {"phase": "data_processing", "progress": 50},
            {"phase": "analysis_execution", "progress": 75},
            {"phase": "report_generation", "progress": 100}
        ]
        
        # Create checkpoints for each phase
        checkpoint_ids = []
        for i, phase in enumerate(analysis_phases):
            checkpoint_id = self.error_handler.create_checkpoint(
                f"analysis_phase_{i}",
                phase,
                {"phase_name": phase["phase"], "progress": phase["progress"]}
            )
            checkpoint_ids.append(checkpoint_id)
        
        # Simulate application restart by creating new error handler
        new_error_handler = setup_standard_error_handling(
            logger=self.logger, 
            checkpoint_dir=self.temp_checkpoint_dir
        )
        
        # Verify checkpoints can be restored from disk
        restored_checkpoints = []
        for checkpoint_id in checkpoint_ids:
            restored_data = new_error_handler.restore_checkpoint(checkpoint_id, from_disk=True)
            self.assertIsNotNone(restored_data)
            restored_checkpoints.append(restored_data)
        
        self.assertEqual(len(restored_checkpoints), len(analysis_phases))
        
        # Verify checkpoint metadata
        listed_checkpoints = new_error_handler.list_checkpoints()
        self.assertEqual(len(listed_checkpoints), len(analysis_phases))
        
        # Test continuing from last checkpoint
        last_checkpoint = restored_checkpoints[-1]
        self.assertEqual(last_checkpoint["phase"], "report_generation")
        self.assertEqual(last_checkpoint["progress"], 100)


if __name__ == '__main__':
    unittest.main()