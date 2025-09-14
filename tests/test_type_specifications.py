"""Tests for type specifications functionality."""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any

from src.genomics_microcosting.type_specifications import (
    DataType,
    ColumnCategory,
    TypeSpecification,
    get_type_spec,
    validate_dataframe_types,
    apply_type_conversions,
    STANDARD_TYPE_SPECS
)


class TestDataType:
    """Test DataType enum functionality."""

    def test_data_type_enum_values(self):
        """Test that DataType enum has expected values."""
        expected_values = [
            "string", "integer", "float", "currency", "percentage",
            "boolean", "date", "categorical"
        ]
        actual_values = [dt.value for dt in DataType]
        assert set(actual_values) == set(expected_values)

    def test_data_type_enum_uniqueness(self):
        """Test that all DataType enum values are unique."""
        values = [dt.value for dt in DataType]
        assert len(values) == len(set(values))


class TestColumnCategory:
    """Test ColumnCategory enum functionality."""

    def test_column_category_enum_values(self):
        """Test that ColumnCategory enum has expected values."""
        expected_values = [
            "identifier", "cost", "quantity", "rate", "metadata", "calculation"
        ]
        actual_values = [cc.value for cc in ColumnCategory]
        assert set(actual_values) == set(expected_values)

    def test_column_category_enum_uniqueness(self):
        """Test that all ColumnCategory enum values are unique."""
        values = [cc.value for cc in ColumnCategory]
        assert len(values) == len(set(values))


class TestTypeSpecification:
    """Test TypeSpecification class functionality."""

    def test_type_spec_initialization(self):
        """Test TypeSpecification initialization with valid parameters."""
        spec = TypeSpecification(
            data_type=DataType.CURRENCY,
            category=ColumnCategory.COST,
            nullable=True,
            min_value=0,
            max_value=1000000,
            unit="AUD",
            description="Test cost column"
        )

        assert spec.data_type == DataType.CURRENCY
        assert spec.category == ColumnCategory.COST
        assert spec.nullable is True
        assert spec.min_value == 0
        assert spec.max_value == 1000000
        assert spec.unit == "AUD"
        assert spec.description == "Test cost column"

    def test_type_spec_validation_valid_value(self):
        """Test validation of valid values."""
        spec = TypeSpecification(
            data_type=DataType.CURRENCY,
            category=ColumnCategory.COST,
            nullable=False,
            min_value=0
        )

        assert spec.validate_value(100.50) is True
        assert spec.validate_value(0) is True
        assert spec.validate_value(None) is False  # Not nullable

    def test_type_spec_validation_invalid_value(self):
        """Test validation of invalid values."""
        spec = TypeSpecification(
            data_type=DataType.INTEGER,
            category=ColumnCategory.QUANTITY,
            nullable=False,
            min_value=0,
            max_value=100
        )

        assert spec.validate_value(-1) is False  # Below min
        assert spec.validate_value(150) is False  # Above max
        assert spec.validate_value("not_a_number") is False  # Wrong type
        assert spec.validate_value(None) is False  # Not nullable

    def test_get_pandas_dtype(self):
        """Test pandas dtype conversion."""
        # Currency should map to Float64 (nullable)
        currency_spec = TypeSpecification(DataType.CURRENCY, ColumnCategory.COST)
        assert currency_spec.get_pandas_dtype() == "Float64"

        # Integer should map to Int64 (nullable)
        int_spec = TypeSpecification(DataType.INTEGER, ColumnCategory.QUANTITY)
        assert int_spec.get_pandas_dtype() == "Int64"

        # String should map to string
        str_spec = TypeSpecification(DataType.STRING, ColumnCategory.IDENTIFIER)
        assert str_spec.get_pandas_dtype() == "string"


class TestGetTypeSpec:
    """Test get_type_spec function."""

    def test_get_existing_type_spec(self):
        """Test getting existing type specifications."""
        spec = get_type_spec("unit_cost_aud_per_unit")
        assert spec is not None
        assert spec.data_type == DataType.CURRENCY
        assert spec.category == ColumnCategory.COST

    def test_get_nonexistent_type_spec(self):
        """Test getting non-existent type specification."""
        spec = get_type_spec("nonexistent_column")
        assert spec is None

    def test_get_type_spec_case_insensitive(self):
        """Test that get_type_spec is case insensitive."""
        spec1 = get_type_spec("unit_cost_aud_per_unit")
        spec2 = get_type_spec("UNIT_COST_AUD_PER_UNIT")
        assert spec1 is not None
        assert spec2 is not None
        assert spec1.data_type == spec2.data_type


