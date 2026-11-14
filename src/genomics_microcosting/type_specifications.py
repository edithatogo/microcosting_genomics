# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Type Specifications for Genomics Microcosting.

This module defines standardized type specifications for different column categories
in the microcosting system, ensuring consistent data handling and validation.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import SupportsFloat, SupportsIndex

import polars as pl

_PERCENTAGE_MAXIMUM = 100
_MAXIMUM_INVALID_SAMPLES = 3


class DataType(Enum):
    """Enumeration of supported data types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"
    DATE = "date"
    CATEGORICAL = "categorical"


class ColumnCategory(Enum):
    """Enumeration of column categories for microcosting data."""

    IDENTIFIER = "identifier"  # Test names, categories, etc.
    COST = "cost"  # Monetary values
    QUANTITY = "quantity"  # Counts, volumes, etc.
    RATE = "rate"  # Hourly rates, percentages, etc.
    METADATA = "metadata"  # Descriptive information
    CALCULATION = "calculation"  # Computed values


@dataclass(eq=False, repr=False, match_args=False)
class TypeSpecification:
    """Specification for a column's data type and validation rules."""

    data_type: DataType
    category: ColumnCategory
    nullable: bool = True
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = None
    description: str | None = None
    validation_rules: list[str] | None = None

    def __post_init__(self) -> None:
        """Give specifications with omitted or empty rules an independent list."""
        self.validation_rules = self.validation_rules or []

    def validate_value(self, value: object) -> bool:
        """Validate a single value against this specification.

        Args:
            value: Value to validate

        Returns:
            True if valid, False otherwise

        """
        # Check for null values
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return self.nullable

        match self.data_type:
            case DataType.INTEGER:
                return self._valid_integer(value)
            case DataType.FLOAT | DataType.CURRENCY | DataType.PERCENTAGE:
                return self._valid_number(value)
            case DataType.STRING:
                return isinstance(value, str)
            case DataType.BOOLEAN:
                return isinstance(value, bool) or value in [
                    0,
                    1,
                    "0",
                    "1",
                    "True",
                    "False",
                ]
            case _:
                return True

    def _valid_integer(self, value: object) -> bool:
        if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
            return self._within_declared_bounds(value)
        return False

    def _valid_number(self, value: object) -> bool:
        if not isinstance(value, (str, bytes, bytearray, SupportsFloat, SupportsIndex)):
            return False
        try:
            number = float(value)
        except ValueError, TypeError:
            return False
        if self.data_type == DataType.PERCENTAGE and (
            number < 0 or number > _PERCENTAGE_MAXIMUM
        ):
            return False
        return self._within_declared_bounds(number)

    def _within_declared_bounds(self, value: float) -> bool:
        return not (
            (self.min_value is not None and value < self.min_value)
            or (self.max_value is not None and value > self.max_value)
        )

    def get_polars_dtype(self) -> pl.DataType | type[pl.DataType]:
        """Return the native dtype for the declared field without converting data."""
        mapping: dict[DataType, pl.DataType | type[pl.DataType]] = {
            DataType.STRING: pl.String,
            DataType.INTEGER: pl.Int64,
            DataType.FLOAT: pl.Float64,
            DataType.CURRENCY: pl.Float64,
            DataType.PERCENTAGE: pl.Float64,
            DataType.BOOLEAN: pl.Boolean,
            DataType.DATE: pl.Date,
            DataType.CATEGORICAL: pl.Categorical,
        }
        return mapping[self.data_type]

    def get_pandas_dtype(self) -> str:
        """Return the historical dtype label for metadata compatibility only.

        Returns:
            Pandas dtype string

        """
        type_mapping = {
            DataType.STRING: "string",
            DataType.INTEGER: "Int64",  # Nullable integer
            DataType.FLOAT: "Float64",  # Nullable float
            DataType.CURRENCY: "Float64",
            DataType.PERCENTAGE: "Float64",
            DataType.BOOLEAN: "boolean",
            DataType.DATE: "datetime64[ns]",
            DataType.CATEGORICAL: "category",
        }
        return type_mapping.get(self.data_type, "string")


