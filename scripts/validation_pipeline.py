#!/usr/bin/env python3
"""
Ongoing Validation Pipeline

This script implements an automated validation pipeline that continuously
monitors standardized models to ensure they maintain consistency and accuracy.

The pipeline:
1. Validates standardized models against templates
2. Checks for data integrity issues
3. Monitors for deviations from standards
4. Generates validation reports and alerts
5. Tracks validation history over time
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
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ValidationIssue:
    """Container for validation issues."""
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'structure', 'data', 'consistency', 'integrity'
    message: str
    field: Optional[str] = None
    row_index: Optional[int] = None
    suggested_fix: Optional[str] = None

@dataclass
class ModelValidationResult:
    """Container for model validation results."""
    model_name: str
    timestamp: datetime
    is_valid: bool
    total_issues: int
    errors: int
    warnings: int
    info: int
    issues: List[ValidationIssue]
    checksum: str
    row_count: int
    column_count: int

@dataclass
class ValidationPipelineResult:
    """Container for pipeline validation results."""
    timestamp: datetime
    models_processed: int
    models_valid: int
    total_issues: int
    results: Dict[str, ModelValidationResult]
    summary: Dict[str, Any]

class OngoingValidationPipeline:
    """Automated validation pipeline for standardized models."""

    def __init__(self, config_path: str = "config/standard_categories.yaml",
                 templates_dir: str = "config/templates",
                 models_dir: str = "data/standardized"):
        self.config_path = Path(config_path)
        self.templates_dir = Path(templates_dir)
        self.models_dir = Path(models_dir)
        self.config = self.load_config()
        self.templates = self.load_templates()

    def load_config(self) -> Dict:
        """Load the standardization configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_templates(self) -> Dict[str, Any]:
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

                template = {
                    'name': template_data['name'],
                    'required_columns': template_data['required_columns'],
                    'optional_columns': template_data['optional_columns'],
                    'column_order': template_data['column_order'],
                    'data_types': template_data['data_types'],
                    'validation_rules': template_data['validation_rules'],
                    'default_values': default_values
                }

                template_key = template_data['name'].replace('_template', '')
                templates[template_key] = template

            except Exception as e:
                logger.error(f"Error loading template {json_file}: {e}")

        return templates

    def get_template_for_model(self, model_name: str) -> Optional[Dict]:
        """Get the appropriate template for a model."""
        # Try model-specific template first
        model_key = model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
        if model_key in self.templates:
            return self.templates[model_key]

        # Fall back to base template
        if 'base' in self.templates:
            return self.templates['base']

        return None

    def load_standardized_model(self, model_name: str) -> Optional[pd.DataFrame]:
        """Load a standardized model from file."""
        filename = f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}_standardized.csv"
        filepath = self.models_dir / filename

        if not filepath.exists():
            return None

        try:
            df = pd.read_csv(filepath)
            return df
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return None

    def calculate_checksum(self, df: pd.DataFrame) -> str:
        """Calculate a checksum for the dataframe to detect changes."""
        # Convert to string representation for hashing
        df_str = df.to_csv(index=False)
        return hashlib.md5(df_str.encode()).hexdigest()

    def validate_model_structure(self, df: pd.DataFrame, template: Dict, model_name: str) -> List[ValidationIssue]:
        """Validate model structure against template."""
        issues = []

        # Check required columns
        required_cols = set(template['required_columns'])
        present_cols = set(df.columns)
        missing_cols = required_cols - present_cols

        if missing_cols:
            for col in missing_cols:
                issues.append(ValidationIssue(
                    severity='error',
                    category='structure',
                    message=f"Missing required column: {col}",
                    field=col,
                    suggested_fix="Add the missing column with appropriate default values"
                ))

        # Check column order (warning only)
        expected_order = template['column_order']
        actual_order = [col for col in expected_order if col in df.columns]

        if actual_order != expected_order[:len(actual_order)]:
            issues.append(ValidationIssue(
                severity='warning',
                category='structure',
                message="Column order does not match template",
                suggested_fix="Consider reordering columns to match template"
            ))

        # Check for extra columns
        extra_cols = present_cols - set(template['column_order'])
        if extra_cols:
            for col in extra_cols:
                issues.append(ValidationIssue(
                    severity='info',
                    category='structure',
                    message=f"Extra column present: {col}",
                    field=col,
                    suggested_fix="Review if this column should be included in the template"
                ))

        return issues

    def validate_data_integrity(self, df: pd.DataFrame, template: Dict, model_name: str) -> List[ValidationIssue]:
        """Validate data integrity."""
        issues = []

        # Check for null values in required columns
        for col in template['required_columns']:
            if col in df.columns:
                null_count = df[col].isna().sum()
                # Also count empty strings as missing values
                empty_count = (df[col] == '').sum()
                total_missing = null_count + empty_count

                if total_missing > 0:
                    severity = 'error' if total_missing > len(df) * 0.1 else 'warning'
                    issues.append(ValidationIssue(
                        severity=severity,
                        category='data',
                        message=f"Column '{col}' has {total_missing} missing/empty values ({total_missing/len(df)*100:.1f}%)",
                        field=col,
                        suggested_fix="Fill missing values with appropriate defaults or investigate data source"
                    ))

        # Check data types
        for col, expected_dtype in template['data_types'].items():
            if col in df.columns:
                try:
                    if expected_dtype == 'float64':
                        non_numeric = pd.to_numeric(df[col], errors='coerce').isna().sum() - df[col].isna().sum()
                        if non_numeric > 0:
                            issues.append(ValidationIssue(
                                severity='warning',
                                category='data',
                                message=f"Column '{col}' has {non_numeric} non-numeric values",
                                field=col,
                                suggested_fix="Convert non-numeric values to numbers or update data type"
                            ))
                    elif expected_dtype == 'int64':
                        # Check if values are whole numbers
                        numeric_series = pd.to_numeric(df[col], errors='coerce')
                        non_integer = ((numeric_series % 1) != 0).sum()
                        if non_integer > 0:
                            issues.append(ValidationIssue(
                                severity='info',
                                category='data',
                                message=f"Column '{col}' has {non_integer} non-integer values",
                                field=col,
                                suggested_fix="Review if integer type is appropriate for this column"
                            ))
                except Exception as e:
                    issues.append(ValidationIssue(
                        severity='warning',
                        category='data',
                        message=f"Error validating data type for column '{col}': {e}",
                        field=col
                    ))

        return issues

    def validate_consistency(self, df: pd.DataFrame, template: Dict, model_name: str) -> List[ValidationIssue]:
        """Validate data consistency."""
        issues = []

        # Check required categories
        required_categories = template['validation_rules'].get('required_categories', [])
        if 'Category' in df.columns and required_categories:
            # Filter out null and empty values
            category_values = df['Category'].fillna('').replace('', pd.NA).dropna()
            present_categories = set(category_values.unique())
            missing_categories = set(required_categories) - present_categories

            if missing_categories:
                issues.append(ValidationIssue(
                    severity='error',
                    category='consistency',
                    message=f"Missing required categories: {', '.join(missing_categories)}",
                    field='Category',
                    suggested_fix="Add missing categories or update model-specific requirements"
                ))

        # Check minimum subcategories
        min_subcategories = template['validation_rules'].get('minimum_subcategories', {})
        if 'Category' in df.columns and 'Sub-Category' in df.columns:
            for category, min_count in min_subcategories.items():
                category_data = df[df['Category'] == category]
                unique_subcats = category_data['Sub-Category'].dropna().unique()

                if len(unique_subcats) < min_count:
                    issues.append(ValidationIssue(
                        severity='warning',
                        category='consistency',
                        message=f"Category '{category}' has {len(unique_subcats)} subcategories, minimum is {min_count}",
                        field='Sub-Category',
                        suggested_fix="Add more subcategories or reduce minimum requirement"
                    ))

        # Check for standard categories only
        standard_categories = set(template['validation_rules'].get('standard_categories', []))
        if 'Category' in df.columns and standard_categories:
            # Filter out null and empty values
            category_values = df['Category'].fillna('').replace('', pd.NA).dropna()
            present_categories = set(category_values.unique())
            non_standard = present_categories - standard_categories

            if non_standard:
                issues.append(ValidationIssue(
                    severity='warning',
                    category='consistency',
                    message=f"Non-standard categories present: {', '.join(non_standard)}",
                    field='Category',
                    suggested_fix="Map non-standard categories to standard ones"
                ))

        return issues

    def validate_cost_calculations(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Validate cost calculations where possible."""
        issues = []

        # Check if cost columns exist and have data
        cost_cols = ['Unit Cost (AUD $/unit)', 'Units', 'Total Cost (AUD)']
        available_cost_cols = [col for col in cost_cols if col in df.columns]

        if len(available_cost_cols) >= 3:
            try:
                # Convert to numeric for validation
                unit_cost = pd.to_numeric(df['Unit Cost (AUD $/unit)'], errors='coerce')
                units = pd.to_numeric(df['Units'], errors='coerce')
                total_cost = pd.to_numeric(df['Total Cost (AUD)'], errors='coerce')

                # Calculate expected total
                expected_total = unit_cost * units

                # Find significant discrepancies
                valid_mask = (~pd.isna(expected_total)) & (~pd.isna(total_cost)) & (expected_total != 0)
                if valid_mask.any():
                    diff = np.abs((total_cost[valid_mask] - expected_total[valid_mask]) / expected_total[valid_mask])
                    significant_diff = (diff > 0.01).sum()  # More than 1% difference

                    if significant_diff > 0:
                        issues.append(ValidationIssue(
                            severity='warning',
                            category='data',
                            message=f"{significant_diff} rows have cost calculation discrepancies >1%",
                            suggested_fix="Review cost calculations and update formulas if needed"
                        ))

            except Exception as e:
                issues.append(ValidationIssue(
                    severity='info',
                    category='data',
                    message=f"Could not validate cost calculations: {e}",
                    suggested_fix="Check data types and formulas in cost columns"
                ))

        return issues

    def validate_model(self, model_name: str) -> ModelValidationResult:
        """Validate a single standardized model."""
        logger.info(f"Validating standardized model: {model_name}")

        # Load model data
        df = self.load_standardized_model(model_name)
        if df is None:
            return ModelValidationResult(
                model_name=model_name,
                timestamp=datetime.now(),
                is_valid=False,
                total_issues=1,
                errors=1,
                warnings=0,
                info=0,
                issues=[ValidationIssue(
                    severity='error',
                    category='structure',
                    message="Could not load standardized model file",
                    suggested_fix="Ensure the model has been properly standardized and saved"
                )],
                checksum="",
                row_count=0,
                column_count=0
            )

        # Get appropriate template
        template = self.get_template_for_model(model_name)
        if template is None:
            return ModelValidationResult(
                model_name=model_name,
                timestamp=datetime.now(),
                is_valid=False,
                total_issues=1,
                errors=1,
                warnings=0,
                info=0,
                issues=[ValidationIssue(
                    severity='error',
                    category='structure',
                    message="No validation template found for model",
                    suggested_fix="Create or update the model template"
                )],
                checksum=self.calculate_checksum(df),
                row_count=len(df),
                column_count=len(df.columns)
            )

        # Run all validations
        issues = []
        issues.extend(self.validate_model_structure(df, template, model_name))
        issues.extend(self.validate_data_integrity(df, template, model_name))
        issues.extend(self.validate_consistency(df, template, model_name))
        issues.extend(self.validate_cost_calculations(df))

        # Calculate issue counts
        errors = sum(1 for issue in issues if issue.severity == 'error')
        warnings = sum(1 for issue in issues if issue.severity == 'warning')
        info = sum(1 for issue in issues if issue.severity == 'info')

        is_valid = errors == 0

        result = ModelValidationResult(
            model_name=model_name,
            timestamp=datetime.now(),
            is_valid=is_valid,
            total_issues=len(issues),
            errors=errors,
            warnings=warnings,
            info=info,
            issues=issues,
            checksum=self.calculate_checksum(df),
            row_count=len(df),
            column_count=len(df.columns)
        )

        logger.info(f"Validation complete for {model_name}: {len(issues)} issues ({errors} errors, {warnings} warnings, {info} info)")
        return result

    def validate_all_models(self) -> ValidationPipelineResult:
        """Validate all standardized models."""
        results = {}
        models_to_check = ["Panel", "WES (P)", "WES (T)", "WGS (P)", "WGS (T)"]

        for model_name in models_to_check:
            try:
                result = self.validate_model(model_name)
                results[model_name] = result

                status = "✅" if result.is_valid else "❌"
                logger.info(f"{status} Validated {model_name}")

                if result.errors > 0:
                    logger.error(f"  Errors: {result.errors}")
                if result.warnings > 0:
                    logger.warning(f"  Warnings: {result.warnings}")

            except Exception as e:
                logger.error(f"Failed to validate {model_name}: {e}")
                results[model_name] = ModelValidationResult(
                    model_name=model_name,
                    timestamp=datetime.now(),
                    is_valid=False,
                    total_issues=1,
                    errors=1,
                    warnings=0,
                    info=0,
                    issues=[ValidationIssue(
                        severity='error',
                        category='structure',
                        message=f"Validation failed: {e}"
                    )],
                    checksum="",
                    row_count=0,
                    column_count=0
                )

        # Calculate summary
        models_processed = len(results)
        models_valid = sum(1 for r in results.values() if r.is_valid)
        total_issues = sum(r.total_issues for r in results.values())

        summary = {
            'models_processed': models_processed,
            'models_valid': models_valid,
            'validation_rate': models_valid / models_processed * 100 if models_processed > 0 else 0,
            'total_issues': total_issues,
            'total_errors': sum(r.errors for r in results.values()),
            'total_warnings': sum(r.warnings for r in results.values()),
            'total_info': sum(r.info for r in results.values())
        }

        return ValidationPipelineResult(
            timestamp=datetime.now(),
            models_processed=models_processed,
            models_valid=models_valid,
            total_issues=total_issues,
            results=results,
            summary=summary
        )

    def generate_validation_report(self, pipeline_result: ValidationPipelineResult) -> str:
        """Generate a comprehensive validation report."""
        report = []
        report.append("# Ongoing Validation Pipeline Report")
        report.append(f"Generated: {pipeline_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        summary = pipeline_result.summary
        report.append("## Summary")
        report.append(f"- **Models Validated**: {summary['models_processed']}")
        report.append(f"- **Models Passing**: {summary['models_valid']}")
        report.append(f"- **Validation Rate**: {summary['validation_rate']:.1f}%")
        report.append(f"- **Total Issues**: {summary['total_issues']}")
        report.append(f"  - Errors: {summary['total_errors']}")
        report.append(f"  - Warnings: {summary['total_warnings']}")
        report.append(f"  - Info: {summary['total_info']}")
        report.append("")

        # Individual model results
        report.append("## Model Validation Results")
        for model_name, result in pipeline_result.results.items():
            status = "✅ PASS" if result.is_valid else "❌ FAIL"
            report.append(f"### {model_name} - {status}")
            report.append(f"- **Rows**: {result.row_count}")
            report.append(f"- **Columns**: {result.column_count}")
            report.append(f"- **Total Issues**: {result.total_issues}")
            report.append(f"- **Errors**: {result.errors}")
            report.append(f"- **Warnings**: {result.warnings}")
            report.append(f"- **Info**: {result.info}")
            report.append(f"- **Checksum**: {result.checksum[:8]}...")

            if result.issues:
                report.append("- **Issues**:")
                for issue in result.issues[:10]:  # Limit to first 10 issues
                    severity_icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(issue.severity, '❓')
                    report.append(f"  - {severity_icon} **{issue.category.title()}**: {issue.message}")
                    if issue.suggested_fix:
                        report.append(f"    - *Suggestion*: {issue.suggested_fix}")

                if len(result.issues) > 10:
                    report.append(f"  - ... and {len(result.issues) - 10} more issues")

            report.append("")

        # Recommendations
        report.append("## Recommendations")

        failed_models = [name for name, result in pipeline_result.results.items() if not result.is_valid]
        if failed_models:
            report.append("### Failed Models")
            for model_name in failed_models:
                result = pipeline_result.results[model_name]
                critical_errors = [issue for issue in result.issues if issue.severity == 'error']
                report.append(f"- **{model_name}**: {len(critical_errors)} critical errors")
                for error in critical_errors[:3]:  # Show first 3 errors
                    report.append(f"  - {error.message}")
            report.append("")

        models_with_warnings = [name for name, result in pipeline_result.results.items()
                              if result.warnings > 0]
        if models_with_warnings:
            report.append("### Models with Warnings")
            for model_name in models_with_warnings:
                result = pipeline_result.results[model_name]
                report.append(f"- **{model_name}**: {result.warnings} warnings")
            report.append("")

        # Overall assessment
        if summary['validation_rate'] == 100.0:
            report.append("### Overall Assessment")
            report.append("🎉 **All models passed validation!**")
            report.append("The standardized models are maintaining consistency and data integrity.")
        elif summary['validation_rate'] >= 80.0:
            report.append("### Overall Assessment")
            report.append("✅ **Most models passed validation**")
            report.append("Review the failed models and address any critical issues.")
        else:
            report.append("### Overall Assessment")
            report.append("⚠️ **Multiple models failed validation**")
            report.append("Immediate attention required to fix critical issues.")

        return "\n".join(report)

    def save_validation_report(self, report: str, output_path: str = "docs/validation_pipeline.md"):
        """Save the validation report."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Validation report saved to: {output_file}")

    def save_validation_history(self, pipeline_result: ValidationPipelineResult,
                               history_path: str = "data/validation_history.json"):
        """Save validation results to history file."""
        history_file = Path(history_path)
        history_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing history
        history = []
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load validation history: {e}")

        # Add current results
        history_entry = {
            'timestamp': pipeline_result.timestamp.isoformat(),
            'summary': pipeline_result.summary,
            'models': {
                name: {
                    'is_valid': result.is_valid,
                    'total_issues': result.total_issues,
                    'errors': result.errors,
                    'warnings': result.warnings,
                    'info': result.info,
                    'checksum': result.checksum,
                    'row_count': result.row_count,
                    'column_count': result.column_count
                }
                for name, result in pipeline_result.results.items()
            }
        }

        history.append(history_entry)

        # Keep only last 50 entries to prevent file from growing too large
        if len(history) > 50:
            history = history[-50:]

        # Save updated history
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, default=str)

        logger.info(f"Validation history updated: {len(history)} entries")