class TestValidateDataframeTypes:
    """Test validate_dataframe_types function."""

    def test_validate_valid_dataframe(self):
        """Test validation of a valid dataframe."""
        # Create test dataframe
        df = pd.DataFrame({
            "test": ["Test1", "Test2", "Test3"],
            "unit_cost_aud_per_unit": [100.0, 200.0, 300.0],
            "quantity_per_test": [1, 2, 3]
        })

        # Create type specs
        type_specs = {
            "test": get_type_spec("test"),
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test")
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Validate
        errors = validate_dataframe_types(df, type_specs)
        assert len(errors) == 0

    def test_validate_invalid_dataframe(self):
        """Test validation of an invalid dataframe."""
        # Create test dataframe with invalid data
        df = pd.DataFrame({
            "unit_cost_aud_per_unit": [-100.0, "invalid", None],  # Negative, string, null
            "quantity_per_test": [1, 2, 3]
        })

        # Create type specs
        type_specs = {
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test")
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Validate
        errors = validate_dataframe_types(df, type_specs)
        assert len(errors) > 0
        assert any("negative" in error.lower() or "invalid" in error.lower() for error in errors)


class TestApplyTypeConversions:
    """Test apply_type_conversions function."""

    def test_apply_conversions_valid_data(self):
        """Test applying type conversions to valid data."""
        # Create test dataframe with string numbers
        df = pd.DataFrame({
            "test": ["Test1", "Test2"],
            "unit_cost_aud_per_unit": ["100.50", "200.75"],
            "quantity_per_test": ["1", "2"]
        })

        # Create type specs
        type_specs = {
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test")
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Apply conversions
        converted_df = apply_type_conversions(df, type_specs)

        # Check that numeric columns were converted
        assert pd.api.types.is_numeric_dtype(converted_df["unit_cost_aud_per_unit"])
        assert pd.api.types.is_numeric_dtype(converted_df["quantity_per_test"])
        assert str(converted_df["unit_cost_aud_per_unit"].dtype) == "Float64"
        assert str(converted_df["quantity_per_test"].dtype) == "Float64"

    def test_apply_conversions_invalid_data(self):
        """Test applying type conversions to invalid data."""
        # Create test dataframe with invalid data
        df = pd.DataFrame({
            "unit_cost_aud_per_unit": ["invalid", "200.75"],
            "quantity_per_test": ["1", "2"]
        })

        # Create type specs
        type_specs = {
            "unit_cost_aud_per_unit": get_type_spec("unit_cost_aud_per_unit"),
            "quantity_per_test": get_type_spec("quantity_per_test")
        }

        # Filter out None specs
        type_specs = {k: v for k, v in type_specs.items() if v is not None}

        # Apply conversions - should handle errors gracefully
        converted_df = apply_type_conversions(df, type_specs)

        # Check that the dataframe still exists and has NaN for invalid values
        assert len(converted_df) == 2
        # The invalid value should be NaN after conversion
        assert pd.isna(converted_df["unit_cost_aud_per_unit"].iloc[0]) or str(converted_df["unit_cost_aud_per_unit"].iloc[0]) == "invalid"


class TestStandardTypeSpecs:
    """Test STANDARD_TYPE_SPECS dictionary."""

    def test_standard_type_specs_structure(self):
        """Test that STANDARD_TYPE_SPECS has expected structure."""
        assert isinstance(STANDARD_TYPE_SPECS, dict)
        assert len(STANDARD_TYPE_SPECS) > 0

        # Check that all values are TypeSpecification instances
        for column_name, spec in STANDARD_TYPE_SPECS.items():
            assert isinstance(spec, TypeSpecification)
            assert isinstance(column_name, str)

    def test_standard_type_specs_coverage(self):
        """Test that STANDARD_TYPE_SPECS covers common column types."""
        expected_columns = [
            "test", "category", "unit_cost_aud_per_unit", "price_aud_per_unit",
            "quantity_per_test", "hourly_rate_aud", "annual_salary_aud"
        ]

        for column in expected_columns:
            assert column in STANDARD_TYPE_SPECS, f"Missing type spec for {column}"

    def test_standard_type_specs_consistency(self):
        """Test that STANDARD_TYPE_SPECS values are consistent."""
        for column_name, spec in STANDARD_TYPE_SPECS.items():
            # Check that data_type is a valid DataType
            assert isinstance(spec.data_type, DataType)
            # Check that category is a valid ColumnCategory
            assert isinstance(spec.category, ColumnCategory)
            # Check that nullable is a boolean
            assert isinstance(spec.nullable, bool)


class TestIntegrationScenarios:
    """Test integration scenarios for type specifications."""

    def test_complete_workflow(self):
        """Test a complete workflow from spec lookup to validation."""
        # 1. Get type spec
        spec = get_type_spec("unit_cost_aud_per_unit")
        assert spec is not None

        # 2. Create test data
        df = pd.DataFrame({
            "unit_cost_aud_per_unit": [100.0, 200.0, 300.0],
            "quantity_per_test": [1, 2, 3]
        })

        # 3. Validate
        type_specs = {"unit_cost_aud_per_unit": spec}
        errors = validate_dataframe_types(df, type_specs)
        assert len(errors) == 0

        # 4. Apply conversions
        converted_df = apply_type_conversions(df, type_specs)
        assert pd.api.types.is_numeric_dtype(converted_df["unit_cost_aud_per_unit"])

    def test_error_handling(self):
        """Test error handling in type specification functions."""
        # Test with empty dataframe
        empty_df = pd.DataFrame()
        errors = validate_dataframe_types(empty_df, {})
        assert isinstance(errors, list)

        # Test with None type specs
        df = pd.DataFrame({"col": [1, 2, 3]})
        converted_df = apply_type_conversions(df, {})
        assert len(converted_df) == 3