# Predefined type specifications for common microcosting columns
STANDARD_TYPE_SPECS = {
    # Identifier columns
    "test": TypeSpecification(
        data_type=DataType.STRING,
        category=ColumnCategory.IDENTIFIER,
        nullable=False,
        description="Test or assay name",
    ),
    "category": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.IDENTIFIER,
        nullable=False,
        description="Test category",
    ),
    "sub_category": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.IDENTIFIER,
        nullable=True,
        description="Test sub-category",
    ),
    "step": TypeSpecification(
        data_type=DataType.STRING,
        category=ColumnCategory.IDENTIFIER,
        nullable=True,
        description="Process step",
    ),
    # Cost columns
    "unit_cost_aud_per_unit": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD per unit",
        description="Final calculated cost per test unit",
    ),
    "price_aud_per_unit": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD per unit",
        description="Base price per unit",
    ),
    "list_price_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD",
        description="Manufacturer's list price",
    ),
    "annualized_cost_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD per year",
        description="Annualized equipment cost",
    ),
    # Quantity columns
    "quantity_per_test": TypeSpecification(
        data_type=DataType.FLOAT,
        category=ColumnCategory.QUANTITY,
        nullable=True,
        min_value=0,
        unit="units per test",
        description="Resource quantity required per test",
    ),
    "monthly_volume": TypeSpecification(
        data_type=DataType.INTEGER,
        category=ColumnCategory.QUANTITY,
        nullable=True,
        min_value=0,
        unit="tests per month",
        description="Monthly test volume",
    ),
    "useful_life_years": TypeSpecification(
        data_type=DataType.INTEGER,
        category=ColumnCategory.QUANTITY,
        nullable=True,
        min_value=1,
        unit="years",
        description="Equipment useful life in years",
    ),
    # Rate columns
    "hourly_rate_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.RATE,
        nullable=True,
        min_value=0,
        unit="AUD per hour",
        description="Labor hourly rate",
    ),
    "annual_salary_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.RATE,
        nullable=True,
        min_value=0,
        unit="AUD per year",
        description="Annual labor salary",
    ),
    # Metadata columns
    "labor_type": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.METADATA,
        nullable=False,
        description="Type of labor",
    ),
    "equipment_name": TypeSpecification(
        data_type=DataType.STRING,
        category=ColumnCategory.METADATA,
        nullable=False,
        description="Equipment name or description",
    ),
    "test_type": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.METADATA,
        nullable=False,
        description="Type of test",
    ),
}


def get_type_spec(column_name: str) -> TypeSpecification | None:
    """Get the type specification for a column name.

    Args:
        column_name: The column name to look up (case insensitive)

    Returns:
        TypeSpecification if found, None otherwise

    """
    # Case insensitive lookup
    column_name_lower = column_name.lower()
    for key, spec in STANDARD_TYPE_SPECS.items():
        if key.lower() == column_name_lower:
            return spec
    return None


def validate_dataframe_types(
    df: pl.DataFrame,
    type_specs: dict[str, TypeSpecification],
) -> list[str]:
    """Validate all columns in a DataFrame against their type specifications.

    Args:
        df: DataFrame to validate
        type_specs: Dictionary mapping column names to type specifications

    Returns:
        List of validation error messages

    """
    errors: list[str] = []

    for col_name, spec in type_specs.items():
        if col_name not in df.columns:
            if not spec.nullable:
                errors.append(f"Required column '{col_name}' is missing")
            continue

        series = df[col_name]
        invalid_count = 0
        invalid_samples: list[str] = []

        for idx, value in enumerate(series.to_list()):
            if not spec.validate_value(value):
                invalid_count += 1
                if len(invalid_samples) < _MAXIMUM_INVALID_SAMPLES:
                    invalid_samples.append(
                        f"row {idx}: {value} ({type(value).__name__})",
                    )

        if invalid_count > 0:
            error_msg = f"Column '{col_name}' has {invalid_count} invalid values"
            if invalid_samples:
                error_msg += f" (examples: {', '.join(invalid_samples)})"
            errors.append(error_msg)

    return errors


def apply_type_conversions(
    df: pl.DataFrame,
    type_specs: dict[str, TypeSpecification],
) -> pl.DataFrame:
    """Apply type conversions to DataFrame columns based on specifications.

    Args:
        df: DataFrame to convert
        type_specs: Dictionary mapping column names to type specifications

    Returns:
        DataFrame with converted types

    """
    df_converted = df.clone()
    for name, spec in type_specs.items():
        if name not in df.columns:
            continue
        expression = _column_conversion(df, name, spec.data_type)
        if expression is None:
            continue
        try:
            df_converted = df_converted.with_columns(expression.alias(name))
        except pl.exceptions.PolarsError, ValueError, TypeError:
            # Retain the complete original column, matching legacy failure semantics.
            continue
    return df_converted


def _column_conversion(
    df: pl.DataFrame,
    name: str,
    kind: DataType,
) -> pl.Expr | None:
    expression = pl.col(name)
    if kind == DataType.CURRENCY:
        expression = (
            expression.cast(pl.String).str.replace_all(r"[\$,]", "").cast(pl.Float64)
        )
    elif kind == DataType.PERCENTAGE:
        expression = (
            expression.cast(pl.String).str.replace_all("%", "").cast(pl.Float64)
        )
    elif kind == DataType.INTEGER:
        return _integer_conversion(df, name)
    elif kind == DataType.FLOAT:
        expression = expression.cast(pl.Float64, strict=False)
    elif kind == DataType.STRING:
        expression = expression.cast(pl.String)
    elif kind == DataType.BOOLEAN:
        values = df[name].drop_nulls()
        if (df[name].dtype != pl.Boolean) and (
            not df[name].dtype.is_numeric() or not values.is_in([0, 1]).all()
        ):
            return None
        expression = expression.cast(pl.Boolean)
    elif kind == DataType.CATEGORICAL:
        expression = expression.cast(pl.String).cast(pl.Categorical)
    else:
        return None
    return expression


def _integer_conversion(df: pl.DataFrame, name: str) -> pl.Expr | None:
    expression = pl.col(name).cast(pl.Float64, strict=False)
    try:
        values = df.select(expression.alias(name))[name].drop_nulls()
    except pl.exceptions.PolarsError:
        return None
    if ((values % 1) != 0).any():
        return None
    return expression.cast(pl.Int64)
