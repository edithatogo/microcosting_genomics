"""Input validation for genomics microcosting analysis.

This module provides comprehensive input validation capabilities for all aspects
of the microcosting analysis system, including data validation, configuration
validation, and parameter validation.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import pandas as pd
import numpy as np

from .logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom exception for input validation errors."""
    pass


class InputValidator:
    """Comprehensive input validation for microcosting analysis."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the input validator.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_sheet_name(self, sheet_name: str) -> bool:
        """Validate sheet name format and content.
        
        Args:
            sheet_name: Sheet name to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If sheet name is invalid
        """
        if not isinstance(sheet_name, str):
            raise ValidationError(f"Sheet name must be a string, got {type(sheet_name)}")
        
        if not sheet_name:
            raise ValidationError("Sheet name cannot be empty")
        
        if len(sheet_name) > 255:
            raise ValidationError("Sheet name cannot exceed 255 characters")
        
        # Check for invalid characters (Excel restrictions)
        invalid_chars = ['\\', '/', '*', '[', ']', ':', '?']
        for char in invalid_chars:
            if char in sheet_name:
                raise ValidationError(f"Sheet name contains invalid character: {char}")
        
        self.logger.debug(f"Sheet name '{sheet_name}' validated successfully")
        return True
    
    def validate_cell_reference(self, cell_ref: str) -> bool:
        """Validate Excel cell reference format.
        
        Args:
            cell_ref: Cell reference to validate (e.g., "A1", "BZ999")
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If cell reference is invalid
        """
        if not isinstance(cell_ref, str):
            raise ValidationError(f"Cell reference must be a string, got {type(cell_ref)}")
        
        if not cell_ref:
            raise ValidationError("Cell reference cannot be empty")
        
        # Regex pattern for Excel cell references (e.g., A1, BZ999)
        pattern = r'^[A-Z]{1,3}[1-9][0-9]{0,6}$'
        if not re.match(pattern, cell_ref):
            raise ValidationError(f"Invalid cell reference format: {cell_ref}")
        
        # Extract column and row
        col_part = ''.join([c for c in cell_ref if c.isalpha()])
        row_part = ''.join([c for c in cell_ref if c.isdigit()])
        
        # Validate column range (A to XFD = 1 to 16384)
        col_number = self._column_to_number(col_part)
        if col_number < 1 or col_number > 16384:
            raise ValidationError(f"Column out of range: {col_part}")
        
        # Validate row range (1 to 1048576)
        row_number = int(row_part)
        if row_number < 1 or row_number > 1048576:
            raise ValidationError(f"Row out of range: {row_number}")
        
        self.logger.debug(f"Cell reference '{cell_ref}' validated successfully")
        return True
    
    def _column_to_number(self, column: str) -> int:
        """Convert Excel column letter to number.
        
        Args:
            column: Column letter(s) (e.g., "A", "BZ")
            
        Returns:
            Column number (1-based)
        """
        result = 0
        for char in column:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result
    
    def validate_dataframe(self, df: pd.DataFrame, expected_columns: List[str] = None,
                          min_rows: int = 0, max_rows: int = None) -> bool:
        """Validate pandas DataFrame structure and content.
        
        Args:
            df: DataFrame to validate
            expected_columns: List of expected column names (optional)
            min_rows: Minimum number of rows required (optional)
            max_rows: Maximum number of rows allowed (optional)
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If DataFrame is invalid
        """
        if not isinstance(df, pd.DataFrame):
            raise ValidationError(f"Expected pandas DataFrame, got {type(df)}")
        
        # Check row count
        row_count = len(df)
        if row_count < min_rows:
            raise ValidationError(f"DataFrame has {row_count} rows, minimum required is {min_rows}")
        
        if max_rows is not None and row_count > max_rows:
            raise ValidationError(f"DataFrame has {row_count} rows, maximum allowed is {max_rows}")
        
        # Check columns
        if expected_columns:
            missing_columns = set(expected_columns) - set(df.columns)
            if missing_columns:
                raise ValidationError(f"Missing expected columns: {missing_columns}")
        
        # Check for excessive null values
        null_percentage = df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100
        if null_percentage > 90:
            raise ValidationError(f"DataFrame has {null_percentage:.2f}% null values, which is excessive")
        
        self.logger.debug(f"DataFrame validated successfully: {df.shape[0]} rows, {df.shape[1]} columns")
        return True
    
    def validate_numeric_value(self, value: Any, min_value: float = None, 
                             max_value: float = None, allow_none: bool = False) -> bool:
        """Validate numeric value with range checking.
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value (optional)
            max_value: Maximum allowed value (optional)
            allow_none: Whether None values are allowed
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            if allow_none:
                return True
            else:
                raise ValidationError("Value cannot be None")
        
        # Check if value is numeric
        if not isinstance(value, (int, float, np.integer, np.floating)):
            # Try to convert to float
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Value must be numeric, got {type(value)}: {value}")
        
        # Check range
        if min_value is not None and value < min_value:
            raise ValidationError(f"Value {value} is less than minimum {min_value}")
        
        if max_value is not None and value > max_value:
            raise ValidationError(f"Value {value} is greater than maximum {max_value}")
        
        # Check for special float values
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            raise ValidationError(f"Value cannot be NaN or infinite: {value}")
        
        self.logger.debug(f"Numeric value {value} validated successfully")
        return True
    
    def validate_string_value(self, value: Any, max_length: int = None, 
                            pattern: str = None, allow_empty: bool = False) -> bool:
        """Validate string value with length and pattern checking.
        
        Args:
            value: Value to validate
            max_length: Maximum allowed length (optional)
            pattern: Regex pattern to match (optional)
            allow_empty: Whether empty strings are allowed
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            raise ValidationError("Value cannot be None")
        
        # Convert to string if needed
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception:
                raise ValidationError(f"Value cannot be converted to string: {value}")
        
        # Check empty string
        if not value and not allow_empty:
            raise ValidationError("String value cannot be empty")
        
        # Check length
        if max_length is not None and len(value) > max_length:
            raise ValidationError(f"String length {len(value)} exceeds maximum {max_length}")
        
        # Check pattern
        if pattern is not None:
            if not re.match(pattern, value):
                raise ValidationError(f"String '{value}' does not match pattern: {pattern}")
        
        self.logger.debug(f"String value '{value}' validated successfully")
        return True
    
    def validate_file_path(self, file_path: Union[str, Path], 
                          must_exist: bool = False, 
                          allowed_extensions: List[str] = None) -> bool:
        """Validate file path.
        
        Args:
            file_path: File path to validate
            must_exist: Whether file must exist
            allowed_extensions: List of allowed file extensions (optional)
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If file path is invalid
        """
        if not isinstance(file_path, (str, Path)):
            raise ValidationError(f"File path must be string or Path, got {type(file_path)}")
        
        path = Path(file_path)
        
        # Check if path is absolute or relative
        if path.is_absolute() and not str(path).startswith(str(Path.cwd())):
            self.logger.warning(f"Absolute path used: {path}")
        
        # Check if file exists
        if must_exist and not path.exists():
            raise ValidationError(f"File does not exist: {path}")
        
        # Check file extension
        if allowed_extensions:
            suffix = path.suffix.lower()
            if suffix not in [ext.lower() for ext in allowed_extensions]:
                raise ValidationError(f"File extension {suffix} not in allowed extensions: {allowed_extensions}")
        
        # Check for invalid characters in path
        invalid_chars = ['<', '>', '|', '"', '?', '*']
        path_str = str(path)
        for char in invalid_chars:
            if char in path_str:
                raise ValidationError(f"File path contains invalid character: {char}")
        
        self.logger.debug(f"File path '{path}' validated successfully")
        return True
    
    def validate_configuration(self, config: Dict[str, Any], 
                             required_keys: List[str] = None) -> bool:
        """Validate configuration dictionary structure.
        
        Args:
            config: Configuration dictionary to validate
            required_keys: List of required top-level keys (optional)
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise ValidationError(f"Configuration must be a dictionary, got {type(config)}")
        
        # Check required keys
        if required_keys:
            missing_keys = set(required_keys) - set(config.keys())
            if missing_keys:
                raise ValidationError(f"Missing required configuration keys: {missing_keys}")
        
        # Validate structure
        self._validate_config_structure(config)
        
        self.logger.debug("Configuration validated successfully")
        return True
    
    def _validate_config_structure(self, config: Dict[str, Any], path: str = ""):
        """Recursively validate configuration structure.
        
        Args:
            config: Configuration dictionary to validate
            path: Current path in configuration (for error reporting)
        """
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check key type
            if not isinstance(key, str):
                raise ValidationError(f"Configuration key must be string at {current_path}")
            
            # Check for empty keys
            if not key:
                raise ValidationError(f"Configuration key cannot be empty at {current_path}")
            
            # Validate value type
            if isinstance(value, dict):
                # Recursively validate nested dictionaries
                self._validate_config_structure(value, current_path)
            elif isinstance(value, list):
                # Validate list items
                for i, item in enumerate(value):
                    item_path = f"{current_path}[{i}]"
                    if isinstance(item, dict):
                        self._validate_config_structure(item, item_path)
            elif value is not None and not isinstance(value, (str, int, float, bool)):
                raise ValidationError(f"Configuration value must be str, int, float, bool, dict, list, or None at {current_path}: {type(value)}")


