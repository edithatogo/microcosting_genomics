"""Type Specifications for Genomics Microcosting.

This module defines standardized type specifications for different column categories
in the microcosting system, ensuring consistent data handling and validation.
"""

from typing import Dict, Any, List, Optional, Union
from enum import Enum
import pandas as pd


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


class TypeSpecification:
    """Specification for a column's data type and validation rules."""

    def __init__(
        self,
        data_type: DataType,
        category: ColumnCategory,
        nullable: bool = True,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        unit: Optional[str] = None,
        description: Optional[str] = None,
        validation_rules: Optional[List[str]] = None
    ):
        """Initialize type specification.

        Args:
            data_type: The expected data type
            category: The column category
            nullable: Whether null values are allowed
            min_value: Minimum allowed value (for numeric types)
            max_value: Maximum allowed value (for numeric types)
            unit: Unit of measurement (e.g., "AUD", "hours", "%")
            description: Human-readable description
            validation_rules: List of additional validation rule names
        """
        self.data_type = data_type
        self.category = category
        self.nullable = nullable
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self.description = description
        self.validation_rules = validation_rules or []

    def validate_value(self, value: Any) -> bool:
        """Validate a single value against this specification.

        Args:
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        # Check for null values
        if pd.isna(value):
            return self.nullable

        # Type-specific validation
        if self.data_type == DataType.INTEGER:
            if not isinstance(value, int) and not (isinstance(value, float) and value.is_integer()):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False

        elif self.data_type in [DataType.FLOAT, DataType.CURRENCY]:
            try:
                float_value = float(value)
                if self.min_value is not None and float_value < self.min_value:
                    return False
                if self.max_value is not None and float_value > self.max_value:
                    return False
            except (ValueError, TypeError):
                return False

        elif self.data_type == DataType.PERCENTAGE:
            try:
                float_value = float(value)
                if self.min_value is not None and float_value < self.min_value:
                    return False
                if self.max_value is not None and float_value > self.max_value:
                    return False
                # Percentages should typically be between 0 and 100
                if float_value < 0 or float_value > 100:
                    return False
            except (ValueError, TypeError):
                return False

        elif self.data_type == DataType.STRING:
            if not isinstance(value, str):
                return False

        elif self.data_type == DataType.BOOLEAN:
            if not isinstance(value, bool) and value not in [0, 1, "0", "1", "True", "False"]:
                return False

        return True

    def get_pandas_dtype(self) -> str:
        """Get the corresponding pandas dtype for this specification.

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
            DataType.CATEGORICAL: "category"
        }
        return type_mapping.get(self.data_type, "string")


# Predefined type specifications for common microcosting columns
STANDARD_TYPE_SPECS = {
    # Identifier columns
    "test": TypeSpecification(
        data_type=DataType.STRING,
        category=ColumnCategory.IDENTIFIER,
        nullable=False,
        description="Test or assay name"
    ),
    "category": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.IDENTIFIER,
        nullable=False,
        description="Test category"
    ),
    "sub_category": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.IDENTIFIER,
        nullable=True,
        description="Test sub-category"
    ),
    "step": TypeSpecification(
        data_type=DataType.STRING,
        category=ColumnCategory.IDENTIFIER,
        nullable=True,
        description="Process step"
    ),

    # Cost columns
    "unit_cost_aud_per_unit": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD per unit",
        description="Final calculated cost per test unit"
    ),
    "price_aud_per_unit": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD per unit",
        description="Base price per unit"
    ),
    "list_price_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD",
        description="Manufacturer's list price"
    ),
    "annualized_cost_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.COST,
        nullable=True,
        min_value=0,
        unit="AUD per year",
        description="Annualized equipment cost"
    ),

    # Quantity columns
    "quantity_per_test": TypeSpecification(
        data_type=DataType.FLOAT,
        category=ColumnCategory.QUANTITY,
        nullable=True,
        min_value=0,
        unit="units per test",
        description="Resource quantity required per test"
    ),
    "monthly_volume": TypeSpecification(
        data_type=DataType.INTEGER,
        category=ColumnCategory.QUANTITY,
        nullable=True,
        min_value=0,
        unit="tests per month",
        description="Monthly test volume"
    ),
    "useful_life_years": TypeSpecification(
        data_type=DataType.INTEGER,
        category=ColumnCategory.QUANTITY,
        nullable=True,
        min_value=1,
        unit="years",
        description="Equipment useful life in years"
    ),

    # Rate columns
    "hourly_rate_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.RATE,
        nullable=True,
        min_value=0,
        unit="AUD per hour",
        description="Labor hourly rate"
    ),
    "annual_salary_aud": TypeSpecification(
        data_type=DataType.CURRENCY,
        category=ColumnCategory.RATE,
        nullable=True,
        min_value=0,
        unit="AUD per year",
        description="Annual labor salary"
    ),

    # Metadata columns
    "labor_type": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.METADATA,
        nullable=False,
        description="Type of labor"
    ),
    "equipment_name": TypeSpecification(
        data_type=DataType.STRING,
        category=ColumnCategory.METADATA,
        nullable=False,
        description="Equipment name or description"
    ),
    "test_type": TypeSpecification(
        data_type=DataType.CATEGORICAL,
        category=ColumnCategory.METADATA,
        nullable=False,
        description="Type of test"
    )
}


