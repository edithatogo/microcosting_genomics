"""Test detailed error logging for genomics microcosting analysis.

This module tests the enhanced error logging capabilities with detailed tracing.
"""

import unittest
import sys
import logging
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.error_handling import (
    ErrorHandler, 
    ErrorContext, 
    ErrorSeverity,
    setup_standard_error_handling,
    DetailedErrorLogger
)


class TestDetailedErrorLogging(unittest.TestCase):
    """Test detailed error logging capabilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a logger for testing
        self.logger = logging.getLogger('test_error_logging')
        self.logger.setLevel(logging.DEBUG)
        
        # Create a temporary log file
        self.temp_log_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
        self.temp_log_file.close()
        
        # Add file handler to logger
        file_handler = logging.FileHandler(self.temp_log_file.name)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.handlers.clear()  # Clear to avoid duplicate handlers
        self.logger.addHandler(file_handler)
        
        # Create error handler
        self.error_handler = ErrorHandler(self.logger)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Close and remove temporary log file
        try:
            os.unlink(self.temp_log_file.name)
        except:
            pass
    
    def test_detailed_error_logging(self):
        """Test detailed error logging with full tracing information."""
        # Create an error context
        context = ErrorContext(
            operation="test_operation",
            data_source="test_data_source",
            module="test_module",
            parameters={'param1': 'value1', 'param2': 'value2'}
        )
        
        # Simulate an error
        try:
            raise ValueError("Test error for detailed logging")
        except Exception as e:
            # Handle the error with detailed logging
            error_record = self.error_handler.handle_error(e, context, ErrorSeverity.MEDIUM)
            
            # Verify error record structure (simple log)
            self.assertIn('id', error_record)
            self.assertIn('timestamp', error_record)
            self.assertIn('operation', error_record)
            self.assertIn('data_source', error_record)
            self.assertIn('error_type', error_record)
            self.assertIn('error_message', error_record)
            self.assertIn('severity', error_record)
            self.assertIn('parameters', error_record)
            self.assertIn('stack_trace', error_record)
            
            # Verify specific values
            self.assertEqual(error_record['operation'], "test_operation")
            self.assertEqual(error_record['data_source'], "test_data_source")
            self.assertEqual(error_record['error_type'], "ValueError")
            self.assertEqual(error_record['error_message'], "Test error for detailed logging")
            self.assertEqual(error_record['severity'], ErrorSeverity.MEDIUM)
            
            # Verify parameters
            self.assertEqual(error_record['parameters']['param1'], 'value1')
            self.assertEqual(error_record['parameters']['param2'], 'value2')
            
            # Get detailed error log to verify it has more information
            detailed_logs = self.error_handler.get_detailed_error_log()
            self.assertGreater(len(detailed_logs), 0)
            
            # Check detailed log has additional fields
            detailed_record = detailed_logs[0]
            self.assertIn('datetime', detailed_record)
            self.assertIn('traceback', detailed_record)
            self.assertIn('frame_info', detailed_record)
            self.assertEqual(detailed_record['operation'], "test_operation")
            self.assertEqual(detailed_record['module'], "test_module")
    
    def test_error_log_retrieval(self):
        """Test retrieval of error logs."""
        # Generate some errors
        context1 = ErrorContext(operation="operation1", data_source="source1")
        context2 = ErrorContext(operation="operation2", data_source="source2")
        
        try:
            raise FileNotFoundError("Test file not found")
        except Exception as e:
            self.error_handler.handle_error(e, context1, ErrorSeverity.HIGH)
        
        try:
            raise KeyError("Test key error")
        except Exception as e:
            self.error_handler.handle_error(e, context2, ErrorSeverity.MEDIUM)
        
        # Get error logs
        simple_log = self.error_handler.get_error_log()
        detailed_log = self.error_handler.get_detailed_error_log()
        
        # Verify log contents
        self.assertEqual(len(simple_log), 2)
        self.assertEqual(len(detailed_log), 2)
        
        # Verify simple log structure
        self.assertEqual(simple_log[0]['operation'], "operation1")
        self.assertEqual(simple_log[0]['error_type'], "FileNotFoundError")
        self.assertEqual(simple_log[1]['operation'], "operation2")
        self.assertEqual(simple_log[1]['error_type'], "KeyError")
        
        # Verify detailed log structure
        self.assertEqual(detailed_log[0]['operation'], "operation1")
        self.assertEqual(detailed_log[0]['error_type'], "FileNotFoundError")
        self.assertEqual(detailed_log[1]['operation'], "operation2")
        self.assertEqual(detailed_log[1]['error_type'], "KeyError")
    
    def test_error_log_persistence(self):
        """Test saving and clearing error logs."""
        # Generate an error
        context = ErrorContext(operation="persistence_test", data_source="test_source")
        
        try:
            raise ValueError("Test persistence error")
        except Exception as e:
            self.error_handler.handle_error(e, context, ErrorSeverity.MEDIUM)
        
        # Save error logs to temporary files
        temp_simple_log = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_detailed_log = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_simple_log.close()
        temp_detailed_log.close()
        
        try:
            # Save logs
            self.error_handler.save_error_log(temp_simple_log.name)
            self.error_handler.save_detailed_error_log(temp_detailed_log.name)
            
            # Verify files were created and have content
            self.assertTrue(os.path.exists(temp_simple_log.name))
            self.assertTrue(os.path.exists(temp_detailed_log.name))
            
            # Check file sizes
            self.assertGreater(os.path.getsize(temp_simple_log.name), 0)
            self.assertGreater(os.path.getsize(temp_detailed_log.name), 0)
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(temp_simple_log.name)
                os.unlink(temp_detailed_log.name)
            except:
                pass
        
        # Test clearing logs
        self.assertEqual(len(self.error_handler.get_error_log()), 1)
        self.assertEqual(len(self.error_handler.get_detailed_error_log()), 1)
        
        self.error_handler.clear_error_log()
        self.error_handler.clear_detailed_error_log()
        
        self.assertEqual(len(self.error_handler.get_error_log()), 0)
        self.assertEqual(len(self.error_handler.get_detailed_error_log()), 0)
    
    def test_detailed_logger_standalone(self):
        """Test DetailedErrorLogger functionality independently."""
        # Create standalone detailed logger
        detailed_logger = DetailedErrorLogger(self.logger)
        
        # Create error context
        context = ErrorContext(
            operation="standalone_test",
            data_source="standalone_source",
            module="standalone_module"
        )
        
        # Simulate error
        try:
            raise RuntimeError("Standalone test error")
        except Exception as e:
            error_record = detailed_logger.log_detailed_error(e, context, ErrorSeverity.HIGH)
            
            # Verify detailed error record
            self.assertIn('id', error_record)
            self.assertIn('datetime', error_record)
            self.assertIn('traceback', error_record)
            self.assertIn('frame_info', error_record)
            
            self.assertEqual(error_record['operation'], "standalone_test")
            self.assertEqual(error_record['data_source'], "standalone_source")
            self.assertEqual(error_record['module'], "standalone_module")
            self.assertEqual(error_record['error_type'], "RuntimeError")
            self.assertEqual(error_record['severity'], ErrorSeverity.HIGH)
    
    def test_error_severity_handling(self):
        """Test that different error severities are handled correctly."""
        context = ErrorContext(operation="severity_test", data_source="test_source")
        
        # Test critical error
        try:
            raise SystemError("Critical system error")
        except Exception as e:
            error_record = self.error_handler.handle_error(e, context, ErrorSeverity.CRITICAL)
            self.assertEqual(error_record['severity'], ErrorSeverity.CRITICAL)
        
        # Test high error
        try:
            raise RuntimeError("High severity error")
        except Exception as e:
            error_record = self.error_handler.handle_error(e, context, ErrorSeverity.HIGH)
            self.assertEqual(error_record['severity'], ErrorSeverity.HIGH)
        
        # Test medium error
        try:
            raise ValueError("Medium severity error")
        except Exception as e:
            error_record = self.error_handler.handle_error(e, context, ErrorSeverity.MEDIUM)
            self.assertEqual(error_record['severity'], ErrorSeverity.MEDIUM)
        
        # Test low error
        try:
            raise Warning("Low severity warning")
        except Exception as e:
            error_record = self.error_handler.handle_error(e, context, ErrorSeverity.LOW)
            self.assertEqual(error_record['severity'], ErrorSeverity.LOW)


if __name__ == '__main__':
    unittest.main()