# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Error handling and graceful degradation for genomics microcosting analysis.

This module provides comprehensive error handling capabilities with graceful
degradation for missing data sources and other error conditions.
"""

import inspect
import json
import logging
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypedDict, Unpack
lazy from collections.abc import Callable, Mapping

from .execution_contracts import legacy_bool_option
lazy from .execution_contracts import DegradationDecorator

logger = logging.getLogger(__name__)


class ErrorSeverity:
    """Error severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DegradationContext(TypedDict, total=False):
    """Optional source context and recovery threshold for an operation."""

    data_source: str | None
    module: str | None
    severity_threshold: str


_DEGRADATION_FIELDS = ("data_source", "module", "severity_threshold")


def _degradation_context(
    positional: tuple[str | None, ...],
    fields: DegradationContext,
) -> tuple[str | None, str | None, str]:
    if len(positional) > len(_DEGRADATION_FIELDS):
        message = "Too many positional options for graceful_degradation"
        raise TypeError(message)
    if (fields.keys() - set(_DEGRADATION_FIELDS)) or any(
        key in fields for key in _DEGRADATION_FIELDS[: len(positional)]
    ):
        message = "Invalid context arguments for graceful_degradation"
        raise TypeError(message)
    data_source = positional[0] if positional else fields.get("data_source")
    module = (
        positional[1]
        if len(positional) >= len(_DEGRADATION_FIELDS) - 1
        else fields.get("module")
    )
    threshold = (
        positional[-1]
        if len(positional) == len(_DEGRADATION_FIELDS)
        else fields.get("severity_threshold", ErrorSeverity.MEDIUM)
    )
    if not isinstance(threshold, str):
        message = "The severity threshold must be a string"
        raise TypeError(message)
    return data_source, module, threshold


class ErrorContext:
    """Context information for errors."""

    def __init__(
        self,
        operation: str,
        data_source: str | None = None,
        parameters: Mapping[str, object] | None = None,
        module: str | None = None,
    ) -> None:
        """Initialize error context.

        Args:
            operation: Operation that failed
            data_source: Data source involved
            parameters: Operation parameters
            module: Module where error occurred

        """
        self.operation = operation
        self.data_source = data_source
        self.parameters = parameters or {}
        self.module = module
        self.timestamp = time.time()
        self.datetime = datetime.fromtimestamp(self.timestamp, UTC)


