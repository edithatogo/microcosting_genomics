# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Input validation for genomics microcosting analysis.

This module provides comprehensive input validation capabilities for all aspects
of the microcosting analysis system, including data validation, configuration
validation, and parameter validation.
"""

import logging
import re
from pathlib import Path
from typing import SupportsFloat, SupportsIndex, SupportsInt, cast
lazy from collections.abc import Mapping, Sequence

import numpy as np
import polars as pl
import polars.selectors as cs

from .logging_config import get_logger

logger = get_logger(__name__)
MAX_SHEET_NAME_LENGTH = 255
MAX_WORKSHEET_COLUMN = 16_384
MAX_WORKSHEET_ROW = 1_048_576
MAX_NULL_PERCENTAGE = 90


class ValidationError(Exception):
    """Custom exception for input validation errors."""


class InputValidator:
    """Comprehensive input validation for microcosting analysis."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the input validator.

        Args:
            logger: Logger instance (optional)

        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")

    def validate_sheet_name(self, sheet_name: object) -> bool:
        """Validate sheet name format and content.

        Args:
            sheet_name: Sheet name to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValidationError: If sheet name is invalid

        """
        if not isinstance(sheet_name, str):
            message = f"Sheet name must be a string, got {type(sheet_name)}"
            raise ValidationError(
                message,
            )

        if not sheet_name:
            message = "Sheet name cannot be empty"
            raise ValidationError(message)

        if len(sheet_name) > MAX_SHEET_NAME_LENGTH:
            message = "Sheet name cannot exceed 255 characters"
            raise ValidationError(message)

        # Check for invalid characters (Excel restrictions)
        invalid_chars = ["\\", "/", "*", "[", "]", ":", "?"]
        for char in invalid_chars:
            if char in sheet_name:
                message = f"Sheet name contains invalid character: {char}"
                raise ValidationError(message)

        self.logger.debug("Sheet name '%s' validated successfully", sheet_name)
        return True

    def validate_cell_reference(self, cell_ref: object) -> bool:
        """Validate Excel cell reference format.

        Args:
            cell_ref: Cell reference to validate (e.g., "A1", "BZ999")

        Returns:
            True if valid, False otherwise

        Raises:
            ValidationError: If cell reference is invalid

        """
        if not isinstance(cell_ref, str):
            message = f"Cell reference must be a string, got {type(cell_ref)}"
            raise ValidationError(
                message,
            )

        if not cell_ref:
            message = "Cell reference cannot be empty"
            raise ValidationError(message)

        # Check if it's just a number (common parsing error)
        if cell_ref.isdigit():
            message = f"Cell reference cannot be just a number: {cell_ref}"
            raise ValidationError(message)

        # Regex pattern for Excel cell references (e.g., A1, BZ999, $A$2)
        # Allow dollar signs for absolute references and underscores for temporary
        # references
        # Support both single cells and range references (with colons)
        single_cell_pattern = r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[A-Z0-9]+)*$"
        single_cell_alt_pattern = r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[a-z0-9]+)*$"

        # Range reference pattern (e.g., A1:B2, $A$1:$B$2, AK81:AK86)
        range_pattern = (
            r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[A-Z0-9]+)*:"
            r"\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[A-Z0-9]+)*$"
        )
        range_alt_pattern = (
            r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[a-z0-9]+)*:"
            r"\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[a-z0-9]+)*$"
        )

        is_single_cell = re.match(single_cell_pattern, cell_ref) or re.match(
            single_cell_alt_pattern,
            cell_ref,
        )
        is_range = re.match(range_pattern, cell_ref) or re.match(
            range_alt_pattern,
            cell_ref,
        )

        if not (is_single_cell or is_range):
            message = f"Invalid cell reference format: {cell_ref}"
            raise ValidationError(message)

        # For range references, validate both start and end cells
        if is_range and ":" in cell_ref:
            start_ref, end_ref = cell_ref.split(":")
            # Validate start cell
            self._validate_single_cell_reference(start_ref)
            # Validate end cell
            self._validate_single_cell_reference(end_ref)
            self.logger.debug("Range reference '%s' validated successfully", cell_ref)
            return True
        # For single cell references, use existing validation
        return self._validate_single_cell_reference(cell_ref)

    def _column_to_number(self, column: str) -> int:
        """Convert Excel column letter to number.

        Args:
            column: Column letter(s) (e.g., "A", "BZ")

        Returns:
            Column number (1-based)

        """
        result = 0
        for char in column:
            result = result * 26 + (ord(char) - ord("A") + 1)
        return result

    def _validate_single_cell_reference(self, cell_ref: str) -> bool:
        """Validate a single cell reference (helper method for range validation).

        Args:
            cell_ref: Single cell reference to validate (e.g., "A1", "BZ999")

        Returns:
            True if valid

        Raises:
            ValidationError: If cell reference is invalid

        """
        # Regex pattern for single Excel cell references
        pattern = r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[A-Z0-9]+)*$"
        alt_pattern = r"^\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}(_[a-z0-9]+)*$"
        if not (re.match(pattern, cell_ref) or re.match(alt_pattern, cell_ref)):
            message = f"Invalid cell reference format: {cell_ref}"
            raise ValidationError(message)

        # Extract column and row (handle suffixes like _ERR)
        base_ref = cell_ref.split("_", maxsplit=1)[0]
        col_part = "".join([c for c in base_ref if c.isalpha()])
        row_part = "".join([c for c in base_ref if c.isdigit()])

        # Validate column range (A to XFD = 1 to 16384)
        col_number = self._column_to_number(col_part)
        if not 1 <= col_number <= MAX_WORKSHEET_COLUMN:
            message = f"Column out of range: {col_part}"
            raise ValidationError(message)

        # Validate row range (1 to 1048576)
        row_number = int(row_part)
        if not 1 <= row_number <= MAX_WORKSHEET_ROW:
            message = f"Row out of range: {row_number}"
            raise ValidationError(message)

        return True

    def validate_dataframe(
        self,
        df: object,
        expected_columns: list[str] | None = None,
        min_rows: int = 0,
        max_rows: int | None = None,
    ) -> bool:
        """Validate Polars DataFrame structure and content.

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
        if not isinstance(df, pl.DataFrame):
            message = f"Expected Polars DataFrame, got {type(df)}"
            raise ValidationError(message)

        # Check row count
        row_count = len(df)
        if row_count < min_rows:
            message = f"DataFrame has {row_count} rows, minimum required is {min_rows}"
            raise ValidationError(
                message,
            )

        if max_rows is not None and row_count > max_rows:
            message = f"DataFrame has {row_count} rows, maximum allowed is {max_rows}"
            raise ValidationError(
                message,
            )

        # Check columns
        if expected_columns:
            missing_columns = set(expected_columns) - set(df.columns)
            if missing_columns:
                message = f"Missing expected columns: {missing_columns}"
                raise ValidationError(message)

        # Check for excessive null values
        view = df.with_columns(cs.float().fill_nan(None))
        total_cells = df.height * df.width
        null_percentage = (
            sum(view.null_count().row(0)) / total_cells * 100 if total_cells else 0.0
        )
        if null_percentage > MAX_NULL_PERCENTAGE:
            message = (
                f"DataFrame has {null_percentage:.2f}% null values, which is excessive"
            )
            raise ValidationError(
                message,
            )

        self.logger.debug(
            "DataFrame validated successfully: %s rows, %s columns",
            df.shape[0],
            df.shape[1],
        )
        return True

    def validate_numeric_value(
        self,
        value: object,
        min_value: float | None = None,
        max_value: float | None = None,
        *,
        allow_none: bool = False,
    ) -> bool:
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
            message = "Value cannot be None"
            raise ValidationError(message)

        # Check if value is numeric
        if not isinstance(value, (int, float, np.integer, np.floating)):
            # Try to convert to float
            if not isinstance(
                value,
                (str, bytes, bytearray, SupportsFloat, SupportsIndex),
            ):
                message = f"Value must be numeric, got {type(value)}: {value}"
                raise ValidationError(message)
            try:
                value = float(value)
            except (ValueError, TypeError) as exc:
                message = f"Value must be numeric, got {type(value)}: {value}"
                raise ValidationError(
                    message,
                ) from exc

        # Check range
        if min_value is not None and value < min_value:
            message = f"Value {value} is less than minimum {min_value}"
            raise ValidationError(message)

        if max_value is not None and value > max_value:
            message = f"Value {value} is greater than maximum {max_value}"
            raise ValidationError(message)

        # Check for special float values
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            message = f"Value cannot be NaN or infinite: {value}"
            raise ValidationError(message)

        self.logger.debug("Numeric value validated successfully")
        return True

    def validate_string_value(
        self,
        value: object,
        max_length: int | None = None,
        pattern: str | None = None,
        *,
        allow_empty: bool = False,
    ) -> bool:
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
            message = "Value cannot be None"
            raise ValidationError(message)

        # Convert to string if needed
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception as exc:
                message = f"Value cannot be converted to string: {value}"
                raise ValidationError(message) from exc

        # Check empty string
        if not value and not allow_empty:
            message = "String value cannot be empty"
            raise ValidationError(message)

        # Check length
        if max_length is not None and len(value) > max_length:
            message = f"String length {len(value)} exceeds maximum {max_length}"
            raise ValidationError(
                message,
            )

        # Check pattern
        if pattern is not None and not re.match(pattern, value):
            message = f"String '{value}' does not match pattern: {pattern}"
            raise ValidationError(
                message,
            )

        self.logger.debug("String value '%s' validated successfully", value)
        return True

    def validate_file_path(
        self,
        file_path: object,
        *,
        must_exist: bool = False,
        allowed_extensions: list[str] | None = None,
    ) -> bool:
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
            message = f"File path must be string or Path, got {type(file_path)}"
            raise ValidationError(
                message,
            )

        path = Path(file_path)

        # Check if path is absolute or relative
        if path.is_absolute() and not str(path).startswith(str(Path.cwd())):
            self.logger.warning("Absolute path used: %s", path)

        # Check if file exists
        if must_exist and not path.exists():
            message = f"File does not exist: {path}"
            raise ValidationError(message)

        # Check file extension
        if allowed_extensions:
            suffix = path.suffix.lower()
            if suffix not in [ext.lower() for ext in allowed_extensions]:
                message = (
                    f"File extension {suffix} not in "
                    f"allowed extensions: {allowed_extensions}"
                )
                raise ValidationError(
                    message,
                )

        # Check for invalid characters in path
        invalid_chars = ["<", ">", "|", '"', "?", "*"]
        path_str = str(path)
        for char in invalid_chars:
            if char in path_str:
                message = f"File path contains invalid character: {char}"
                raise ValidationError(message)

        self.logger.debug("File path '%s' validated successfully", path)
        return True

    def validate_configuration(
        self,
        config: object,
        required_keys: list[str] | None = None,
    ) -> bool:
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
            message = f"Configuration must be a dictionary, got {type(config)}"
            raise ValidationError(
                message,
            )

        fields = cast("Mapping[object, object]", config)

        # Check required keys
        if required_keys:
            missing_keys = set(required_keys) - set(fields)
            if missing_keys:
                message = f"Missing required configuration keys: {missing_keys}"
                raise ValidationError(
                    message,
                )

        # Validate structure
        self._validate_config_structure(fields)

        self.logger.debug("Configuration validated successfully")
        return True

    def _validate_config_structure(
        self,
        config: Mapping[object, object],
        path: str = "",
    ) -> None:
        """Recursively validate configuration structure.

        Args:
            config: Configuration dictionary to validate
            path: Current path in configuration (for error reporting)

        """
        for key, value in config.items():
            if not isinstance(key, str):
                message = f"Configuration key must be string at {path or '<root>'}"
                raise ValidationError(message)
            current_path = f"{path}.{key}" if path else key

            # Check for empty keys
            if not key:
                message = f"Configuration key cannot be empty at {current_path}"
                raise ValidationError(
                    message,
                )

            # Validate value type
            if isinstance(value, dict):
                # Recursively validate nested dictionaries
                self._validate_config_structure(
                    cast("Mapping[object, object]", value),
                    current_path,
                )
            elif isinstance(value, list):
                # Validate list items
                for i, item in enumerate(cast("Sequence[object]", value)):
                    item_path = f"{current_path}[{i}]"
                    if isinstance(item, dict):
                        self._validate_config_structure(
                            cast("Mapping[object, object]", item),
                            item_path,
                        )
            elif value is not None and not isinstance(value, (str, int, float, bool)):
                message = (
                    f"Configuration value must be str, int, float, bool, "
                    f"dict, list, or None at {current_path}: {type(value)}"
                )
                raise ValidationError(
                    message,
                )


# Predefined validators for common use cases
def validate_cost_value(value: object) -> bool:
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


def validate_percentage(value: object) -> bool:
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


def validate_positive_integer(value: object) -> bool:
    """Validate positive integer value.

    Args:
        value: Value to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If value is invalid

    """
    validator = InputValidator()
    try:
        if isinstance(value, (int, str, bytes, bytearray, SupportsInt, SupportsIndex)):
            integer = int(value)
        else:
            message = f"Value must be integer, got {type(value)}: {value}"
            raise ValidationError(message)
    except (ValueError, TypeError) as exc:
        message = f"Value must be integer, got {type(value)}: {value}"
        raise ValidationError(message) from exc
    return validator.validate_numeric_value(integer, min_value=1)


# Example usage:
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create validator
    validator = InputValidator()

    # Test sheet name validation
    try:
        validator.validate_sheet_name("Detailed Table")
        logger.info("%s", "Sheet name validation passed")
    except ValidationError as e:
        logger.info("%s", f"Sheet name validation failed: {e}")

    # Test cell reference validation
    try:
        validator.validate_cell_reference("A1")
        validator.validate_cell_reference("BZ999")
        logger.info("%s", "Cell reference validation passed")
    except ValidationError as e:
        logger.info("%s", f"Cell reference validation failed: {e}")

    # Test DataFrame validation
    try:
        df = pl.DataFrame(
            {
                "Test": ["Panel", "WES (P)", "WES (T)", "WGS"],
                "Cost": [50000, 75000, 40000, 60000],
            },
        )
        validator.validate_dataframe(df, expected_columns=["Test", "Cost"], min_rows=1)
        logger.info("%s", "DataFrame validation passed")
    except ValidationError as e:
        logger.info("%s", f"DataFrame validation failed: {e}")

    # Test numeric value validation
    try:
        validator.validate_numeric_value(50000, min_value=0)
        validator.validate_numeric_value(-5.5, min_value=-10, max_value=10)
        logger.info("%s", "Numeric value validation passed")
    except ValidationError as e:
        logger.info("%s", f"Numeric value validation failed: {e}")

    # Test file path validation
    try:
        validator.validate_file_path(
            "./data/test.xlsx",
            allowed_extensions=[".xlsx", ".xls"],
        )
        logger.info("%s", "File path validation passed")
    except ValidationError as e:
        logger.info("%s", f"File path validation failed: {e}")
