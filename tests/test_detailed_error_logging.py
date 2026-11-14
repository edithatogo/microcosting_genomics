# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test detailed error logging for genomics microcosting analysis.

This module tests the enhanced error logging capabilities with detailed tracing.
"""

import contextlib
import logging
import tempfile
import unittest
from pathlib import Path

from genomics_microcosting.error_handling import (
    DetailedErrorLogger,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
)
from tests.checks import require, require_equal, require_keys


def _raise_test_error(error: Exception) -> None:
    raise error


class TestDetailedErrorLogging(unittest.TestCase):
    """Test detailed error logging capabilities."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a logger for testing
        self.logger = logging.getLogger("test_error_logging")
        self.logger.setLevel(logging.DEBUG)

        # Create a temporary log file
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.log_path = Path(temporary.name) / "detailed.log"

        # Add file handler to logger
        file_handler = logging.FileHandler(self.log_path)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        file_handler.setFormatter(formatter)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()
        self.logger.addHandler(file_handler)

        # Create error handler
        self.error_handler = ErrorHandler(self.logger)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()
        # Close and remove temporary log file
        with contextlib.suppress(OSError, FileNotFoundError):
            Path(self.log_path).unlink()

    def test_detailed_error_logging(self) -> None:
        """Test detailed error logging with full tracing information."""
        # Create an error context
        context = ErrorContext(
            operation="test_operation",
            data_source="test_data_source",
            module="test_module",
            parameters={"param1": "value1", "param2": "value2"},
        )

        # Simulate an error
        try:
            message = "Test error for detailed logging"
            _raise_test_error(ValueError(message))
        except ValueError as e:
            # Handle the error with detailed logging
            error_record = self.error_handler.handle_error(
                e,
                context,
                ErrorSeverity.MEDIUM,
            )

            # Verify error record structure (simple log)
            require_keys(error_record, ("id",))
            require_keys(error_record, ("timestamp",))
            require_keys(error_record, ("operation",))
            require_keys(error_record, ("data_source",))
            require_keys(error_record, ("error_type",))
            require_keys(error_record, ("error_message",))
            require_keys(error_record, ("severity",))
            require_keys(error_record, ("parameters",))
            require_keys(error_record, ("stack_trace",))

            # Verify specific values
            require_equal(error_record["operation"], "test_operation")
            require_equal(error_record["data_source"], "test_data_source")
            require_equal(error_record["error_type"], "ValueError")
            require_equal(
                error_record["error_message"],
                "Test error for detailed logging",
            )
            require_equal(error_record["severity"], ErrorSeverity.MEDIUM)

            # Verify parameters
            require_equal(error_record["parameters"]["param1"], "value1")
            require_equal(error_record["parameters"]["param2"], "value2")

            # Get detailed error log to verify it has more information
            detailed_logs = self.error_handler.get_detailed_error_log()
            require(condition=len(detailed_logs) > 0)

            # Check detailed log has additional fields
            detailed_record = detailed_logs[0]
            require_keys(detailed_record, ("datetime",))
            require_keys(detailed_record, ("traceback",))
            require_keys(detailed_record, ("frame_info",))
            require_equal(detailed_record["operation"], "test_operation")
            require_equal(detailed_record["module"], "test_module")

    def test_error_log_retrieval(self) -> None:
        """Test retrieval of error logs."""
        # Generate some errors
        context1 = ErrorContext(operation="operation1", data_source="source1")
        context2 = ErrorContext(operation="operation2", data_source="source2")

        try:
            message = "Test file not found"
            _raise_test_error(FileNotFoundError(message))
        except FileNotFoundError as e:
            self.error_handler.handle_error(e, context1, ErrorSeverity.HIGH)

        try:
            message = "Test key error"
            _raise_test_error(KeyError(message))
        except KeyError as e:
            self.error_handler.handle_error(e, context2, ErrorSeverity.MEDIUM)

        # Get error logs
        simple_log = self.error_handler.get_error_log()
        detailed_log = self.error_handler.get_detailed_error_log()

        # Verify log contents
        require_equal(len(simple_log), 2)
        require_equal(len(detailed_log), 2)

        # Verify simple log structure
        require_equal(simple_log[0]["operation"], "operation1")
        require_equal(simple_log[0]["error_type"], "FileNotFoundError")
        require_equal(simple_log[1]["operation"], "operation2")
        require_equal(simple_log[1]["error_type"], "KeyError")

        # Verify detailed log structure
        require_equal(detailed_log[0]["operation"], "operation1")
        require_equal(detailed_log[0]["error_type"], "FileNotFoundError")
        require_equal(detailed_log[1]["operation"], "operation2")
        require_equal(detailed_log[1]["error_type"], "KeyError")

    def test_error_log_persistence(self) -> None:
        """Test saving and clearing error logs."""
        # Generate an error
        context = ErrorContext(operation="persistence_test", data_source="test_source")

        try:
            message = "Test persistence error"
            _raise_test_error(ValueError(message))
        except ValueError as e:
            self.error_handler.handle_error(e, context, ErrorSeverity.MEDIUM)

        # Save error logs to temporary files
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        simple_path = Path(temporary.name) / "simple.json"
        detailed_path = Path(temporary.name) / "detailed.json"

        try:
            # Save logs
            self.error_handler.save_error_log(str(simple_path))
            self.error_handler.save_detailed_error_log(str(detailed_path))

            # Verify files were created and have content
            require(condition=simple_path.exists())
            require(condition=detailed_path.exists())

            # Check file sizes
            require(condition=simple_path.stat().st_size > 0)
            require(condition=detailed_path.stat().st_size > 0)

        finally:
            # Clean up temporary files
            try:
                simple_path.unlink()
                detailed_path.unlink()
            except OSError, FileNotFoundError:
                pass

        # Test clearing logs
        require_equal(len(self.error_handler.get_error_log()), 1)
        require_equal(len(self.error_handler.get_detailed_error_log()), 1)

        self.error_handler.clear_error_log()
        self.error_handler.clear_detailed_error_log()

        require_equal(len(self.error_handler.get_error_log()), 0)
        require_equal(len(self.error_handler.get_detailed_error_log()), 0)

    def test_detailed_logger_standalone(self) -> None:
        """Test DetailedErrorLogger functionality independently."""
        # Create standalone detailed logger
        detailed_logger = DetailedErrorLogger(self.logger)

        # Create error context
        context = ErrorContext(
            operation="standalone_test",
            data_source="standalone_source",
            module="standalone_module",
        )

        # Simulate error
        try:
            message = "Standalone test error"
            _raise_test_error(RuntimeError(message))
        except RuntimeError as e:
            error_record = detailed_logger.log_detailed_error(
                e,
                context,
                ErrorSeverity.HIGH,
            )

            # Verify detailed error record
            require_keys(error_record, ("id",))
            require_keys(error_record, ("datetime",))
            require_keys(error_record, ("traceback",))
            require_keys(error_record, ("frame_info",))

            require_equal(error_record["operation"], "standalone_test")
            require_equal(error_record["data_source"], "standalone_source")
            require_equal(error_record["module"], "standalone_module")
            require_equal(error_record["error_type"], "RuntimeError")
            require_equal(error_record["severity"], ErrorSeverity.HIGH)

    def test_error_severity_handling(self) -> None:
        """Test that different error severities are handled correctly."""
        context = ErrorContext(operation="severity_test", data_source="test_source")

        # Test critical error
        try:
            message = "Critical system error"
            _raise_test_error(SystemError(message))
        except Exception as e:
            error_record = self.error_handler.handle_error(
                e,
                context,
                ErrorSeverity.CRITICAL,
            )
            if not ((error_record["severity"]) == (ErrorSeverity.CRITICAL)):
                raise AssertionError from e

        # Test high error
        try:
            message = "High severity error"
            _raise_test_error(RuntimeError(message))
        except Exception as e:
            error_record = self.error_handler.handle_error(
                e,
                context,
                ErrorSeverity.HIGH,
            )
            if not ((error_record["severity"]) == (ErrorSeverity.HIGH)):
                raise AssertionError from e

        # Test medium error
        try:
            message = "Medium severity error"
            _raise_test_error(ValueError(message))
        except Exception as e:
            error_record = self.error_handler.handle_error(
                e,
                context,
                ErrorSeverity.MEDIUM,
            )
            if not ((error_record["severity"]) == (ErrorSeverity.MEDIUM)):
                raise AssertionError from e

        # Test low error
        try:
            message = "Low severity warning"
            _raise_test_error(Warning(message))
        except Exception as e:
            error_record = self.error_handler.handle_error(
                e,
                context,
                ErrorSeverity.LOW,
            )
            if not ((error_record["severity"]) == (ErrorSeverity.LOW)):
                raise AssertionError from e


if __name__ == "__main__":
    unittest.main()