class DetailedErrorLogger:
    """Enhanced error logger with detailed tracing capabilities."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize detailed error logger.

        Args:
            logger: Logger instance (optional)

        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_trace_log: list[dict[str, Any]] = []

    def log_detailed_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: str = ErrorSeverity.MEDIUM,
    ) -> dict[str, Any]:
        """Log detailed error information with full tracing.

        Args:
            error: Exception that occurred
            context: Error context information
            severity: Error severity level

        Returns:
            Dict with detailed error information

        """
        # Capture detailed traceback information
        exc_type, exc_value, exc_traceback = sys.exc_info()

        # Get frame information
        current_frame = inspect.currentframe()
        frame = current_frame.f_back if current_frame is not None else None
        frame_info = (
            {
                "filename": frame.f_code.co_filename if frame else "unknown",
                "function": frame.f_code.co_name if frame else "unknown",
                "line_number": frame.f_lineno if frame else 0,
            }
            if frame
            else {}
        )
        del current_frame, frame

        # Get full stack trace
        full_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)

        # Create detailed error record
        error_record = {
            "id": str(uuid.uuid4()),
            "timestamp": context.timestamp,
            "datetime": context.datetime.isoformat(),
            "operation": context.operation,
            "module": context.module,
            "data_source": context.data_source,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity,
            "parameters": context.parameters,
            "traceback": "".join(full_traceback) if full_traceback else "",
            "frame_info": frame_info,
            "resolved": False,
            "recovery_attempts": 0,
        }

        # Add to trace log
        self.error_trace_log.append(error_record)

        # Log with structured format
        log_message = self._format_detailed_log(error_record)
        self._log_by_severity(log_message, severity, exc_info=True)

        return error_record

    def _format_detailed_log(self, error_record: dict[str, Any]) -> str:
        """Format detailed error log message.

        Args:
            error_record: Error record to format

        Returns:
            Formatted log message

        """
        frame_info = error_record.get("frame_info", {})
        return (
            f"DETAILED_ERROR_TRACE | "
            f"ID: {error_record['id']} | "
            f"Time: {error_record['datetime']} | "
            f"Module: {error_record.get('module', 'unknown')} | "
            f"Operation: {error_record['operation']} | "
            f"Source: {error_record.get('data_source', 'unknown')} | "
            f"Error: {error_record['error_type']}: {error_record['error_message']} | "
            f"Severity: {error_record['severity']} | "
            f"Location: {frame_info.get('filename', 'unknown')}:"
            f"{frame_info.get('line_number', 0)} "
            f"in {frame_info.get('function', 'unknown')}"
        )

    def _log_by_severity(
        self,
        message: str,
        severity: str,
        *,
        exc_info: bool = False,
    ) -> None:
        """Log message based on severity level.

        Args:
            message: Message to log
            severity: Severity level
            exc_info: Whether to include exception info

        """
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(message, exc_info=exc_info)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(message, exc_info=exc_info)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(message, exc_info=exc_info)
        else:
            self.logger.info(message, exc_info=exc_info)

    def get_error_trace_log(self) -> list[dict[str, Any]]:
        """Get the detailed error trace log.

        Returns:
            List of detailed error records

        """
        return self.error_trace_log

    def save_error_trace_log(self, file_path: str) -> None:
        """Save detailed error trace log to file.

        Args:
            file_path: Path to save log

        """
        try:
            with Path(file_path).open("w") as f:
                json.dump(self.error_trace_log, f, indent=2, default=str)
            self.logger.info("Detailed error trace log saved to %s", file_path)
        except Exception:
            self.logger.exception("Failed to save detailed error trace log")

    def clear_error_trace_log(self) -> None:
        """Clear the detailed error trace log."""
        self.error_trace_log.clear()
        self.logger.info("Detailed error trace log cleared")


class CheckpointManager:
    """Enhanced checkpoint management with persistence capabilities."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        checkpoint_dir: str | None = None,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            logger: Logger instance (optional)
            checkpoint_dir: Directory to store persistent checkpoints (optional)

        """
        self.logger = logger or logging.getLogger(__name__)
        self.checkpoint_data: dict[str, dict[str, Any]] = {}
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None

        # Create checkpoint directory if specified
        if self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info("Checkpoint directory set to %s", self.checkpoint_dir)

    def create_checkpoint(
        self,
        checkpoint_id: str | None,
        data: object,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a checkpoint for recovery with optional persistence.

        Args:
            checkpoint_id: Unique identifier, or None to generate one
            data: Data to save
            metadata: Additional metadata about the checkpoint

        Returns:
            Checkpoint identifier

        """
        # Generate full checkpoint ID if not provided
        if not checkpoint_id:
            checkpoint_id = f"checkpoint_{uuid.uuid4()}"

        # Create checkpoint record
        checkpoint_record = {
            "id": checkpoint_id,
            "data": data,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "datetime": datetime.now(UTC).isoformat(),
        }

        # Store in memory
        self.checkpoint_data[checkpoint_id] = checkpoint_record

        # Save to disk if checkpoint directory is specified
        if self.checkpoint_dir:
            try:
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
                with Path(checkpoint_file).open("w") as f:
                    json.dump(checkpoint_record, f)
                self.logger.debug(
                    "Saved checkpoint %s to %s",
                    checkpoint_id,
                    checkpoint_file,
                )
            except Exception:
                self.logger.exception(
                    "Failed to save checkpoint %s to disk",
                    checkpoint_id,
                )

        self.logger.debug("Created checkpoint %s", checkpoint_id)
        return checkpoint_id

    def restore_checkpoint(
        self,
        checkpoint_id: str,
        *positional_from_disk: bool,
        from_disk: bool | None = None,
    ) -> object:
        """Restore data from a checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier
            *positional_from_disk: Optional positional flag for existing callers.
            from_disk: Whether to load from disk (if persistent)

        Returns:
            Checkpoint data or None if not found

        """
        from_disk = legacy_bool_option(
            "from_disk",
            positional_from_disk,
            keyword=from_disk,
            default=False,
        )
        checkpoint = None

        # Try to load from memory first
        if not from_disk and checkpoint_id in self.checkpoint_data:
            checkpoint = self.checkpoint_data[checkpoint_id]
        # Try to load from disk if specified
        elif from_disk and self.checkpoint_dir:
            try:
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    with Path(checkpoint_file).open() as f:
                        checkpoint = json.load(f)
                    # Also store in memory for future access
                    self.checkpoint_data[checkpoint_id] = checkpoint
                    self.logger.debug(
                        "Loaded checkpoint %s from %s",
                        checkpoint_id,
                        checkpoint_file,
                    )
            except Exception:
                self.logger.exception(
                    "Failed to load checkpoint %s from disk",
                    checkpoint_id,
                )

        if checkpoint:
            self.logger.info("Restored checkpoint %s", checkpoint_id)
            return checkpoint["data"]
        self.logger.warning("Checkpoint %s not found", checkpoint_id)
        return None

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all available checkpoints with metadata.

        Returns:
            List of checkpoint information

        """
        checkpoints: list[dict[str, Any]] = []
        for checkpoint_id, checkpoint in self.checkpoint_data.items():
            checkpoints.append(
                {
                    "id": checkpoint_id,
                    "timestamp": checkpoint["timestamp"],
                    "datetime": checkpoint["datetime"],
                    "metadata": checkpoint["metadata"],
                },
            )
        return checkpoints

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier to delete

        """
        # Remove from memory
        if checkpoint_id in self.checkpoint_data:
            del self.checkpoint_data[checkpoint_id]

        # Remove from disk if it exists
        if self.checkpoint_dir:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                try:
                    checkpoint_file.unlink()
                    self.logger.debug("Deleted checkpoint file %s", checkpoint_file)
                except Exception:
                    self.logger.exception(
                        "Failed to delete checkpoint file %s",
                        checkpoint_file,
                    )

        self.logger.info("Deleted checkpoint %s", checkpoint_id)


