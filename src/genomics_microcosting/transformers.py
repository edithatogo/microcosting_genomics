"""
Transformer Components for Genomics Microcosting Data Pipeline

This module contains concrete implementations of transformer components
for data processing, validation, and calculation operations.
"""

from typing import Any, Dict, List, Optional, Union
import logging
import re

import pandas as pd
import numpy as np

from .data_pipeline import Transformer
from .config import load_config


class HeaderNormalizer(Transformer):
    """Transformer to normalize and standardize column headers."""

    def __init__(self, name: str, column_mappings: Optional[Dict[str, str]] = None):
        super().__init__(name)
        if column_mappings is None:
            config = load_config()
            # Extract column mappings from config
            self.column_mappings = {}
            for workbook_key, workbook_config in config.get("workbooks", {}).items():
                for sheet_name, sheet_config in workbook_config.get("sheets", {}).items():
                    mappings = sheet_config.get("column_mapping", {})
                    self.column_mappings.update(mappings)
        else:
            self.column_mappings = column_mappings

    def transform(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Normalize column headers in the data."""
        if isinstance(data, dict):
            # Handle multiple sheets
            transformed_data = {}
            for sheet_name, df in data.items():
                transformed_data[sheet_name] = self._normalize_dataframe(df)
            return transformed_data
        else:
            # Handle single DataFrame
            return self._normalize_dataframe(data)

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize headers for a single DataFrame."""
        df_normalized = df.copy()

        # Apply column mappings
        rename_dict = {}
        for old_name, new_name in self.column_mappings.items():
            if old_name in df_normalized.columns:
                rename_dict[old_name] = new_name

        if rename_dict:
            df_normalized = df_normalized.rename(columns=rename_dict)
            self.logger.info(f"Renamed {len(rename_dict)} columns")

        # Standardize column names (snake_case, lowercase)
        standardized_columns = {}
        for col in df_normalized.columns:
            if col not in rename_dict.values():  # Don't standardize already mapped columns
                standardized = self._standardize_column_name(col)
                if standardized != col:
                    standardized_columns[col] = standardized

        if standardized_columns:
            df_normalized = df_normalized.rename(columns=standardized_columns)
            self.logger.info(f"Standardized {len(standardized_columns)} column names")

        return df_normalized

    def _standardize_column_name(self, name: str) -> str:
        """Convert column name to standardized format."""
        # Convert to lowercase
        name = name.lower()

        # Replace spaces and special characters with underscores
        name = re.sub(r'[^a-z0-9]+', '_', name)

        # Remove multiple consecutive underscores
        name = re.sub(r'_+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        return name


class CostCalculator(Transformer):
    """Transformer to calculate costs and perform cost-related computations."""

    def __init__(self, name: str, cost_config: Optional[Dict] = None):
        super().__init__(name)
        if cost_config is None:
            config = load_config()
            self.cost_config = config.get("cost_config", {})
        else:
            self.cost_config = cost_config

    def transform(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Calculate costs in the data."""
        if isinstance(data, dict):
            # Handle multiple sheets
            transformed_data = {}
            for sheet_name, df in data.items():
                transformed_data[sheet_name] = self._calculate_costs(df, sheet_name)
            return transformed_data
        else:
            # Handle single DataFrame
            return self._calculate_costs(data, "default")

    def _calculate_costs(self, df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
        """Calculate costs for a single DataFrame."""
        df_calculated = df.copy()

        # Look for cost-related columns and perform calculations
        cost_columns = self._identify_cost_columns(df_calculated)

        if not cost_columns:
            self.logger.info(f"No cost columns found in {sheet_name}")
            return df_calculated

        self.logger.info(f"Found {len(cost_columns)} cost columns in {sheet_name}")

        # Perform cost calculations
        for col_info in cost_columns:
            col_name = col_info['name']
            calculation_type = col_info['type']

            if calculation_type == 'unit_cost':
                df_calculated = self._calculate_unit_costs(df_calculated, col_name)
            elif calculation_type == 'total_cost':
                df_calculated = self._calculate_total_costs(df_calculated, col_name)
            elif calculation_type == 'percentage':
                df_calculated = self._calculate_percentages(df_calculated, col_name)

        return df_calculated

    def _identify_cost_columns(self, df: pd.DataFrame) -> List[Dict]:
        """Identify columns that contain cost data."""
        cost_columns = []

        for col in df.columns:
            col_str = str(col).lower()

            # Check for cost-related keywords
            if any(keyword in col_str for keyword in ['cost', 'price', 'amount', 'fee']):
                if 'unit' in col_str:
                    cost_columns.append({'name': col, 'type': 'unit_cost'})
                elif 'total' in col_str:
                    cost_columns.append({'name': col, 'type': 'total_cost'})
                elif 'percentage' in col_str or '%' in col_str:
                    cost_columns.append({'name': col, 'type': 'percentage'})
                else:
                    cost_columns.append({'name': col, 'type': 'cost'})

        return cost_columns

    def _calculate_unit_costs(self, df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        """Calculate unit costs if needed."""
        # For now, just ensure numeric type
        if df[col_name].dtype == 'object':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        return df

    def _calculate_total_costs(self, df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        """Calculate total costs if needed."""
        # For now, just ensure numeric type
        if df[col_name].dtype == 'object':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        return df

    def _calculate_percentages(self, df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        """Calculate percentages if needed."""
        # For now, just ensure numeric type
        if df[col_name].dtype == 'object':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        return df


class ValidationChecker(Transformer):
    """Transformer to validate data quality and integrity."""

    def __init__(self, name: str, validation_rules: Optional[Dict] = None):
        super().__init__(name)
        if validation_rules is None:
            config = load_config()
            self.validation_rules = config.get("validation_rules", {})
        else:
            self.validation_rules = validation_rules

    def transform(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Validate data quality."""
        if isinstance(data, dict):
            # Handle multiple sheets
            for sheet_name, df in data.items():
                self._validate_dataframe(df, sheet_name)
            return data
        else:
            # Handle single DataFrame
            self._validate_dataframe(data, "default")
            return data

    def _validate_dataframe(self, df: pd.DataFrame, sheet_name: str) -> None:
        """Validate a single DataFrame."""
        self.logger.info(f"Validating data for {sheet_name}")

        validation_results = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'issues': []
        }

        # Check for missing values
        missing_data = df.isnull().sum()
        if missing_data.any():
            for col, count in missing_data[missing_data > 0].items():
                percentage = (count / len(df)) * 100
                if percentage > 50:  # More than 50% missing
                    validation_results['issues'].append(
                        f"High missing data in {col}: {percentage:.1f}% ({count}/{len(df)})"
                    )

        # Check for duplicate rows
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            validation_results['issues'].append(
                f"Found {duplicate_count} duplicate rows"
            )

        # Check data types
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if numeric columns are stored as strings
                try:
                    numeric_sample = pd.to_numeric(df[col].dropna().head(10), errors='coerce')
                    if not numeric_sample.isna().all():
                        validation_results['issues'].append(
                            f"Column {col} appears to contain numeric data but is stored as text"
                        )
                except:
                    pass

        # Check for negative values in cost columns
        cost_cols = [col for col in df.columns if 'cost' in str(col).lower() or 'price' in str(col).lower()]
        for col in cost_cols:
            if df[col].dtype in ['int64', 'float64']:
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    validation_results['issues'].append(
                        f"Found {negative_count} negative values in cost column {col}"
                    )

        # Log validation results
        if validation_results['issues']:
            self.logger.warning(f"Validation issues found in {sheet_name}:")
            for issue in validation_results['issues']:
                self.logger.warning(f"  - {issue}")
        else:
            self.logger.info(f"No validation issues found in {sheet_name}")

        # Store validation results for potential use by other components
        df.attrs['validation_results'] = validation_results


class DataCleaner(Transformer):
    """Transformer to clean and preprocess data."""

    def __init__(self, name: str, cleaning_config: Optional[Dict] = None):
        super().__init__(name)
        if cleaning_config is None:
            self.cleaning_config = {
                'remove_duplicates': True,
                'handle_missing': 'interpolate',  # 'drop', 'fill', 'interpolate'
                'fill_value': 0,
                'normalize_text': True
            }
        else:
            self.cleaning_config = cleaning_config

    def transform(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Clean and preprocess data."""
        if isinstance(data, dict):
            # Handle multiple sheets
            transformed_data = {}
            for sheet_name, df in data.items():
                transformed_data[sheet_name] = self._clean_dataframe(df, sheet_name)
            return transformed_data
        else:
            # Handle single DataFrame
            return self._clean_dataframe(data, "default")

    def _clean_dataframe(self, df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
        """Clean a single DataFrame."""
        df_clean = df.copy()

        # Remove duplicates
        if self.cleaning_config.get('remove_duplicates', True):
            original_count = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            removed_count = original_count - len(df_clean)
            if removed_count > 0:
                self.logger.info(f"Removed {removed_count} duplicate rows from {sheet_name}")

        # Handle missing values
        missing_strategy = self.cleaning_config.get('handle_missing', 'interpolate')
        if missing_strategy == 'drop':
            df_clean = df_clean.dropna()
        elif missing_strategy == 'fill':
            fill_value = self.cleaning_config.get('fill_value', 0)
            df_clean = df_clean.fillna(fill_value)
        elif missing_strategy == 'interpolate':
            # Interpolate numeric columns
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            df_clean[numeric_cols] = df_clean[numeric_cols].interpolate(method='linear')

        # Normalize text columns
        if self.cleaning_config.get('normalize_text', True):
            text_cols = df_clean.select_dtypes(include=['object']).columns
            for col in text_cols:
                df_clean[col] = df_clean[col].astype(str).str.strip().str.lower()

        return df_clean