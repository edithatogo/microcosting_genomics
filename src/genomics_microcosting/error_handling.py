"""Error handling and graceful degradation for genomics microcosting analysis.

This module provides comprehensive error handling capabilities with graceful
degradation for missing data sources and other error conditions.
"""

import logging
import traceback
import sys
from typing import Any, Dict, List, Callable
from functools import wraps
import time
import json
from pathlib import Path
from datetime import datetime
import uuid
import pickle


class ErrorSeverity:
    """Error severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ErrorContext:
    """Context information for errors."""
    
    def __init__(self, operation: str, data_source: str = None, 
                 parameters: Dict[str, Any] = None, module: str = None):
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
        self.datetime = datetime.fromtimestamp(self.timestamp)


class DetailedErrorLogger:
    """Enhanced error logger with detailed tracing capabilities."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize detailed error logger.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_trace_log: List[Dict[str, Any]] = []
    
    def log_detailed_error(self, error: Exception, context: ErrorContext,
                          severity: str = ErrorSeverity.MEDIUM) -> Dict[str, Any]:
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
        frame = sys._getframe(1) if hasattr(sys, '_getframe') else None
        frame_info = {
            'filename': frame.f_code.co_filename if frame else 'unknown',
            'function': frame.f_code.co_name if frame else 'unknown',
            'line_number': frame.f_lineno if frame else 0
        } if frame else {}
        
        # Get full stack trace
        full_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
        
        # Create detailed error record
        error_record = {
            'id': str(uuid.uuid4()),
            'timestamp': context.timestamp,
            'datetime': context.datetime.isoformat(),
            'operation': context.operation,
            'module': context.module,
            'data_source': context.data_source,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity,
            'parameters': context.parameters,
            'traceback': ''.join(full_traceback) if full_traceback else '',
            'frame_info': frame_info,
            'resolved': False,
            'recovery_attempts': 0
        }
        
        # Add to trace log
        self.error_trace_log.append(error_record)
        
        # Log with structured format
        log_message = self._format_detailed_log(error_record)
        self._log_by_severity(log_message, severity, exc_info=True)
        
        return error_record
    
    def _format_detailed_log(self, error_record: Dict[str, Any]) -> str:
        """Format detailed error log message.
        
        Args:
            error_record: Error record to format
            
        Returns:
            Formatted log message
        """
        return (
            f"DETAILED_ERROR_TRACE | "
            f"ID: {error_record['id']} | "
            f"Time: {error_record['datetime']} | "
            f"Module: {error_record.get('module', 'unknown')} | "
            f"Operation: {error_record['operation']} | "
            f"Source: {error_record.get('data_source', 'unknown')} | "
            f"Error: {error_record['error_type']}: {error_record['error_message']} | "
            f"Severity: {error_record['severity']} | "
            f"Location: {error_record.get('frame_info', {}).get('filename', 'unknown')}:"
            f"{error_record.get('frame_info', {}).get('line_number', 0)} "
            f"in {error_record.get('frame_info', {}).get('function', 'unknown')}"
        )
    
    def _log_by_severity(self, message: str, severity: str, exc_info: bool = False):
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
    
    def get_error_trace_log(self) -> List[Dict[str, Any]]:
        """Get the detailed error trace log.
        
        Returns:
            List of detailed error records
        """
        return self.error_trace_log
    
    def save_error_trace_log(self, file_path: str):
        """Save detailed error trace log to file.
        
        Args:
            file_path: Path to save log
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.error_trace_log, f, indent=2, default=str)
            self.logger.info(f"Detailed error trace log saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save detailed error trace log: {e}")
    
    def clear_error_trace_log(self):
        """Clear the detailed error trace log."""
        self.error_trace_log.clear()
        self.logger.info("Detailed error trace log cleared")


class CheckpointManager:
    """Enhanced checkpoint management with persistence capabilities."""
    
    def __init__(self, logger: logging.Logger = None, checkpoint_dir: str = None):
        """Initialize checkpoint manager.
        
        Args:
            logger: Logger instance (optional)
            checkpoint_dir: Directory to store persistent checkpoints (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.checkpoint_data: Dict[str, Dict[str, Any]] = {}
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        
        # Create checkpoint directory if specified
        if self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Checkpoint directory set to {self.checkpoint_dir}")
    
    def create_checkpoint(self, checkpoint_id: str, data: Any, metadata: Dict[str, Any] = None) -> str:
        """Create a checkpoint for recovery with optional persistence.
        
        Args:
            checkpoint_id: Unique identifier for checkpoint
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
            'id': checkpoint_id,
            'data': data,
            'metadata': metadata or {},
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        # Store in memory
        self.checkpoint_data[checkpoint_id] = checkpoint_record
        
        # Save to disk if checkpoint directory is specified
        if self.checkpoint_dir:
            try:
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.pkl"
                with open(checkpoint_file, 'wb') as f:
                    pickle.dump(checkpoint_record, f)
                self.logger.debug(f"Saved checkpoint {checkpoint_id} to {checkpoint_file}")
            except Exception as e:
                self.logger.error(f"Failed to save checkpoint {checkpoint_id} to disk: {e}")
        
        self.logger.debug(f"Created checkpoint {checkpoint_id}")
        return checkpoint_id
    
    def restore_checkpoint(self, checkpoint_id: str, from_disk: bool = False) -> Any:
        """Restore data from a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            from_disk: Whether to load from disk (if persistent)
            
        Returns:
            Checkpoint data or None if not found
        """
        checkpoint = None
        
        # Try to load from memory first
        if not from_disk and checkpoint_id in self.checkpoint_data:
            checkpoint = self.checkpoint_data[checkpoint_id]
        # Try to load from disk if specified
        elif from_disk and self.checkpoint_dir:
            try:
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.pkl"
                if checkpoint_file.exists():
                    with open(checkpoint_file, 'rb') as f:
                        checkpoint = pickle.load(f)
                    # Also store in memory for future access
                    self.checkpoint_data[checkpoint_id] = checkpoint
                    self.logger.debug(f"Loaded checkpoint {checkpoint_id} from {checkpoint_file}")
            except Exception as e:
                self.logger.error(f"Failed to load checkpoint {checkpoint_id} from disk: {e}")
        
        if checkpoint:
            self.logger.info(f"Restored checkpoint {checkpoint_id}")
            return checkpoint['data']
        else:
            self.logger.warning(f"Checkpoint {checkpoint_id} not found")
            return None
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints with metadata.
        
        Returns:
            List of checkpoint information
        """
        checkpoints = []
        for checkpoint_id, checkpoint in self.checkpoint_data.items():
            checkpoints.append({
                'id': checkpoint_id,
                'timestamp': checkpoint['timestamp'],
                'datetime': checkpoint['datetime'],
                'metadata': checkpoint['metadata']
            })
        return checkpoints
    
    def delete_checkpoint(self, checkpoint_id: str):
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier to delete
        """
        # Remove from memory
        if checkpoint_id in self.checkpoint_data:
            del self.checkpoint_data[checkpoint_id]
        
        # Remove from disk if it exists
        if self.checkpoint_dir:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.pkl"
            if checkpoint_file.exists():
                try:
                    checkpoint_file.unlink()
                    self.logger.debug(f"Deleted checkpoint file {checkpoint_file}")
                except Exception as e:
                    self.logger.error(f"Failed to delete checkpoint file {checkpoint_file}: {e}")
        
        self.logger.info(f"Deleted checkpoint {checkpoint_id}")


class ErrorHandler:
    """Comprehensive error handler with graceful degradation."""
    
    def __init__(self, logger: logging.Logger = None, checkpoint_dir: str = None):
        """Initialize the error handler.
        
        Args:
            logger: Logger instance (optional)
            checkpoint_dir: Directory to store persistent checkpoints (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.detailed_logger = DetailedErrorLogger(logger)
        self.error_log: List[Dict[str, Any]] = []
        self.degradation_strategies: Dict[str, Callable] = {}
        self.checkpoint_manager = CheckpointManager(logger, checkpoint_dir)
        
    def register_degradation_strategy(self, error_type: str, 
                                    strategy: Callable):
        """Register a degradation strategy for a specific error type.
        
        Args:
            error_type: Type of error
            strategy: Function to handle the error
        """
        self.degradation_strategies[error_type] = strategy
        self.logger.debug(f"Registered degradation strategy for {error_type}")
    
    def handle_error(self, error: Exception, context: ErrorContext,
                    severity: str = ErrorSeverity.MEDIUM) -> Dict[str, Any]:
        """Handle an error with appropriate logging and degradation.
        
        Args:
            error: Exception that occurred
            context: Error context information
            severity: Error severity level
            
        Returns:
            Dict with error handling results
        """
        # Log detailed error information
        detailed_error = self.detailed_logger.log_detailed_error(error, context, severity)
        
        # Log the error in the simple format as well
        error_info = {
            'id': detailed_error['id'],
            'timestamp': context.timestamp,
            'operation': context.operation,
            'data_source': context.data_source,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity,
            'parameters': context.parameters,
            'stack_trace': traceback.format_exc(),
            'resolved': False
        }
        
        self.error_log.append(error_info)
        
        # Log based on severity (simple format)
        log_message = (
            f"Error in {context.operation}: {type(error).__name__}: {error} "
            f"(Data source: {context.data_source})"
        )
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, exc_info=True)
        else:
            self.logger.info(log_message)
        
        # Apply degradation strategy if available
        degradation_result = None
        strategy_key = f"{context.operation}_{type(error).__name__}"
        
        if strategy_key in self.degradation_strategies:
            try:
                degradation_result = self.degradation_strategies[strategy_key](error, context)
                self.logger.info(f"Applied degradation strategy for {strategy_key}")
            except Exception as strategy_error:
                self.logger.error(
                    f"Error in degradation strategy {strategy_key}: {strategy_error}"
                )
        elif type(error).__name__ in self.degradation_strategies:
            try:
                degradation_result = self.degradation_strategies[type(error).__name__](error, context)
                self.logger.info(f"Applied general degradation strategy for {type(error).__name__}")
            except Exception as strategy_error:
                self.logger.error(
                    f"Error in general degradation strategy {type(error).__name__}: {strategy_error}"
                )
        
        error_info['degradation_result'] = degradation_result
        detailed_error['degradation_result'] = degradation_result
        return error_info
    
    def graceful_degradation(self, operation: str, 
                           fallback_function: Callable = None,
                           default_value: Any = None,
                           data_source: str = None,
                           module: str = None,
                           severity_threshold: str = ErrorSeverity.MEDIUM):
        """Decorator for graceful degradation of operations.
        
        Args:
            operation: Name of the operation
            fallback_function: Function to call on error
            default_value: Default value to return on error
            data_source: Data source involved
            module: Module where operation occurs
            severity_threshold: Minimum severity to handle
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                context = ErrorContext(
                    operation=operation,
                    data_source=data_source,
                    module=module,
                    parameters={'args': args, 'kwargs': kwargs}
                )
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_info = self.handle_error(e, context)
                    
                    # Check if we should apply degradation
                    if self._should_degrade(error_info['severity'], severity_threshold):
                        if fallback_function:
                            try:
                                return fallback_function(*args, **kwargs)
                            except Exception as fallback_error:
                                self.logger.error(
                                    f"Fallback function failed: {fallback_error}"
                                )
                        
                        # Return default value
                        self.logger.info(
                            f"Returning default value for {operation} due to error"
                        )
                        return default_value
                    else:
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
            ErrorSeverity.CRITICAL: 4
        }
        
        return severity_levels.get(error_severity, 0) >= severity_levels.get(threshold, 0)
    
    def create_checkpoint(self, checkpoint_id: str, data: Any, metadata: Dict[str, Any] = None):
        """Create a checkpoint for recovery.
        
        Args:
            checkpoint_id: Unique identifier for checkpoint
            data: Data to save
            metadata: Additional metadata about the checkpoint
        """
        return self.checkpoint_manager.create_checkpoint(checkpoint_id, data, metadata)
    
    def restore_checkpoint(self, checkpoint_id: str, from_disk: bool = False) -> Any:
        """Restore data from a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            from_disk: Whether to load from disk (if persistent)
            
        Returns:
            Checkpoint data or None if not found
        """
        return self.checkpoint_manager.restore_checkpoint(checkpoint_id, from_disk)
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints with metadata.
        
        Returns:
            List of checkpoint information
        """
        return self.checkpoint_manager.list_checkpoints()
    
    def delete_checkpoint(self, checkpoint_id: str):
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier to delete
        """
        self.checkpoint_manager.delete_checkpoint(checkpoint_id)
    
    def get_error_log(self) -> List[Dict[str, Any]]:
        """Get the error log.
        
        Returns:
            List of error information
        """
        return self.error_log
    
    def get_detailed_error_log(self) -> List[Dict[str, Any]]:
        """Get the detailed error trace log.
        
        Returns:
            List of detailed error records
        """
        return self.detailed_logger.get_error_trace_log()
    
    def save_error_log(self, file_path: str):
        """Save error log to file.
        
        Args:
            file_path: Path to save log
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.error_log, f, indent=2, default=str)
            self.logger.info(f"Error log saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save error log: {e}")
    
    def save_detailed_error_log(self, file_path: str):
        """Save detailed error trace log to file.
        
        Args:
            file_path: Path to save log
        """
        self.detailed_logger.save_error_trace_log(file_path)
    
    def clear_error_log(self):
        """Clear the error log."""
        self.error_log.clear()
        self.logger.info("Error log cleared")
    
    def clear_detailed_error_log(self):
        """Clear the detailed error trace log."""
        self.detailed_logger.clear_error_trace_log()