def main():
    """Main execution function."""
    pipeline = OngoingValidationPipeline()

    try:
        logger.info("Starting ongoing validation pipeline...")
        logger.info("Validating all standardized models...")

        # Run validation pipeline
        pipeline_result = pipeline.validate_all_models()

        # Generate and save report
        logger.info("Generating validation report...")
        report = pipeline.generate_validation_report(pipeline_result)
        pipeline.save_validation_report(report)

        # Save validation history
        pipeline.save_validation_history(pipeline_result)

        # Print summary
        summary = pipeline_result.summary
        logger.info("")
        logger.info("Validation Pipeline Summary:")
        logger.info(f"- Models validated: {summary['models_processed']}")
        logger.info(f"- Models passing: {summary['models_valid']}")
        logger.info(f"- Validation rate: {summary['validation_rate']:.1f}%")
        logger.info(f"- Total issues: {summary['total_issues']}")
        logger.info(f"  - Errors: {summary['total_errors']}")
        logger.info(f"  - Warnings: {summary['total_warnings']}")
        logger.info(f"  - Info: {summary['total_info']}")

        if summary['validation_rate'] == 100.0:
            logger.info("🎉 All models passed validation!")
        elif summary['validation_rate'] >= 80.0:
            logger.info("✅ Most models passed validation")
        else:
            logger.info("⚠️ Multiple validation failures detected")

    except Exception as e:
        logger.error(f"Error in validation pipeline: {e}")
        raise

if __name__ == "__main__":
    main()
