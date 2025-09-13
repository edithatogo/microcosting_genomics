#!/usr/bin/env python3
"""
Model Transformation Engine

This script transforms original genomic models into standardized format
using the templates and rules defined in the configuration files.

The transformation process:
1. Loads original model data
2. Applies standardization mappings
3. Validates against templates
4. Generates standardized output files
5. Creates transformation reports
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import yaml
import json
from dataclasses import dataclass
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TransformationResult:
    """Container for transformation results."""
    model_name: str
    original_rows: int
    transformed_rows: int
    transformations_applied: Dict[str, int]
    validation_passed: bool
    validation_errors: List[str]
    validation_warnings: List[str]
    output_path: Optional[str]

@dataclass
class ModelTemplate:
    """Template for a standardized model."""
    name: str
    required_columns: List[str]
    optional_columns: List[str]
    column_order: List[str]
    data_types: Dict[str, str]
    validation_rules: Dict[str, Any]
    default_values: Dict[str, Any]

class ModelTransformationEngine:
    """Engine for transforming models to standardized format."""

    def __init__(self, config_path: str = "config/standard_categories.yaml",
                 templates_dir: str = "config/templates"):
        self.config_path = Path(config_path)
        self.templates_dir = Path(templates_dir)
        self.config = self.load_config()
        self.templates = self.load_templates()

        self.models = [
            "Panel",
            "WES (P)",
            "WES (T)",
            "WGS",
            "WGS (T)"
        ]

    def load_config(self) -> Dict:
        """Load the standardization configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_templates(self) -> Dict[str, ModelTemplate]:
        """Load all available templates."""
        templates = {}

        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return templates

        # Load all JSON template files
        for json_file in self.templates_dir.glob("*_template.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)

                # Convert default_values back from strings
                default_values = {}
                for k, v in template_data['default_values'].items():
                    if v == 'NaT':
                        default_values[k] = pd.NaT
                    elif v == '':
                        default_values[k] = ''
                    else:
                        try:
                            # Try to convert numeric strings
                            if '.' in str(v):
                                default_values[k] = float(v)
                            else:
                                default_values[k] = int(v)
                        except (ValueError, TypeError):
                            default_values[k] = v

                template = ModelTemplate(
                    name=template_data['name'],
                    required_columns=template_data['required_columns'],
                    optional_columns=template_data['optional_columns'],
                    column_order=template_data['column_order'],
                    data_types=template_data['data_types'],
                    validation_rules=template_data['validation_rules'],
                    default_values=default_values
                )

                template_key = template_data['name'].replace('_template', '')
                templates[template_key] = template

            except Exception as e:
                logger.error(f"Error loading template {json_file}: {e}")

        return templates

    def get_template_for_model(self, model_name: str) -> ModelTemplate:
        """Get the appropriate template for a model."""
        # Try model-specific template first
        model_key = model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
        if model_key in self.templates:
            return self.templates[model_key]

        # Fall back to base template
        if 'base' in self.templates:
            return self.templates['base']

        raise ValueError(f"No suitable template found for model {model_name}")

    def load_original_model(self, model_name: str) -> Optional[pd.DataFrame]:
        """Load original model data."""
        data_path = Path("data/Detailed Table.csv")

        if not data_path.exists():
            logger.error(f"Data file not found: {data_path}")
            return None

        try:
            # Load and find the model's data
            df = pd.read_csv(data_path, header=None)

            # Find header row
            header_row_idx: Optional[int] = None
            for idx in range(len(df)):
                row = df.iloc[idx]
                if 'Test' in str(row.values) and 'Category' in str(row.values):
                    header_row_idx = idx
                    break

            if header_row_idx is None:
                logger.error("Could not find header row")
                return None

            # Read with correct header
            df = pd.read_csv(data_path, header=header_row_idx)

            # Extract model data
            model_data = self.extract_model_data(df, model_name)
            return model_data

        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return None

    def extract_model_data(self, df: pd.DataFrame, model_name: str) -> Optional[pd.DataFrame]:
        """Extract data for a specific model."""
        # Find all rows with non-empty Test values
        test_rows = df[df['Test'].notna()].index.tolist()

        for i, row_idx in enumerate(test_rows):
            test_value = df.loc[row_idx, 'Test']

            if test_value == model_name:
                # Collect all rows for this test
                start_idx = row_idx
                end_idx = test_rows[i + 1] if i + 1 < len(test_rows) else len(df)

                test_df = df.loc[start_idx:end_idx-1].copy()
                test_df['Test'] = test_df['Test'].fillna(test_value)
                return test_df

        return None

    def apply_standardization_mappings(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """Apply all standardization mappings to the dataframe."""
        transformations = {
            'category_mappings': 0,
            'subcategory_mappings': 0,
            'data_type_conversions': 0,
            'missing_value_fills': 0
        }

        df_copy = df.copy()

        # Apply category mappings
        category_mappings = self.config.get('standardization_mappings', {}).get('category_mappings', {})
        if 'Category' in df_copy.columns and category_mappings:
            original_categories = df_copy['Category'].copy()
            df_copy['Category'] = df_copy['Category'].map(
                lambda x: category_mappings.get(x, x) if pd.notna(x) else x
            )
            transformations['category_mappings'] = sum(1 for orig, mapped in zip(original_categories, df_copy['Category'])
                                                     if orig != mapped and pd.notna(orig) and orig in category_mappings)

        # Apply subcategory mappings
        subcategory_mappings = self.config.get('standardization_mappings', {}).get('subcategory_mappings', {})
        if 'Sub-Category' in df_copy.columns and subcategory_mappings:
            original_subcats = df_copy['Sub-Category'].copy()
            df_copy['Sub-Category'] = df_copy['Sub-Category'].map(
                lambda x: subcategory_mappings.get(x, x) if pd.notna(x) else x
            )
            transformations['subcategory_mappings'] = sum(1 for orig, mapped in zip(original_subcats, df_copy['Sub-Category'])
                                                        if orig != mapped and pd.notna(orig) and orig in subcategory_mappings)

        return df_copy, transformations

    def apply_template_formatting(self, df: pd.DataFrame, template: ModelTemplate) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """Apply template formatting to the dataframe."""
        transformations = {
            'columns_reordered': 0,
            'missing_columns_added': 0,
            'data_types_converted': 0,
            'default_values_applied': 0
        }

        df_copy = df.copy()

        # Add missing columns with default values
        for col in template.column_order:
            if col not in df_copy.columns:
                default_value = template.default_values.get(col, '')
                df_copy[col] = default_value
                transformations['missing_columns_added'] += 1

        # Reorder columns according to template
        existing_columns = [col for col in template.column_order if col in df_copy.columns]
        df_copy = df_copy[existing_columns]
        transformations['columns_reordered'] = 1

        # Fill missing values with defaults BEFORE type conversion
        for col, default_value in template.default_values.items():
            if col in df_copy.columns:
                if pd.isna(default_value):
                    # Don't fill NaT values
                    continue
                mask = df_copy[col].isna()
                if mask.any():
                    df_copy.loc[mask, col] = default_value
                    transformations['default_values_applied'] += mask.sum()

        # Apply data type conversions
        for col, dtype in template.data_types.items():
            if col in df_copy.columns:
                try:
                    if dtype == 'category':
                        # Get unique values including defaults, then create categorical
                        unique_values = df_copy[col].dropna().unique()
                        df_copy[col] = pd.Categorical(df_copy[col], categories=unique_values)
                        transformations['data_types_converted'] += 1
                    elif dtype == 'datetime64[ns]':
                        df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
                        transformations['data_types_converted'] += 1
                    elif dtype == 'float64':
                        df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').astype('float64')
                        transformations['data_types_converted'] += 1
                    elif dtype == 'int64':
                        df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').astype('int64')
                        transformations['data_types_converted'] += 1
                    elif dtype == 'string':
                        df_copy[col] = df_copy[col].astype('string')
                        transformations['data_types_converted'] += 1
                except Exception as e:
                    logger.warning(f"Could not convert column {col} to {dtype}: {e}")

        return df_copy, transformations

    def validate_transformed_model(self, df: pd.DataFrame, template: ModelTemplate, model_name: str) -> Tuple[bool, List[str], List[str]]:
        """Validate the transformed model against template rules."""
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("Transformed model is empty")
            return False, errors, warnings

        # Check required columns
        missing_required = set(template.required_columns) - set(df.columns)
        if missing_required:
            errors.append(f"Missing required columns: {', '.join(missing_required)}")

        # Check required categories
        required_categories = template.validation_rules.get('required_categories', [])
        present_categories = set(df['Category'].dropna().unique())
        missing_categories = set(required_categories) - present_categories
        if missing_categories:
            errors.append(f"Missing required categories: {', '.join(missing_categories)}")

        # Check minimum subcategories
        min_subcategories = template.validation_rules.get('minimum_subcategories', {})
        for category, min_count in min_subcategories.items():
            if category in present_categories:
                subcats = df[df['Category'] == category]['Sub-Category'].dropna().unique()
                if len(subcats) < min_count:
                    warnings.append(f"Category '{category}' has {len(subcats)} subcategories, minimum is {min_count}")

        # Check for invalid categories
        standard_categories = set(template.validation_rules.get('standard_categories', []))
        invalid_categories = present_categories - standard_categories
        if invalid_categories:
            warnings.append(f"Non-standard categories present: {', '.join(invalid_categories)}")

        # Check data integrity
        for col in template.required_columns:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    warnings.append(f"Column '{col}' has {null_count} null values")

        # Check cost calculations if numeric columns exist
        if 'Unit Cost (AUD $/unit)' in df.columns and 'Units' in df.columns and 'Total Cost (AUD)' in df.columns:
            try:
                # Convert to numeric for calculation check
                unit_cost = pd.to_numeric(df['Unit Cost (AUD $/unit)'], errors='coerce')
                units = pd.to_numeric(df['Units'], errors='coerce')
                total_cost = pd.to_numeric(df['Total Cost (AUD)'], errors='coerce')

                # Check if total = unit * units (allowing for small rounding differences)
                calculated_total = unit_cost * units
                mask = (~pd.isna(calculated_total)) & (~pd.isna(total_cost))
                if mask.any():
                    diff = np.abs(calculated_total[mask] - total_cost[mask])
                    max_diff = diff.max()
                    if max_diff > 0.01:  # Allow for 1 cent difference
                        warnings.append(".2f")
            except Exception as e:
                warnings.append(f"Could not validate cost calculations: {e}")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def transform_model(self, model_name: str) -> TransformationResult:
        """Transform a single model to standardized format."""
        logger.info(f"Starting transformation of {model_name}")

        # Load original data
        original_df = self.load_original_model(model_name)
        if original_df is None:
            return TransformationResult(
                model_name=model_name,
                original_rows=0,
                transformed_rows=0,
                transformations_applied={},
                validation_passed=False,
                validation_errors=["Could not load original model data"],
                validation_warnings=[],
                output_path=None
            )

        original_rows = len(original_df)

        # Get appropriate template
        try:
            template = self.get_template_for_model(model_name)
        except ValueError as e:
            return TransformationResult(
                model_name=model_name,
                original_rows=original_rows,
                transformed_rows=0,
                transformations_applied={},
                validation_passed=False,
                validation_errors=[str(e)],
                validation_warnings=[],
                output_path=None
            )

        # Apply standardization mappings
        df_step1, mappings_transforms = self.apply_standardization_mappings(original_df)

        # Apply template formatting
        df_step2, template_transforms = self.apply_template_formatting(df_step1, template)

        # Combine transformations
        all_transformations = {**mappings_transforms, **template_transforms}

        # Validate the transformed model
        is_valid, errors, warnings = self.validate_transformed_model(df_step2, template, model_name)

        # Save transformed model
        output_path = None
        if is_valid and not df_step2.empty:
            output_dir = Path("data/standardized")
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}_standardized.csv"
            output_path = str(output_dir / filename)

            df_step2.to_csv(output_path, index=False)
            logger.info(f"Saved transformed model to: {output_path}")

        result = TransformationResult(
            model_name=model_name,
            original_rows=original_rows,
            transformed_rows=len(df_step2) if df_step2 is not None else 0,
            transformations_applied=all_transformations,
            validation_passed=is_valid,
            validation_errors=errors,
            validation_warnings=warnings,
            output_path=output_path
        )

        logger.info(f"Completed transformation of {model_name}: {result.transformed_rows} rows, {sum(all_transformations.values())} transformations applied")
        return result

    def transform_all_models(self) -> Dict[str, TransformationResult]:
        """Transform all models to standardized format."""
        results = {}

        for model_name in self.models:
            try:
                result = self.transform_model(model_name)
                results[model_name] = result

                status = "✅" if result.validation_passed else "❌"
                logger.info(f"{status} Transformed {model_name}")

                if result.validation_errors:
                    logger.error(f"  Errors: {', '.join(result.validation_errors)}")
                if result.validation_warnings:
                    logger.warning(f"  Warnings: {', '.join(result.validation_warnings)}")

            except Exception as e:
                logger.error(f"Failed to transform {model_name}: {e}")
                results[model_name] = TransformationResult(
                    model_name=model_name,
                    original_rows=0,
                    transformed_rows=0,
                    transformations_applied={},
                    validation_passed=False,
                    validation_errors=[str(e)],
                    validation_warnings=[],
                    output_path=None
                )

        return results

    def generate_transformation_report(self, results: Dict[str, TransformationResult]) -> str:
        """Generate a comprehensive transformation report."""
        report = []
        report.append("# Model Transformation Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        total_models = len(results)
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_transformations = sum(sum(r.transformations_applied.values()) for r in results.values())

        report.append("## Summary")
        report.append(f"- **Models Processed**: {total_models}")
        report.append(f"- **Successfully Transformed**: {successful_models}")
        report.append(f"- **Success Rate**: {successful_models/total_models*100:.1f}%")
        report.append(f"- **Total Transformations Applied**: {total_transformations}")
        report.append("")

        # Individual model results
        report.append("## Model Transformation Results")
        for model_name, result in results.items():
            status = "✅ PASS" if result.validation_passed else "❌ FAIL"
            report.append(f"### {model_name} - {status}")
            report.append(f"- **Original Rows**: {result.original_rows}")
            report.append(f"- **Transformed Rows**: {result.transformed_rows}")
            report.append(f"- **Transformations Applied**: {sum(result.transformations_applied.values())}")

            if result.transformations_applied:
                report.append("- **Transformation Details**:")
                for transform_type, count in result.transformations_applied.items():
                    if count > 0:
                        report.append(f"  - {transform_type.replace('_', ' ').title()}: {count}")

            if result.validation_errors:
                report.append("- **Errors**:")
                for error in result.validation_errors:
                    report.append(f"  - {error}")

            if result.validation_warnings:
                report.append("- **Warnings**:")
                for warning in result.validation_warnings:
                    report.append(f"  - {warning}")

            if result.output_path:
                report.append(f"- **Output File**: {result.output_path}")

            report.append("")

        # Overall assessment
        report.append("## Overall Assessment")

        if successful_models == total_models:
            report.append("🎉 **All models successfully transformed!**")
            report.append("The transformation engine has successfully converted all models")
            report.append("to standardized format according to the defined templates and rules.")
        else:
            failed_models = [name for name, result in results.items() if not result.validation_passed]
            report.append(f"⚠️ **{total_models - successful_models} model(s) failed transformation**")
            report.append(f"Failed models: {', '.join(failed_models)}")
            report.append("Review the errors above and adjust the templates or transformation rules as needed.")

        # Transformation statistics
        if total_transformations > 0:
            report.append("")
            report.append("## Transformation Statistics")
            all_transform_types = set()
            for result in results.values():
                all_transform_types.update(result.transformations_applied.keys())

            for transform_type in sorted(all_transform_types):
                total_count = sum(r.transformations_applied.get(transform_type, 0) for r in results.values())
                if total_count > 0:
                    report.append(f"- **{transform_type.replace('_', ' ').title()}**: {total_count}")

        return "\n".join(report)

    def save_report(self, report: str, output_path: str = "docs/model_transformation.md"):
        """Save the transformation report."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Transformation report saved to: {output_file}")

def main():
    """Main execution function."""
    engine = ModelTransformationEngine()

    try:
        logger.info("Starting model transformation process...")
        logger.info(f"Models to transform: {', '.join(engine.models)}")
        logger.info("")

        # Transform all models
        results = engine.transform_all_models()

        # Generate and save report
        logger.info("Generating transformation report...")
        report = engine.generate_transformation_report(results)
        engine.save_report(report)

        # Print summary
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_transformations = sum(sum(r.transformations_applied.values()) for r in results.values())

        logger.info("")
        logger.info("Transformation Summary:")
        logger.info(f"- Models processed: {len(results)}")
        logger.info(f"- Successfully transformed: {successful_models}")
        logger.info(f"- Failed: {len(results) - successful_models}")
        logger.info(f"- Total transformations applied: {total_transformations}")
        logger.info(".1f")

        if successful_models == len(results):
            logger.info("🎉 All models successfully transformed!")
        else:
            logger.info("⚠️ Some transformations failed. Check the report for details.")

    except Exception as e:
        logger.error(f"Error during transformation: {e}")
        raise

if __name__ == "__main__":
    main()