class DataDegradationStrategies:
    """Standard degradation strategies for common data issues."""
    
    @staticmethod
    def missing_sheet_strategy(error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle missing sheet data.
        
        Args:
            error: Exception that occurred
            context: Error context
            
        Returns:
            Degradation result
        """
        return {
            'action': 'use_default_values',
            'default_data': {},
            'message': f'Using default values for missing sheet: {context.data_source}'
        }
    
    @staticmethod
    def missing_cell_strategy(error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle missing cell data.
        
        Args:
            error: Exception that occurred
            context: Error context
            
        Returns:
            Degradation result
        """
        return {
            'action': 'use_zero_value',
            'default_value': 0,
            'message': f'Using zero for missing cell in {context.data_source}'
        }
    
    @staticmethod
    def formula_error_strategy(error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Handle formula execution errors.
        
        Args:
            error: Exception that occurred
            context: Error context
            
        Returns:
            Degradation result
        """
        return {
            'action': 'skip_calculation',
            'default_value': None,
            'message': f'Skipping formula calculation due to error: {error}'
        }


def setup_standard_error_handling(logger: logging.Logger = None, checkpoint_dir: str = None) -> ErrorHandler:
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
        'FileNotFoundError', 
        DataDegradationStrategies.missing_sheet_strategy
    )
    
    handler.register_degradation_strategy(
        'KeyError', 
        DataDegradationStrategies.missing_cell_strategy
    )
    
    handler.register_degradation_strategy(
        'ValueError', 
        DataDegradationStrategies.formula_error_strategy
    )
    
    handler.register_degradation_strategy(
        'ZeroDivisionError', 
        DataDegradationStrategies.formula_error_strategy
    )
    
    return handler


# Example usage:
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create error handler with checkpoint directory
    error_handler = setup_standard_error_handling(logger, checkpoint_dir="./checkpoints")
    
    # Example 1: Using decorator for graceful degradation
    @error_handler.graceful_degradation(
        operation="data_loading",
        default_value=[],
        data_source="sample_data.csv",
        module="data_loader"
    )
    def load_data(file_path: str):
        """Simulate data loading that might fail."""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File {file_path} not found")
        # Simulate successful loading
        return ["data1", "data2", "data3"]
    
    # This will fail gracefully and return default value
    result = load_data("nonexistent_file.csv")
    print(f"Load result: {result}")
    
    # Example 2: Manual error handling
    try:
        # Simulate an operation that might fail
        raise ValueError("Invalid data format")
    except Exception as e:
        context = ErrorContext(
            operation="data_processing",
            data_source="input_data",
            module="data_processor",
            parameters={'format': 'csv'}
        )
        error_info = error_handler.handle_error(e, context, ErrorSeverity.MEDIUM)
        print(f"Error handled: {error_info['error_message']}")
    
    # Example 3: Checkpoint usage
    # Create a checkpoint
    test_data = {"analysis_results": [1, 2, 3, 4, 5], "metadata": {"version": "1.0"}}
    checkpoint_id = error_handler.create_checkpoint(
        "analysis_step_1", 
        test_data,
        {"step": "initial_analysis", "status": "completed"}
    )
    print(f"Created checkpoint: {checkpoint_id}")
    
    # List checkpoints
    checkpoints = error_handler.list_checkpoints()
    print(f"Available checkpoints: {len(checkpoints)}")
    
    # Restore checkpoint
    restored_data = error_handler.restore_checkpoint(checkpoint_id)
    print(f"Restored data: {restored_data}")
    
    # Show error logs
    print(f"\nError log contains {len(error_handler.get_error_log())} entries")
    print(f"Detailed error log contains {len(error_handler.get_detailed_error_log())} entries")