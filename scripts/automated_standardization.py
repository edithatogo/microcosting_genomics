#!/usr/bin/env python3
"""
Automated Standardization Engine

This script implements automated standardization of genomic testing models
using the rules defined in the standard_categories.yaml configuration file.

The engine:
1. Loads original model data
2. Applies standardization mappings
3. Validates standardized structure
4. Generates standardized model files
5. Runs validation checks
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import yaml
from dataclasses import dataclass
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StandardizationResult:
    """Container for standardization results."""
    model_name: str
    original_rows: int
    standardized_rows: int
    categories_mapped: int
    subcategories_mapped: int
    validation_passed: bool
    validation_errors: List[str]
    validation_warnings: List[str]

@dataclass
class StandardizedModel:
    """Container for a standardized model."""
    name: str
    dataframe: pd.DataFrame
    metadata: Dict[str, Any]

class AutomatedStandardizationEngine:
    """Engine for automated model standardization."""

    def __init__(self, config_path: str = "config/standard_categories.yaml"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.models = [
            "Panel",
            "WES (P)",
            "WES (T)",
            "WGS (P)",
            "WGS (T)"
        ]

    def load_config(self) -> Dict:
        """Load the standardization configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_original_model(self, model_name: str) -> Optional[pd.DataFrame]:
        """Load original model data from the detailed table."""
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

    def apply_category_mappings(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Apply category standardization mappings."""
        if df is None or df.empty:
            return df, 0

        df_copy = df.copy()
        mappings_applied = 0

        category_mappings = self.config.get('standardization_mappings', {}).get('category_mappings', {})

        if 'Category' in df_copy.columns and category_mappings:
            # Apply mappings
            df_copy['Category'] = df_copy['Category'].map(
                lambda x: category_mappings.get(x, x) if pd.notna(x) else x
            )

            # Count how many mappings were applied
            original_categories = df['Category'].fillna('')
            mapped_categories = df_copy['Category'].fillna('')
            mappings_applied = sum(1 for orig, mapped in zip(original_categories, mapped_categories)
                                 if orig != mapped and orig in category_mappings)

        return df_copy, mappings_applied

    def apply_subcategory_mappings(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Apply subcategory standardization mappings."""
        if df is None or df.empty:
            return df, 0

        df_copy = df.copy()
        mappings_applied = 0

        subcategory_mappings = self.config.get('standardization_mappings', {}).get('subcategory_mappings', {})

        if 'Sub-Category' in df_copy.columns and subcategory_mappings:
            # Apply mappings
            df_copy['Sub-Category'] = df_copy['Sub-Category'].map(
                lambda x: subcategory_mappings.get(x, x) if pd.notna(x) else x
            )

            # Count how many mappings were applied
            original_subcats = df['Sub-Category'].fillna('')
            mapped_subcats = df_copy['Sub-Category'].fillna('')
            mappings_applied = sum(1 for orig, mapped in zip(original_subcats, mapped_subcats)
                                 if orig != mapped and orig in subcategory_mappings)

        return df_copy, mappings_applied

    def add_model_specific_subcategories(self, df: pd.DataFrame, model_name: str) -> pd.DataFrame:
        """Add model-specific subcategories if applicable."""
        if df is None or df.empty:
            return df

        df_copy = df.copy()
        model_specific = self.config.get('model_specific_subcategories', {}).get(model_name, {})

        if model_specific:
            logger.info(f"Adding model-specific subcategories for {model_name}: {model_specific}")

            # For now, we'll log this but not modify the data structure
            # In a full implementation, this would add missing subcategories
            # based on the model-specific configuration

        return df_copy

    def validate_standardized_model(self, df: pd.DataFrame, model_name: str) -> Tuple[bool, List[str], List[str]]:
        """Validate that the standardized model meets requirements."""
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("Model data is empty")
            return False, errors, warnings

        # Check required categories
        required_categories = self.config.get('validation_rules', {}).get('required_categories', [])
        present_categories = set(df['Category'].dropna().unique())

        missing_categories = set(required_categories) - present_categories
        if missing_categories:
            errors.append(f"Missing required categories: {', '.join(missing_categories)}")

        # Check minimum subcategories
        min_subcategories = self.config.get('validation_rules', {}).get('minimum_subcategories', {})
        for category, min_count in min_subcategories.items():
            if category in present_categories:
                subcats = df[df['Category'] == category]['Sub-Category'].dropna().unique()
                if len(subcats) < min_count:
                    warnings.append(f"Category '{category}' has {len(subcats)} subcategories, minimum is {min_count}")

        # Check for unmapped categories/subcategories
        standard_categories = set(self.config.get('standard_categories', []))
        non_standard_categories = present_categories - standard_categories
        if non_standard_categories:
            warnings.append(f"Non-standard categories present: {', '.join(non_standard_categories)}")

        # Check data integrity
        if len(df) == 0:
            errors.append("No data rows found")
        elif len(df.columns) < 3:
            warnings.append(f"Model has few columns ({len(df.columns)}), may be incomplete")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def standardize_model(self, model_name: str) -> StandardizationResult:
        """Standardize a single model."""
        logger.info(f"Starting standardization of {model_name}")

        # Load original data
        original_df = self.load_original_model(model_name)
        if original_df is None:
            return StandardizationResult(
                model_name=model_name,
                original_rows=0,
                standardized_rows=0,
                categories_mapped=0,
                subcategories_mapped=0,
                validation_passed=False,
                validation_errors=["Could not load original model data"],
                validation_warnings=[]
            )

        original_rows = len(original_df)

        # Apply category mappings
        df_step1, cat_mappings = self.apply_category_mappings(original_df)

        # Apply subcategory mappings
        df_step2, subcat_mappings = self.apply_subcategory_mappings(df_step1)

        # Add model-specific subcategories
        standardized_df = self.add_model_specific_subcategories(df_step2, model_name)

        # Validate the standardized model
        is_valid, errors, warnings = self.validate_standardized_model(standardized_df, model_name)

        # Save the standardized model
        if standardized_df is not None and not standardized_df.empty:
            self.save_standardized_model(model_name, standardized_df)

        result = StandardizationResult(
            model_name=model_name,
            original_rows=original_rows,
            standardized_rows=len(standardized_df) if standardized_df is not None else 0,
            categories_mapped=cat_mappings,
            subcategories_mapped=subcat_mappings,
            validation_passed=is_valid,
            validation_errors=errors,
            validation_warnings=warnings
        )

        logger.info(f"Completed standardization of {model_name}: {result.standardized_rows} rows, {cat_mappings + subcat_mappings} mappings applied")
        return result

    def standardize_all_models(self) -> Dict[str, StandardizationResult]:
        """Standardize all models."""
        results = {}

        for model_name in self.models:
            try:
                result = self.standardize_model(model_name)
                results[model_name] = result

                status = "✅" if result.validation_passed else "❌"
                logger.info(f"{status} Standardized {model_name}")

                if result.validation_errors:
                    logger.error(f"  Errors: {', '.join(result.validation_errors)}")
                if result.validation_warnings:
                    logger.warning(f"  Warnings: {', '.join(result.validation_warnings)}")

            except Exception as e:
                logger.error(f"Failed to standardize {model_name}: {e}")
                results[model_name] = StandardizationResult(
                    model_name=model_name,
                    original_rows=0,
                    standardized_rows=0,
                    categories_mapped=0,
                    subcategories_mapped=0,
                    validation_passed=False,
                    validation_errors=[str(e)],
                    validation_warnings=[]
                )

        return results

    def save_standardized_model(self, model_name: str, df: pd.DataFrame, output_dir: str = "data/standardized"):
        """Save a standardized model to file."""
        if df is None or df.empty:
            logger.warning(f"Cannot save empty model: {model_name}")
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}_standardized.csv"
        filepath = output_path / filename

        df.to_csv(filepath, index=False)
        logger.info(f"Saved standardized model to: {filepath}")

    def generate_standardization_report(self, results: Dict[str, StandardizationResult]) -> str:
        """Generate a comprehensive standardization report."""
        report = []
        report.append("# Automated Standardization Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        total_models = len(results)
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_mappings = sum(r.categories_mapped + r.subcategories_mapped for r in results.values())

        report.append("## Summary")
        report.append(f"- **Models Processed**: {total_models}")
        report.append(f"- **Successfully Standardized**: {successful_models}")
        report.append(f"- **Success Rate**: {successful_models/total_models*100:.1f}%")
        report.append(f"- **Total Mappings Applied**: {total_mappings}")
        report.append("")

        # Individual model results
        report.append("## Model Standardization Results")
        for model_name, result in results.items():
            status = "✅ PASS" if result.validation_passed else "❌ FAIL"
            report.append(f"### {model_name} - {status}")
            report.append(f"- **Original Rows**: {result.original_rows}")
            report.append(f"- **Standardized Rows**: {result.standardized_rows}")
            report.append(f"- **Categories Mapped**: {result.categories_mapped}")
            report.append(f"- **Subcategories Mapped**: {result.subcategories_mapped}")

            if result.validation_errors:
                report.append("- **Errors**:")
                for error in result.validation_errors:
                    report.append(f"  - {error}")

            if result.validation_warnings:
                report.append("- **Warnings**:")
                for warning in result.validation_warnings:
                    report.append(f"  - {warning}")

            report.append("")

        # Overall assessment
        report.append("## Overall Assessment")

        if successful_models == total_models:
            report.append("🎉 **All models successfully standardized!**")
            report.append("The automated standardization process has successfully transformed all models")
            report.append("according to the defined rules and validation criteria.")
        else:
            failed_models = [name for name, result in results.items() if not result.validation_passed]
            report.append(f"⚠️ **{total_models - successful_models} model(s) failed standardization**")
            report.append(f"Failed models: {', '.join(failed_models)}")
            report.append("Review the errors above and adjust the standardization rules as needed.")

        return "\n".join(report)

    def save_report(self, report: str, output_path: str = "docs/automated_standardization.md"):
        """Save the standardization report."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Standardization report saved to: {output_file}")

def main():
    """Main execution function."""
    engine = AutomatedStandardizationEngine()

    try:
        logger.info("Starting automated standardization process...")
        logger.info(f"Models to standardize: {', '.join(engine.models)}")
        logger.info("")

        # Standardize all models
        results = engine.standardize_all_models()

        # Generate and save report
        logger.info("Generating standardization report...")
        report = engine.generate_standardization_report(results)
        engine.save_report(report)

        # Print summary
        successful_models = sum(1 for r in results.values() if r.validation_passed)
        total_mappings = sum(r.categories_mapped + r.subcategories_mapped for r in results.values())

        logger.info("")
        logger.info("Standardization Summary:")
        logger.info(f"- Models processed: {len(results)}")
        logger.info(f"- Successfully standardized: {successful_models}")
        logger.info(f"- Failed: {len(results) - successful_models}")
        logger.info(f"- Total mappings applied: {total_mappings}")
        logger.info(".1f")

        if successful_models == len(results):
            logger.info("🎉 All models successfully standardized!")
        else:
            logger.info("⚠️ Some standardizations failed. Check the report for details.")

    except Exception as e:
        logger.error(f"Error during standardization: {e}")
        raise

if __name__ == "__main__":
    main()