type DegradationStrategy = Callable[[Exception, ErrorContext], object]


class ErrorHandler:
    """Comprehensive error handler with graceful degradation."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        checkpoint_dir: str | None = None,
    ) -> None:
        """Initialize the error handler.

        Args:
            logger: Logger instance (optional)
            checkpoint_dir: Directory to store persistent checkpoints (optional)

        """
        self.logger = logger or logging.getLogger(__name__)
        self.detailed_logger = DetailedErrorLogger(logger)
        self.error_log: list[dict[str, Any]] = []
        self.degradation_strategies: dict[str, DegradationStrategy] = {}
        self.checkpoint_manager = CheckpointManager(logger, checkpoint_dir)

    def register_degradation_strategy(
        self,
        error_type: str,
        strategy: DegradationStrategy,
    ) -> None:
        """Register a degradation strategy for a specific error type.

        Args:
            error_type: Type of error
            strategy: Function to handle the error

        """
        self.degradation_strategies[error_type] = strategy
        self.logger.debug("Registered degradation strategy for %s", error_type)

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: str = ErrorSeverity.MEDIUM,
    ) -> dict[str, Any]:
        """Handle an error with appropriate logging and degradation.

        Args:
            error: Exception that occurred
            context: Error context information
            severity: Error severity level

        Returns:
            Dict with error handling results

        """
        # Log detailed error information
        detailed_error = self.detailed_logger.log_detailed_error(
            error,
            context,
            severity,
        )

        # Log the error in the simple format as well
        error_info = {
            "id": detailed_error["id"],
            "timestamp": context.timestamp,
            "operation": context.operation,
            "data_source": context.data_source,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity,
            "parameters": context.parameters,
            "stack_trace": "".join(traceback.format_exception(error)),
            "resolved": False,
        }

        self.error_log.append(error_info)

        # Log based on severity (simple format)
        log_message = (
            f"Error in {context.operation}: {type(error).__name__}: {error} "
            f"(Data source: {context.data_source})"
        )

        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=error)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=error)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, exc_info=error)
        else:
            self.logger.info(log_message)

        # Apply degradation strategy if available
        degradation_result = None
        strategy_key = f"{context.operation}_{type(error).__name__}"

        if strategy_key in self.degradation_strategies:
            try:
                degradation_result = self.degradation_strategies[strategy_key](
                    error,
                    context,
                )
                self.logger.info("Applied degradation strategy for %s", strategy_key)
            except Exception:
                self.logger.exception(
                    "Error in degradation strategy %s",
                    strategy_key,
                )
        elif type(error).__name__ in self.degradation_strategies:
            try:
                degradation_result = self.degradation_strategies[type(error).__name__](
                    error,
                    context,
                )
                self.logger.info(
                    "Applied general degradation strategy for %s",
                    type(error).__name__,
                )
            except Exception:
                self.logger.exception(
                    "Error in general degradation strategy %s",
                    type(error).__name__,
                )

        error_info["degradation_result"] = degradation_result
        detailed_error["degradation_result"] = degradation_result
        return error_info

    def graceful_degradation[D = None](
        self,
        operation: str,
        fallback_function: Callable[..., D] | None = None,
        default_value: D | None = None,
        *positional_context: str | None,
        **context_fields: Unpack[DegradationContext],
    ) -> DegradationDecorator[D]:
        """Wrap an operation with graceful degradation.

        Args:
            operation: Name of the operation
            fallback_function: Function to call on error
            default_value: Default value to return on error
            *positional_context: Optional positional context for existing callers.
            **context_fields: Data source, module and minimum recovery severity.

        Returns:
            Decorated function

        """
        data_source, module, severity_threshold = _degradation_context(
            positional_context,
            context_fields,
        )

        def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R | D | None]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | D | None:
                context = ErrorContext(
                    operation=operation,
                    data_source=data_source,
                    module=module,
                    parameters={"args": args, "kwargs": kwargs},
                )

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_info = self.handle_error(e, context)

                    # Check if we should apply degradation
                    if self._should_degrade(error_info["severity"], severity_threshold):
                        if fallback_function:
                            try:
                                return fallback_function(*args, **kwargs)
                            except Exception:
                                self.logger.exception(
                                    "Fallback function failed",
                                )

                        # Return default value
                        self.logger.info(
                            "Returning default value for %s due to error",
                            operation,
                        )
                        return default_value
                    # Re-raise critical errors
                    raise

            return wrapper

        return decorator

    def _should_degrade(self, error_severity: str, threshold: str) -> bool:
        """Determine if error should trigger degradation.

        Args:
            error_severity: Severity of the error
            threshold: Severity threshold

        Returns:
            True if error should trigger degradation

        """
        severity_levels = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4,
        }

        return severity_levels.get(error_severity, 0) >= severity_levels.get(
            threshold,
            0,
        )

    def create_checkpoint(
        self,
        checkpoint_id: str | None,
        data: object,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a checkpoint for recovery.

        Args:
            checkpoint_id: Unique identifier, or None to generate one
            data: Data to save
            metadata: Additional metadata about the checkpoint

        """
        return self.checkpoint_manager.create_checkpoint(checkpoint_id, data, metadata)

    def restore_checkpoint(
        self,
        checkpoint_id: str,
        *positional_from_disk: bool,
        from_disk: bool | None = None,
    ) -> object:
        """Restore data from a checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier
            *positional_from_disk: Optional positional flag for existing callers.
            from_disk: Whether to load from disk (if persistent)

        Returns:
            Checkpoint data or None if not found

        """
        return self.checkpoint_manager.restore_checkpoint(
            checkpoint_id,
            *positional_from_disk,
            from_disk=from_disk,
        )

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all available checkpoints with metadata.

        Returns:
            List of checkpoint information

        """
        return self.checkpoint_manager.list_checkpoints()

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier to delete

        """
        self.checkpoint_manager.delete_checkpoint(checkpoint_id)

    def get_error_log(self) -> list[dict[str, Any]]:
        """Get the error log.

        Returns:
            List of error information

        """
        return self.error_log

    def get_detailed_error_log(self) -> list[dict[str, Any]]:
        """Get the detailed error trace log.

        Returns:
            List of detailed error records

        """
        return self.detailed_logger.get_error_trace_log()

    def save_error_log(self, file_path: str) -> None:
        """Save error log to file.

        Args:
            file_path: Path to save log

        """
        try:
            with Path(file_path).open("w") as f:
                json.dump(self.error_log, f, indent=2, default=str)
            self.logger.info("Error log saved to %s", file_path)
        except Exception:
            self.logger.exception("Failed to save error log")

    def save_detailed_error_log(self, file_path: str) -> None:
        """Save detailed error trace log to file.

        Args:
            file_path: Path to save log

        """
        self.detailed_logger.save_error_trace_log(file_path)

    def clear_error_log(self) -> None:
        """Clear the error log."""
        self.error_log.clear()
        self.logger.info("Error log cleared")

    def clear_detailed_error_log(self) -> None:
        """Clear the detailed error trace log."""
        self.detailed_logger.clear_error_trace_log()


