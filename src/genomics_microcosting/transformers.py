# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Transformer components for the genomics microcosting data pipeline.

This module contains concrete implementations of transformer components
for data processing, validation, and calculation operations.
"""

import re
from typing import Literal, TypedDict
lazy from collections.abc import Mapping

import polars as pl
import polars.selectors as cs
from pydantic import ConfigDict, TypeAdapter, with_config

from .config import load_config
from .data_pipeline import Transformer


@with_config(ConfigDict(strict=True, extra="forbid"))
class CleaningConfig(TypedDict, total=False):
    """Make row deletion, filling and normalisation explicit configured choices."""

    remove_duplicates: bool
    handle_missing: Literal["preserve", "drop", "fill", "interpolate"]
    fill_value: str | int | float | bool | None
    normalize_text: bool


CLEANING_CONFIG_ADAPTER = TypeAdapter(CleaningConfig)
_HIGH_MISSING_FRACTION = 0.5


class ValidationIssues(TypedDict):
    """Keep validation findings outside the immutable source dataframe."""

    total_rows: int
    total_columns: int
    issues: list[str]


class _CostColumn(TypedDict):
    name: str
    type: Literal["unit_cost", "total_cost", "percentage", "cost"]


class HeaderNormalizer(Transformer):
    """Transformer to normalize and standardize column headers."""

    def __init__(
        self,
        name: str,
        column_mappings: dict[str, str] | None = None,
    ) -> None:
        """Initialise the transformer with optional column mappings."""
        super().__init__(name)
        self.column_mappings: dict[str, str]
        if column_mappings is None:
            config = load_config()
            # Extract column mappings from config
            self.column_mappings = {}
            for workbook_config in config.get("workbooks", {}).values():
                for sheet_config in workbook_config.get(
                    "sheets",
                    {},
                ).values():
                    mappings = sheet_config.get("column_mapping", {})
                    self.column_mappings.update(mappings)
        else:
            self.column_mappings = column_mappings

    def transform(
        self,
        data: pl.DataFrame | dict[str, pl.DataFrame],
    ) -> pl.DataFrame | dict[str, pl.DataFrame]:
        """Normalize column headers in the data."""
        if isinstance(data, dict):
            return {
                sheet_name: self._normalize_dataframe(df)
                for sheet_name, df in data.items()
            }
        # Handle single DataFrame
        return self._normalize_dataframe(data)

    def _normalize_dataframe(self, df: pl.DataFrame) -> pl.DataFrame:
        """Normalize headers for a single DataFrame."""
        df_normalized = df.clone()

        # Apply column mappings
        rename_dict = {
            old_name: new_name
            for old_name, new_name in self.column_mappings.items()
            if old_name in df_normalized.columns
        }

        if rename_dict:
            df_normalized = df_normalized.rename(rename_dict)
            self.logger.info("Renamed %s columns", len(rename_dict))

        # Standardize column names (snake_case, lowercase)
        standardized_columns: dict[str, str] = {}
        for col in df_normalized.columns:
            if (
                col not in rename_dict.values()
            ):  # Don't standardize already mapped columns
                standardized = self._standardize_column_name(col)
                if standardized != col:
                    standardized_columns[col] = standardized

        if standardized_columns:
            df_normalized = df_normalized.rename(standardized_columns)
            self.logger.info("Standardized %s column names", len(standardized_columns))

        return df_normalized

    def _standardize_column_name(self, name: str) -> str:
        """Convert column name to standardized format."""
        # Convert to lowercase
        name = name.lower()

        # Replace spaces and special characters with underscores
        name = re.sub(r"[^a-z0-9]+", "_", name)

        # Remove multiple consecutive underscores
        name = re.sub(r"_+", "_", name)

        # Remove leading/trailing underscores
        return name.strip("_")


class CostCalculator(Transformer):
    """Transformer to calculate costs and perform cost-related computations."""

    def __init__(
        self,
        name: str,
        cost_config: Mapping[str, object] | None = None,
    ) -> None:
        """Initialise the transformer with optional cost configuration."""
        super().__init__(name)
        if cost_config is None:
            config = load_config()
            self.cost_config = config.get("cost_config", {})
        else:
            self.cost_config = cost_config

    def transform(
        self,
        data: pl.DataFrame | dict[str, pl.DataFrame],
    ) -> pl.DataFrame | dict[str, pl.DataFrame]:
        """Calculate costs in the data."""
        if isinstance(data, dict):
            # Handle multiple sheets
            transformed_data: dict[str, pl.DataFrame] = {}
            for sheet_name, df in data.items():
                transformed_data[sheet_name] = self._calculate_costs(df, sheet_name)
            return transformed_data
        # Handle single DataFrame
        return self._calculate_costs(data, "default")

    def _calculate_costs(self, df: pl.DataFrame, sheet_name: str) -> pl.DataFrame:
        """Calculate costs for a single DataFrame."""
        df_calculated = df.clone()

        # Look for cost-related columns and perform calculations
        cost_columns = self._identify_cost_columns(df_calculated)

        if not cost_columns:
            self.logger.info("No cost columns found in %s", sheet_name)
            return df_calculated

        self.logger.info("Found %s cost columns in %s", len(cost_columns), sheet_name)

        # Perform cost calculations
        for col_info in cost_columns:
            col_name = col_info["name"]
            calculation_type = col_info["type"]

            if calculation_type == "unit_cost":
                df_calculated = self._calculate_unit_costs(df_calculated, col_name)
            elif calculation_type == "total_cost":
                df_calculated = self._calculate_total_costs(df_calculated, col_name)
            elif calculation_type == "percentage":
                df_calculated = self._calculate_percentages(df_calculated, col_name)

        return df_calculated

    def _identify_cost_columns(self, df: pl.DataFrame) -> list[_CostColumn]:
        """Identify columns that contain cost data."""
        cost_columns: list[_CostColumn] = []

        for col in df.columns:
            col_str = str(col).lower()

            # Check for cost-related keywords
            if any(
                keyword in col_str for keyword in ["cost", "price", "amount", "fee"]
            ):
                if "unit" in col_str:
                    cost_columns.append({"name": col, "type": "unit_cost"})
                elif "total" in col_str:
                    cost_columns.append({"name": col, "type": "total_cost"})
                elif "percentage" in col_str or "%" in col_str:
                    cost_columns.append({"name": col, "type": "percentage"})
                else:
                    cost_columns.append({"name": col, "type": "cost"})

        return cost_columns

    def _calculate_unit_costs(self, df: pl.DataFrame, col_name: str) -> pl.DataFrame:
        """Calculate unit costs if needed."""
        # For now, just ensure numeric type
        if df[col_name].dtype == pl.String:
            df = df.with_columns(pl.col(col_name).cast(pl.Float64, strict=False))
        return df

    def _calculate_total_costs(self, df: pl.DataFrame, col_name: str) -> pl.DataFrame:
        """Calculate total costs if needed."""
        # For now, just ensure numeric type
        if df[col_name].dtype == pl.String:
            df = df.with_columns(pl.col(col_name).cast(pl.Float64, strict=False))
        return df

    def _calculate_percentages(self, df: pl.DataFrame, col_name: str) -> pl.DataFrame:
        """Calculate percentages if needed."""
        # For now, just ensure numeric type
        if df[col_name].dtype == pl.String:
            df = df.with_columns(pl.col(col_name).cast(pl.Float64, strict=False))
        return df


class ValidationChecker(Transformer):
    """Transformer to validate data quality and integrity."""

    def __init__(
        self,
        name: str,
        validation_rules: Mapping[str, object] | None = None,
    ) -> None:
        """Initialise the transformer with optional validation rules."""
        super().__init__(name)
        self.results: dict[str, ValidationIssues] = {}
        if validation_rules is None:
            config = load_config()
            self.validation_rules = config.get("validation_rules", {})
        else:
            self.validation_rules = validation_rules

    def transform(
        self,
        data: pl.DataFrame | dict[str, pl.DataFrame],
    ) -> pl.DataFrame | dict[str, pl.DataFrame]:
        """Validate data quality."""
        if isinstance(data, dict):
            # Handle multiple sheets
            for sheet_name, df in data.items():
                self._validate_dataframe(df, sheet_name)
            return data
        # Handle single DataFrame
        self._validate_dataframe(data, "default")
        return data

    def _validate_dataframe(self, df: pl.DataFrame, sheet_name: str) -> None:
        """Validate a single DataFrame."""
        self.logger.info("Validating data for %s", sheet_name)

        validation_results: ValidationIssues = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "issues": [],
        }

        view = df.with_columns(cs.float().fill_nan(None))
        for col, count in view.null_count().row(0, named=True).items():
            if len(df) and count / len(df) > _HIGH_MISSING_FRACTION:
                validation_results["issues"].append(
                    (
                        f"High missing data in {col}: "
                        f"{100 * count / len(df):.1f}% ({count}/{len(df)})"
                    ),
                )
        duplicate_count = view.height - view.unique(maintain_order=True).height
        if duplicate_count:
            validation_results["issues"].append(
                f"Found {duplicate_count} duplicate rows",
            )
        for col in view.select(cs.string()).columns:
            sample = view[col].drop_nulls().head(10).cast(pl.Float64, strict=False)
            if sample.is_not_null().any():
                validation_results["issues"].append(
                    (
                        f"Column {col} appears to contain "
                        f"numeric data but is stored as text"
                    ),
                )
        for col in view.select(cs.numeric()).columns:
            if "cost" in col.lower() or "price" in col.lower():
                count = (view[col] < 0).sum()
                if count:
                    validation_results["issues"].append(
                        f"Found {count} negative values in cost column {col}",
                    )
        self.results[sheet_name] = validation_results
        for issue in validation_results["issues"]:
            self.logger.warning("%s", issue)


class DataCleaner(Transformer):
    """Transformer to clean and preprocess data."""

    def __init__(
        self,
        name: str,
        cleaning_config: CleaningConfig | None = None,
    ) -> None:
        """Initialise the transformer with optional cleaning settings."""
        super().__init__(name)
        self.cleaning_config: CleaningConfig
        if cleaning_config is None:
            self.cleaning_config = {
                "remove_duplicates": False,
                "handle_missing": "preserve",  # 'drop', 'fill', 'interpolate'
                "fill_value": 0,
                "normalize_text": False,
            }
        else:
            self.cleaning_config = CLEANING_CONFIG_ADAPTER.validate_python(
                cleaning_config,
            )

    def transform(
        self,
        data: pl.DataFrame | dict[str, pl.DataFrame],
    ) -> pl.DataFrame | dict[str, pl.DataFrame]:
        """Clean and preprocess data."""
        if isinstance(data, dict):
            return {
                sheet_name: self._clean_dataframe(df) for sheet_name, df in data.items()
            }
        return self._clean_dataframe(data)

    def _clean_dataframe(self, df: pl.DataFrame) -> pl.DataFrame:
        """Clean a single DataFrame."""
        df_clean = df.clone()
        if self.cleaning_config.get("remove_duplicates", False):
            df_clean = df_clean.with_columns(cs.float().fill_nan(None)).unique(
                maintain_order=True,
            )
        strategy = self.cleaning_config.get("handle_missing", "preserve")
        if strategy in {"drop", "fill", "interpolate"}:
            df_clean = df_clean.with_columns(cs.float().fill_nan(None))
        if strategy == "drop":
            df_clean = df_clean.drop_nulls()
        elif strategy == "fill":
            df_clean = df_clean.fill_null(self.cleaning_config.get("fill_value", 0))
        elif strategy == "interpolate":
            df_clean = df_clean.with_columns(cs.numeric().interpolate().forward_fill())
        if self.cleaning_config.get("normalize_text", False):
            df_clean = df_clean.with_columns(
                cs.string().str.strip_chars().str.to_lowercase(),
            )
        return df_clean
