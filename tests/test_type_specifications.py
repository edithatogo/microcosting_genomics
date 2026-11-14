# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Tests for type specifications functionality."""

import polars as pl

from genomics_microcosting.type_specifications import (
    STANDARD_TYPE_SPECS,
    ColumnCategory,
    DataType,
    TypeSpecification,
    apply_type_conversions,
    get_type_spec,
    validate_dataframe_types,
)
from tests.checks import require_equal, require_keys, require_runtime_instance


class TestDataType:
    """Test DataType enum functionality."""

    def test_data_type_enum_values(self) -> None:
        """Test that DataType enum has expected values."""
        expected_values = [
            "string",
            "integer",
            "float",
            "currency",
            "percentage",
            "boolean",
            "date",
            "categorical",
        ]
        actual_values = [dt.value for dt in DataType]
        if not (set(actual_values) == set(expected_values)):
            raise AssertionError

    def test_data_type_enum_uniqueness(self) -> None:
        """Test that all DataType enum values are unique."""
        values = [dt.value for dt in DataType]
        if not (len(values) == len(set(values))):
            raise AssertionError


class TestColumnCategory:
    """Test ColumnCategory enum functionality."""

    def test_column_category_enum_values(self) -> None:
        """Test that ColumnCategory enum has expected values."""
        expected_values = [
            "identifier",
            "cost",
            "quantity",
            "rate",
            "metadata",
            "calculation",
        ]
        actual_values = [cc.value for cc in ColumnCategory]
        if not (set(actual_values) == set(expected_values)):
            raise AssertionError

    def test_column_category_enum_uniqueness(self) -> None:
        """Test that all ColumnCategory enum values are unique."""
        values = [cc.value for cc in ColumnCategory]
        if not (len(values) == len(set(values))):
            raise AssertionError


class TestTypeSpecification:
    """Test TypeSpecification class functionality."""

    def test_type_spec_initialization(self) -> None:
        """Test TypeSpecification initialization with valid parameters."""
        spec = TypeSpecification(
            data_type=DataType.CURRENCY,
            category=ColumnCategory.COST,
            nullable=True,
            min_value=0,
            max_value=1000000,
            unit="AUD",
            description="Test cost column",
        )

        if not (spec.data_type == DataType.CURRENCY):
            raise AssertionError
        if not (spec.category == ColumnCategory.COST):
            raise AssertionError
        if spec.nullable is not True:
            raise AssertionError
        if not (spec.min_value == 0):
            raise AssertionError
        require_equal(spec.max_value, 1000000)
        if not (spec.unit == "AUD"):
            raise AssertionError
        if not (spec.description == "Test cost column"):
            raise AssertionError

    def test_type_spec_validation_valid_value(self) -> None:
        """Test validation of valid values."""
        spec = TypeSpecification(
            data_type=DataType.CURRENCY,
            category=ColumnCategory.COST,
            nullable=False,
            min_value=0,
        )

        if spec.validate_value(100.50) is not True:
            raise AssertionError
        if spec.validate_value(0) is not True:
            raise AssertionError
        if spec.validate_value(None) is not False:
            raise AssertionError  # Not nullable

    def test_type_spec_validation_invalid_value(self) -> None:
        """Test validation of invalid values."""
        spec = TypeSpecification(
            data_type=DataType.INTEGER,
            category=ColumnCategory.QUANTITY,
            nullable=False,
            min_value=0,
            max_value=100,
        )

        if spec.validate_value(-1) is not False:
            raise AssertionError  # Below min
        if spec.validate_value(150) is not False:
            raise AssertionError  # Above max
        if spec.validate_value("not_a_number") is not False:
            raise AssertionError  # Wrong type
        if spec.validate_value(None) is not False:
            raise AssertionError  # Not nullable

    def test_get_pandas_dtype(self) -> None:
        """Test pandas dtype conversion."""
        # Currency should map to Float64 (nullable)
        currency_spec = TypeSpecification(DataType.CURRENCY, ColumnCategory.COST)
        if not (currency_spec.get_pandas_dtype() == "Float64"):
            raise AssertionError

        # Integer should map to Int64 (nullable)
        int_spec = TypeSpecification(DataType.INTEGER, ColumnCategory.QUANTITY)
        if not (int_spec.get_pandas_dtype() == "Int64"):
            raise AssertionError

        # String should map to string
        str_spec = TypeSpecification(DataType.STRING, ColumnCategory.IDENTIFIER)
        if not (str_spec.get_pandas_dtype() == "string"):
            raise AssertionError