def get_type_spec(column_name: str) -> Optional[TypeSpecification]:
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


def validate_dataframe_types(df: pd.DataFrame, type_specs: Dict[str, TypeSpecification]) -> List[str]:
    """Validate all columns in a DataFrame against their type specifications.

    Args:
        df: DataFrame to validate
        type_specs: Dictionary mapping column names to type specifications

    Returns:
        List of validation error messages
    """
    errors = []

    for col_name, spec in type_specs.items():
        if col_name not in df.columns:
            if not spec.nullable:
                errors.append(f"Required column '{col_name}' is missing")
            continue

        series = df[col_name]
        invalid_count = 0
        invalid_samples = []

        for idx, value in series.items():
            if not spec.validate_value(value):
                invalid_count += 1
                if len(invalid_samples) < 3:  # Collect up to 3 examples
                    invalid_samples.append(f"row {idx}: {value} ({type(value).__name__})")

        if invalid_count > 0:
            error_msg = f"Column '{col_name}' has {invalid_count} invalid values"
            if invalid_samples:
                error_msg += f" (examples: {', '.join(invalid_samples)})"
            errors.append(error_msg)

    return errors


def apply_type_conversions(df: pd.DataFrame, type_specs: Dict[str, TypeSpecification]) -> pd.DataFrame:
    """Apply type conversions to DataFrame columns based on specifications.

    Args:
        df: DataFrame to convert
        type_specs: Dictionary mapping column names to type specifications

    Returns:
        DataFrame with converted types
    """
    df_converted = df.copy()

    for col_name, spec in type_specs.items():
        if col_name not in df_converted.columns:
            continue

        try:
            if spec.data_type == DataType.CURRENCY:
                # Remove currency symbols and convert to float
                df_converted[col_name] = (
                    df_converted[col_name]
                    .astype(str)
                    .str.replace(r'[\$,]', '', regex=True)
                    .astype('Float64')
                )
            elif spec.data_type == DataType.PERCENTAGE:
                # Remove percentage symbols and convert to float
                df_converted[col_name] = (
                    df_converted[col_name]
                    .astype(str)
                    .str.replace(r'[%]', '', regex=True)
                    .astype('Float64')
                )
            elif spec.data_type == DataType.INTEGER:
                df_converted[col_name] = pd.to_numeric(df_converted[col_name], errors='coerce').astype('Int64')
            elif spec.data_type == DataType.FLOAT:
                df_converted[col_name] = pd.to_numeric(df_converted[col_name], errors='coerce').astype('Float64')
            elif spec.data_type == DataType.STRING:
                df_converted[col_name] = df_converted[col_name].astype('string')
            elif spec.data_type == DataType.BOOLEAN:
                df_converted[col_name] = df_converted[col_name].astype('boolean')
            elif spec.data_type == DataType.CATEGORICAL:
                df_converted[col_name] = df_converted[col_name].astype('category')
        except (ValueError, TypeError) as e:
            # Log warning but don't fail - keep original data
            print(f"Warning: Could not convert column '{col_name}' to {spec.data_type.value}: {e}")

    return df_converted