# Predefined validators for common use cases
def validate_cost_value(value: Any) -> bool:
    """Validate cost value (must be non-negative numeric).
    
    Args:
        value: Value to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If value is invalid
    """
    validator = InputValidator()
    return validator.validate_numeric_value(value, min_value=0.0)


def validate_percentage(value: Any) -> bool:
    """Validate percentage value (0-100 range).
    
    Args:
        value: Value to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If value is invalid
    """
    validator = InputValidator()
    return validator.validate_numeric_value(value, min_value=0.0, max_value=100.0)


def validate_positive_integer(value: Any) -> bool:
    """Validate positive integer value.
    
    Args:
        value: Value to validate
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If value is invalid
    """
    validator = InputValidator()
    if not isinstance(value, (int, np.integer)) or isinstance(value, bool):
        # Try to convert to int
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Value must be integer, got {type(value)}: {value}")
    
    return validator.validate_numeric_value(value, min_value=1)


# Example usage:
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create validator
    validator = InputValidator()
    
    # Test sheet name validation
    try:
        validator.validate_sheet_name("Detailed Table")
        print("Sheet name validation passed")
    except ValidationError as e:
        print(f"Sheet name validation failed: {e}")
    
    # Test cell reference validation
    try:
        validator.validate_cell_reference("A1")
        validator.validate_cell_reference("BZ999")
        print("Cell reference validation passed")
    except ValidationError as e:
        print(f"Cell reference validation failed: {e}")
    
    # Test DataFrame validation
    try:
        df = pd.DataFrame({
            'Test': ['Panel', 'WES (P)', 'WES (T)', 'WGS'],
            'Cost': [50000, 75000, 40000, 60000]
        })
        validator.validate_dataframe(df, expected_columns=['Test', 'Cost'], min_rows=1)
        print("DataFrame validation passed")
    except ValidationError as e:
        print(f"DataFrame validation failed: {e}")
    
    # Test numeric value validation
    try:
        validator.validate_numeric_value(50000, min_value=0)
        validator.validate_numeric_value(-5.5, min_value=-10, max_value=10)
        print("Numeric value validation passed")
    except ValidationError as e:
        print(f"Numeric value validation failed: {e}")
    
    # Test file path validation
    try:
        validator.validate_file_path("./data/test.xlsx", allowed_extensions=['.xlsx', '.xls'])
        print("File path validation passed")
    except ValidationError as e:
        print(f"File path validation failed: {e}")