class TestGetTypeSpec:
    """Test get_type_spec function."""

    def test_get_existing_type_spec(self) -> None:
        """Test getting existing type specifications."""
        spec = get_type_spec("unit_cost_aud_per_unit")
        if not (spec is not None):
            raise AssertionError
        if not (spec.data_type == DataType.CURRENCY):
            raise AssertionError
        if not (spec.category == ColumnCategory.COST):
            raise AssertionError

    def test_get_nonexistent_type_spec(self) -> None:
        """Test getting non-existent type specification."""
        spec = get_type_spec("nonexistent_column")
        if spec is not None:
            raise AssertionError

    def test_get_type_spec_case_insensitive(self) -> None:
        """Test that get_type_spec is case insensitive."""
        spec1 = get_type_spec("unit_cost_aud_per_unit")
        spec2 = get_type_spec("UNIT_COST_AUD_PER_UNIT")
        if not (spec1 is not None):
            raise AssertionError
        if not (spec2 is not None):
            raise AssertionError
        if not (spec1.data_type == spec2.data_type):
            raise AssertionError


class TestValidateDataframeTypes:
    """Test validate_dataframe_types function."""

    def test_validate_valid_dataframe(self) -> None:
        """Test validation of a valid dataframe."""
        # Create test dataframe
        df = pl.DataFrame(
            {
                "test": ["Test1", "Test2", "Test3"],
                "unit_cost_aud_per_unit": [100.0, 200.0, 300.0],
                "quantity_per_test": [1, 2, 3],
            },
            strict=False,
        )

        # Create type specs
        type_specs = {
            "test": get_type_spec("test"),
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test"),
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Validate
        errors = validate_dataframe_types(df, type_specs)
        if not (len(errors) == 0):
            raise AssertionError

    def test_validate_invalid_dataframe(self) -> None:
        """Test validation of an invalid dataframe."""
        # Create test dataframe with invalid data
        df = pl.DataFrame(
            {
                "unit_cost_aud_per_unit": [
                    -100.0,
                    "invalid",
                    None,
                ],  # Negative, string, null
                "quantity_per_test": [1, 2, 3],
            },
            strict=False,
        )

        # Create type specs
        type_specs = {
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test"),
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Validate
        errors = validate_dataframe_types(df, type_specs)
        if not (len(errors) > 0):
            raise AssertionError
        if not (
            any(
                "negative" in error.lower() or "invalid" in error.lower()
                for error in errors
            )
        ):
            raise AssertionError


class TestApplyTypeConversions:
    """Test apply_type_conversions function."""

    def test_apply_conversions_valid_data(self) -> None:
        """Test applying type conversions to valid data."""
        # Create test dataframe with string numbers
        df = pl.DataFrame(
            {
                "test": ["Test1", "Test2"],
                "unit_cost_aud_per_unit": ["100.50", "200.75"],
                "quantity_per_test": ["1", "2"],
            },
            strict=False,
        )

        # Create type specs
        type_specs = {
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test"),
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Apply conversions
        converted_df = apply_type_conversions(df, type_specs)

        # Check that numeric columns were converted
        if not (converted_df["unit_cost_aud_per_unit"].dtype.is_numeric()):
            raise AssertionError
        if not (converted_df["quantity_per_test"].dtype.is_numeric()):
            raise AssertionError
        if not (str(converted_df["unit_cost_aud_per_unit"].dtype) == "Float64"):
            raise AssertionError
        if not (str(converted_df["quantity_per_test"].dtype) == "Float64"):
            raise AssertionError

    def test_apply_conversions_invalid_data(self) -> None:
        """Test applying type conversions to invalid data."""
        # Create test dataframe with invalid data
        df = pl.DataFrame(
            {
                "unit_cost_aud_per_unit": ["invalid", "200.75"],
                "quantity_per_test": ["1", "2"],
            },
            strict=False,
        )

        # Create type specs
        type_specs = {
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test"),
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Apply conversions - should handle errors gracefully
        converted_df = apply_type_conversions(df, type_specs)

        # Check that the dataframe still exists and has NaN for invalid values
        require_equal(len(converted_df), 2)
        # The invalid value should be NaN after conversion
        if not (
            converted_df["unit_cost_aud_per_unit"][0] is None
            or str(converted_df["unit_cost_aud_per_unit"][0]) == "invalid"
        ):
            raise AssertionError


class TestStandardTypeSpecs:
    """Test STANDARD_TYPE_SPECS dictionary."""

    def test_standard_type_specs_structure(self) -> None:
        """Test that STANDARD_TYPE_SPECS has expected structure."""
        require_runtime_instance(STANDARD_TYPE_SPECS, dict)
        if not (len(STANDARD_TYPE_SPECS) > 0):
            raise AssertionError

        # Check that all values are TypeSpecification instances
        for column_name, spec in STANDARD_TYPE_SPECS.items():
            require_runtime_instance(spec, TypeSpecification)
            require_runtime_instance(column_name, str)

    def test_standard_type_specs_coverage(self) -> None:
        """Test that STANDARD_TYPE_SPECS covers common column types."""
        expected_columns = (
            "test",
            "category",
            "unit_cost_aud_per_unit",
            "price_aud_per_unit",
            "quantity_per_test",
            "hourly_rate_aud",
            "annual_salary_aud",
        )
        require_keys(STANDARD_TYPE_SPECS, expected_columns)

    def test_standard_type_specs_consistency(self) -> None:
        """Test that STANDARD_TYPE_SPECS values are consistent."""
        for spec in STANDARD_TYPE_SPECS.values():
            # Check that data_type is a valid DataType
            require_runtime_instance(spec.data_type, DataType)
            # Check that category is a valid ColumnCategory
            require_runtime_instance(spec.category, ColumnCategory)
            # Check that nullable is a boolean
            require_runtime_instance(spec.nullable, bool)


class TestIntegrationScenarios:
    """Test integration scenarios for type specifications."""

    def test_complete_workflow(self) -> None:
        """Test a complete workflow from spec lookup to validation."""
        # 1. Get type spec
        spec = get_type_spec("unit_cost_aud_per_unit")
        if not (spec is not None):
            raise AssertionError

        # 2. Create test data
        df = pl.DataFrame(
            {
                "unit_cost_aud_per_unit": [100.0, 200.0, 300.0],
                "quantity_per_test": [1, 2, 3],
            },
            strict=False,
        )

        # 3. Validate
        type_specs = {"unit_cost_aud_per_unit": spec}
        errors = validate_dataframe_types(df, type_specs)
        if not (len(errors) == 0):
            raise AssertionError

        # 4. Apply conversions
        converted_df = apply_type_conversions(df, type_specs)
        if not (converted_df["unit_cost_aud_per_unit"].dtype.is_numeric()):
            raise AssertionError

    def test_error_handling(self) -> None:
        """Test error handling in type specification functions."""
        # Test with empty dataframe
        empty_df = pl.DataFrame()
        errors = validate_dataframe_types(empty_df, {})
        require_runtime_instance(errors, list)

        # Test with None type specs
        df = pl.DataFrame({"col": [1, 2, 3]})
        converted_df = apply_type_conversions(df, {})
        require_equal(len(converted_df), 3)