class DataDegradationStrategies:
    """Standard degradation strategies for common data issues."""

    @staticmethod
    def _log_degradation(error: Exception, context: ErrorContext) -> None:
        logging.getLogger(__name__).debug(
            "Applying fallback for %s during %s",
            type(error).__name__,
            context.operation,
        )

    @staticmethod
    def missing_sheet_strategy(
        error: Exception,
        context: ErrorContext,
    ) -> dict[str, Any]:
        """Handle missing sheet data.

        Args:
            error: Exception that occurred
            context: Error context

        Returns:
            Degradation result

        """
        DataDegradationStrategies._log_degradation(error, context)
        return {
            "action": "use_default_values",
            "default_data": {},
            "message": f"Using default values for missing sheet: {context.data_source}",
        }

    @staticmethod
    def missing_cell_strategy(
        error: Exception,
        context: ErrorContext,
    ) -> dict[str, Any]:
        """Handle missing cell data.

        Args:
            error: Exception that occurred
            context: Error context

        Returns:
            Degradation result

        """
        DataDegradationStrategies._log_degradation(error, context)
        return {
            "action": "use_zero_value",
            "default_value": 0,
            "message": f"Using zero for missing cell in {context.data_source}",
        }

    @staticmethod
    def formula_error_strategy(
        error: Exception,
        context: ErrorContext,
    ) -> dict[str, Any]:
        """Handle formula execution errors.

        Args:
            error: Exception that occurred
            context: Error context

        Returns:
            Degradation result

        """
        DataDegradationStrategies._log_degradation(error, context)
        return {
            "action": "skip_calculation",
            "default_value": None,
            "message": f"Skipping formula calculation due to error: {error}",
        }


