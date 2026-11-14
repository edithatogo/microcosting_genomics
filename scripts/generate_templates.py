#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Standardized Model Templates.

This script creates standardized templates for genomic testing models
based on the configuration in standard_categories.yaml.

Templates define:
1. Required columns and their order
2. Expected data types
3. Validation rules
4. Default values for optional fields
"""

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass
class ModelTemplate:
    """Template for a standardized model."""

    name: str
    required_columns: list[str]
    optional_columns: list[str]
    column_order: list[str]
    data_types: dict[str, str]
    validation_rules: dict[str, Any]
    default_values: dict[str, Any]


class StandardizedTemplateGenerator:
    """Generates standardized templates for genomic models."""

    def __init__(self, config_path: str = "config/standard_categories.yaml") -> None:
        """Load the standard category configuration for templates."""
        self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self) -> dict:
        """Load the standardization configuration."""
        if not self.config_path.exists():
            message = f"Configuration file not found: {self.config_path}"
            raise FileNotFoundError(message)

        with self.config_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def generate_base_template(self) -> ModelTemplate:
        """Generate the base template structure."""
        # Define standard columns
        required_columns = [
            "Test",
            "Category",
            "Sub-Category",
            "Item",
            "Unit Cost (AUD $/unit)",
            "Units",
            "Total Cost (AUD)",
            "Notes",
        ]

        optional_columns = [
            "Supplier",
            "Catalogue Number",
            "Batch/Lot Number",
            "Expiry Date",
            "Storage Conditions",
            "Quality Control",
            "References",
        ]

        column_order = required_columns + optional_columns

        # Define data types
        data_types = {
            "Test": "string",
            "Category": "category",
            "Sub-Category": "category",
            "Item": "string",
            "Unit Cost (AUD $/unit)": "float64",
            "Units": "float64",
            "Total Cost (AUD)": "float64",
            "Notes": "string",
            "Supplier": "string",
            "Catalogue Number": "string",
            "Batch/Lot Number": "string",
            "Expiry Date": "datetime64[ns]",
            "Storage Conditions": "string",
            "Quality Control": "string",
            "References": "string",
        }

        # Define validation rules
        validation_rules = {
            "required_categories": self.config.get("validation_rules", {}).get(
                "required_categories",
                [],
            ),
            "minimum_subcategories": self.config.get("validation_rules", {}).get(
                "minimum_subcategories",
                {},
            ),
            "standard_categories": self.config.get("standard_categories", []),
            "standard_subcategories": self.config.get("standard_subcategories", {}),
            "model_specific_subcategories": self.config.get(
                "model_specific_subcategories",
                {},
            ),
            "cost_validation": {
                "unit_cost_range": [0, 10000],  # Reasonable cost range in AUD
                "units_range": [0, 10000],  # Reasonable units range
                "total_cost_calculation": "Unit Cost * Units",
            },
            "data_integrity": {
                "no_empty_required_fields": True,
                "consistent_test_name": True,
                "valid_categories_only": True,
            },
        }

        # Define default values
        default_values = {
            "Test": "",
            "Category": "",
            "Sub-Category": "",
            "Item": "",
            "Unit Cost (AUD $/unit)": 0.0,
            "Units": 1.0,
            "Total Cost (AUD)": 0.0,
            "Notes": "",
            "Supplier": "",
            "Catalogue Number": "",
            "Batch/Lot Number": "",
            "Expiry Date": pd.NaT,
            "Storage Conditions": "Room temperature",
            "Quality Control": "",
            "References": "",
        }

        return ModelTemplate(
            name="base_template",
            required_columns=required_columns,
            optional_columns=optional_columns,
            column_order=column_order,
            data_types=data_types,
            validation_rules=validation_rules,
            default_values=default_values,
        )

    def generate_model_specific_template(self, model_name: str) -> ModelTemplate:
        """Generate a model-specific template."""
        base_template = self.generate_base_template()

        # Get model-specific configuration
        model_specific = self.config.get("model_specific_subcategories", {}).get(
            model_name,
            {},
        )

        # Customize validation rules for this model
        model_validation_rules = base_template.validation_rules.copy()
        if model_specific:
            model_validation_rules["model_specific_subcategories"] = model_specific

        # Create model-specific template
        return ModelTemplate(
            name=f"{model_name}_template",
            required_columns=base_template.required_columns,
            optional_columns=base_template.optional_columns,
            column_order=base_template.column_order,
            data_types=base_template.data_types,
            validation_rules=model_validation_rules,
            default_values={**base_template.default_values, "Test": model_name},
        )

    def create_empty_standardized_dataframe(
        self,
        template: ModelTemplate,
        num_rows: int = 0,
    ) -> pd.DataFrame:
        """Create an empty DataFrame following the template structure."""
        # Create empty DataFrame with correct columns
        df = pd.DataFrame(columns=template.column_order)

        # Set data types
        for col, dtype in template.data_types.items():
            if col in df.columns:
                if dtype == "category":
                    df[col] = pd.Categorical(df[col])
                elif dtype == "datetime64[ns]":
                    df[col] = pd.to_datetime(df[col])
                elif dtype == "float64":
                    df[col] = df[col].astype("float64")
                elif dtype == "int64":
                    df[col] = df[col].astype("int64")
                else:
                    df[col] = df[col].astype("string")

        if num_rows > 0:
            return self._default_rows(template, num_rows)

        return df

    def _default_rows(self, template: ModelTemplate, num_rows: int) -> pd.DataFrame:
        default_row = template.default_values.copy()
        default_rows = [default_row] * num_rows
        df = pd.DataFrame(default_rows, columns=template.column_order)

        # Apply data types to default data
        for col, dtype in template.data_types.items():
            if col in df.columns:
                if dtype == "category":
                    df[col] = pd.Categorical(df[col])
                elif dtype == "datetime64[ns]":
                    df[col] = pd.to_datetime(df[col])
                elif dtype in ["float64", "int64"]:
                    try:
                        df[col] = df[col].astype("float64")
                    except ValueError, TypeError:
                        df[col] = pd.Series([0.0] * len(df), dtype="float64")

        return df

    def generate_category_examples(
        self,
        _template: ModelTemplate,
    ) -> dict[str, list[dict]]:
        """Generate example data for each category."""
        examples = {}

        standard_subcategories = self.config.get("standard_subcategories", {})

        for category in self.config.get("standard_categories", []):
            examples[category] = []

            subcategories = standard_subcategories.get(category, [])
            for subcategory in subcategories:
                example = {
                    "Test": "Example Model",
                    "Category": category,
                    "Sub-Category": subcategory,
                    "Item": f"Example {subcategory} Item",
                    "Unit Cost (AUD $/unit)": 100.0,
                    "Units": 1.0,
                    "Total Cost (AUD)": 100.0,
                    "Notes": f"Example entry for {category} - {subcategory}",
                }
                examples[category].append(example)

        return examples

    def save_template_to_json(self, template: ModelTemplate, output_path: str) -> None:
        """Save a template to JSON format."""
        template_dict = {
            "name": template.name,
            "required_columns": template.required_columns,
            "optional_columns": template.optional_columns,
            "column_order": template.column_order,
            "data_types": template.data_types,
            "validation_rules": template.validation_rules,
            "default_values": {
                k: str(v) if pd.isna(v) else v
                for k, v in template.default_values.items()
            },
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with Path(output_file).open("w", encoding="utf-8") as f:
            json.dump(template_dict, f, indent=2, default=str)

    def save_template_examples(
        self,
        examples: dict[str, list[dict]],
        output_path: str,
    ) -> None:
        """Save example data to CSV format."""
        all_examples = []
        for category_examples in examples.values():
            all_examples.extend(category_examples)

        if all_examples:
            df = pd.DataFrame(all_examples)
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_file, index=False)

    def generate_template_documentation(
        self,
        templates: dict[str, ModelTemplate],
    ) -> str:
        """Generate documentation for the templates."""
        doc = []
        doc.append("# Standardized Model Templates")
        doc.append(
            "Generated: "
            f"{datetime.now(UTC).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        )
        doc.append("")

        doc.append("## Overview")
        doc.append(
            "This document describes the standardized templates for genomic"
            " testing models.",
        )
        doc.append(
            "Templates define the structure, validation rules, and data "
            "types for consistent model formatting.",
        )
        doc.append("")

        for template_name, template in templates.items():
            doc.append(f"## {template_name.replace('_', ' ').title()}")
            doc.append("")

            doc.append("### Required Columns")
            for col in template.required_columns:
                dtype = template.data_types.get(col, "string")
                doc.append(f"- **{col}** ({dtype})")
            doc.append("")

            doc.append("### Optional Columns")
            for col in template.optional_columns:
                dtype = template.data_types.get(col, "string")
                doc.append(f"- **{col}** ({dtype})")
            doc.append("")

            doc.append("### Validation Rules")
            rules = template.validation_rules
            if "required_categories" in rules:
                doc.append(
                    "- **Required Categories**: "
                    f"{', '.join(rules['required_categories'])}",
                )
            if "minimum_subcategories" in rules:
                for cat, min_count in rules["minimum_subcategories"].items():
                    doc.append(f"- **Minimum {cat} Subcategories**: {min_count}")
            doc.append("")

        doc.append("## Usage")
        doc.append("1. Use the base template for general model creation")
        doc.append("2. Use model-specific templates for specialized requirements")
        doc.append("3. Follow the column order and data types specified")
        doc.append("4. Ensure all validation rules are met")
        doc.append("5. Use default values for optional fields when appropriate")
        doc.append("")

        return "\n".join(doc)

    def generate_all_templates(self) -> dict[str, ModelTemplate]:
        """Generate all templates."""
        templates = {}

        # Base template
        templates["base"] = self.generate_base_template()

        # Model-specific templates
        models = ["Panel", "WES (P)", "WES (T)", "WGS", "WGS (T)"]
        for model in models:
            templates[
                model.lower().replace(" ", "_").replace("(", "").replace(")", "")
            ] = self.generate_model_specific_template(model)

        return templates


def main() -> None:
    """Generate the standard model templates."""
    generator = StandardizedTemplateGenerator()

    sys.stdout.write("Generating standardized model templates..." + "\n")

    # Generate all templates
    templates = generator.generate_all_templates()

    # Save templates
    templates_dir = Path("config/templates")
    templates_dir.mkdir(parents=True, exist_ok=True)

    for template_name, template in templates.items():
        json_path = str(templates_dir / f"{template_name}_template.json")
        generator.save_template_to_json(template, json_path)
        sys.stdout.write(f"Saved template: {json_path}" + "\n")

    # Generate and save examples
    base_template = templates["base"]
    examples = generator.generate_category_examples(base_template)
    examples_path = str(templates_dir / "template_examples.csv")
    generator.save_template_examples(examples, examples_path)
    sys.stdout.write(f"Saved examples: {examples_path}" + "\n")

    # Generate documentation
    doc_path = "docs/standardized_templates.md"
    documentation = generator.generate_template_documentation(templates)
    Path(doc_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(doc_path).open("w", encoding="utf-8") as f:
        f.write(documentation)
    sys.stdout.write(f"Saved documentation: {doc_path}" + "\n")

    sys.stdout.write(f"\nGenerated {len(templates)} templates successfully!" + "\n")
    sys.stdout.write("Templates include:" + "\n")
    for name in templates:
        sys.stdout.write(f"  - {name}" + "\n")


if __name__ == "__main__":
    main()