def setup_standard_error_handling(
    logger: logging.Logger | None = None,
    checkpoint_dir: str | None = None,
) -> ErrorHandler:
    """Set up standard error handling with common degradation strategies.

    Args:
        logger: Logger instance (optional)
        checkpoint_dir: Directory to store persistent checkpoints (optional)

    Returns:
        Configured ErrorHandler instance

    """
    handler = ErrorHandler(logger, checkpoint_dir)

    # Register standard degradation strategies
    handler.register_degradation_strategy(
        "FileNotFoundError",
        DataDegradationStrategies.missing_sheet_strategy,
    )

    handler.register_degradation_strategy(
        "KeyError",
        DataDegradationStrategies.missing_cell_strategy,
    )

    handler.register_degradation_strategy(
        "ValueError",
        DataDegradationStrategies.formula_error_strategy,
    )

    handler.register_degradation_strategy(
        "ZeroDivisionError",
        DataDegradationStrategies.formula_error_strategy,
    )

    return handler


# Example usage:
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create error handler with checkpoint directory
    error_handler = setup_standard_error_handling(
        logger,
        checkpoint_dir="./checkpoints",
    )

    # Example 1: Using decorator for graceful degradation
    @error_handler.graceful_degradation(
        operation="data_loading",
        default_value=[],
        data_source="sample_data.csv",
        module="data_loader",
    )
    def load_data(file_path: str) -> list[str]:
        """Simulate data loading that might fail."""
        if not Path(file_path).exists():
            message = f"File {file_path} not found"
            raise FileNotFoundError(message)
        # Simulate successful loading
        return ["data1", "data2", "data3"]

    # This will fail gracefully and return default value
    result = load_data("nonexistent_file.csv")
    logger.info("%s", f"Load result: {result}")

    context = ErrorContext(
        operation="data_processing",
        data_source="input_data",
        module="data_processor",
        parameters={"format": "csv"},
    )
    error_info = error_handler.handle_error(
        ValueError("Invalid data format"),
        context,
        ErrorSeverity.MEDIUM,
    )
    logger.info("Error handled: %s", error_info["error_message"])

    # Example 3: Checkpoint usage
    # Create a checkpoint
    test_data = {"analysis_results": [1, 2, 3, 4, 5], "metadata": {"version": "1.0"}}
    checkpoint_id = error_handler.create_checkpoint(
        "analysis_step_1",
        test_data,
        {"step": "initial_analysis", "status": "completed"},
    )
    logger.info("%s", f"Created checkpoint: {checkpoint_id}")

    # List checkpoints
    checkpoints = error_handler.list_checkpoints()
    logger.info("%s", f"Available checkpoints: {len(checkpoints)}")

    # Restore checkpoint
    restored_data = error_handler.restore_checkpoint(checkpoint_id)
    logger.info("%s", f"Restored data: {restored_data}")

    # Show error logs
    logger.info(
        "%s",
        f"\nError log contains {len(error_handler.get_error_log())} entries",
    )
    logger.info(
        "%s",
        (
            f"Detailed error log contains "
            f"{len(error_handler.get_detailed_error_log())} entries"
        ),
    )
