#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Validate Corrected Data Integrity.

This script validates that the corrected data extraction preserved meaningful
numeric values and compares them with the original Excel data.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

MINIMUM_NONZERO_RATE = 0.1
MINIMUM_NUMERIC_RATE = 0.5

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataIntegrityValidator:
    """Validates data integrity of corrected models."""

    def __init__(self, excel_path: str, corrected_dir: str = "data/corrected") -> None:
        """Set the reference workbook and corrected table directory."""
        self.excel_path = Path(excel_path)
        self.corrected_dir = Path(corrected_dir)

    def load_corrected_model(self, model_name: str) -> pd.DataFrame | None:
        """Load a corrected model."""
        filename = (
            f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}"
            "_corrected.csv"
        )
        filepath = self.corrected_dir / filename

        if not filepath.exists():
            logger.warning("Corrected model not found: %s", filepath)
            return None

        try:
            df = pd.read_csv(filepath)
            logger.info("Loaded corrected model '%s': %s", model_name, df.shape)
        except Exception:
            logger.exception("Error loading corrected model %s", model_name)
            return None
        else:
            return df

    def analyze_numeric_content(self, df: pd.DataFrame, model_name: str) -> dict:
        """Analyze the numeric content of a DataFrame."""
        analysis = {
            "model": model_name,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": 0,
            "text_columns": 0,
            "empty_columns": 0,
            "total_numeric_values": 0,
            "non_zero_numeric_values": 0,
            "numeric_value_ranges": {},
            "sample_numeric_values": {},
        }

        for col in df.columns:
            col_data = df[col]

            # Check if column is empty
            non_null_count = col_data.notna().sum()
            if non_null_count == 0:
                analysis["empty_columns"] += 1
                continue

            # Try to convert to numeric
            numeric_series = pd.to_numeric(col_data, errors="coerce")
            numeric_count = numeric_series.notna().sum()

            if numeric_count > non_null_count * 0.8:  # 80% of values are numeric
                analysis["numeric_columns"] += 1
                analysis["total_numeric_values"] += numeric_count
                analysis["non_zero_numeric_values"] += (numeric_series != 0).sum()

                # Store range and sample values
                clean_numeric = numeric_series.dropna()
                if len(clean_numeric) > 0:
                    analysis["numeric_value_ranges"][str(col)] = {
                        "min": float(clean_numeric.min()),
                        "max": float(clean_numeric.max()),
                        "mean": float(clean_numeric.mean()),
                        "non_zero_count": int((clean_numeric != 0).sum()),
                    }

                    # Sample values (first 3 non-zero)
                    non_zero_sample = clean_numeric[clean_numeric != 0].head(3).tolist()
                    analysis["sample_numeric_values"][str(col)] = [
                        float(x) for x in non_zero_sample
                    ]

            else:
                analysis["text_columns"] += 1

        # Calculate data quality metrics
        if analysis["total_numeric_values"] > 0:
            analysis["data_quality_score"] = (
                analysis["non_zero_numeric_values"] / analysis["total_numeric_values"]
            )
            analysis["numeric_coverage"] = (
                analysis["total_numeric_values"]
                / (analysis["total_rows"] * analysis["numeric_columns"])
                if analysis["numeric_columns"] > 0
                else 0
            )
        else:
            analysis["data_quality_score"] = 0.0
            analysis["numeric_coverage"] = 0.0

        return analysis

    def validate_model_data_integrity(self, model_name: str) -> dict:
        """Validate data integrity for a single model."""
        logger.info("Validating data integrity for %s", model_name)

        # Load corrected data
        df = self.load_corrected_model(model_name)
        if df is None:
            return {"status": "error", "message": "Could not load corrected model"}

        # Analyze numeric content
        analysis = self.analyze_numeric_content(df, model_name)

        # Determine validation status
        if analysis["numeric_columns"] == 0:
            status = "no_numeric_data"
            message = "No numeric columns detected in corrected data"
        elif analysis["data_quality_score"] == 0:
            status = "all_zero_values"
            message = f"All {analysis['total_numeric_values']} numeric values are zero"
        elif (
            analysis["data_quality_score"] < MINIMUM_NONZERO_RATE
        ):  # Less than 10% non-zero
            status = "mostly_zero"
            message = ".1%"
        elif (
            analysis["numeric_coverage"] < MINIMUM_NUMERIC_RATE
        ):  # Less than 50% coverage
            status = "sparse_data"
            message = ".1%"
        else:
            status = "good_integrity"
            message = (
                f"Good data integrity: {analysis['numeric_columns']}"
                f" numeric columns, {analysis['data_quality_score']:.1%} quality"
            )

        return {
            "status": status,
            "message": message,
            "analysis": analysis,
        }

    def validate_all_models(self) -> dict[str, dict]:
        """Validate data integrity for all corrected models."""
        logger.info("Starting data integrity validation for all corrected models...")

        models = ["Panel", "WES (P)", "WES (T)", "WGS (P)", "WGS (T)"]
        results = {}

        for model_name in models:
            result = self.validate_model_data_integrity(model_name)
            results[model_name] = result

            status_emoji = {
                "good_integrity": "✅",
                "sparse_data": "⚠️",
                "mostly_zero": "⚠️",
                "all_zero_values": "❌",
                "no_numeric_data": "❌",
                "error": "❌",
            }.get(result.get("status", "unknown"), "❓")

            logger.info(
                "%s %s: %s",
                status_emoji,
                model_name,
                result.get("message", "Unknown status"),
            )

        return results

    def generate_integrity_report(self, results: dict[str, dict]) -> str:
        """Generate a comprehensive integrity report."""
        report_lines = []
        report_lines.append("# Data Integrity Validation Report")
        report_lines.append("")
        report_lines.append("## Executive Summary")
        report_lines.append("")

        # Summary statistics
        total_models = len(results)
        good_models = sum(
            1 for r in results.values() if r.get("status") == "good_integrity"
        )
        issues_models = sum(
            1
            for r in results.values()
            if r.get("status")
            in ["sparse_data", "mostly_zero", "all_zero_values", "no_numeric_data"]
        )

        report_lines.append(f"- **Total Models**: {total_models}")
        report_lines.append(f"- **Good Integrity**: {good_models}")
        report_lines.append(f"- **Issues Found**: {issues_models}")
        report_lines.append("")

        # Detailed results
        report_lines.append("## Detailed Results")
        report_lines.append("")

        for model_name, result in results.items():
            status = result.get("status", "unknown")
            message = result.get("message", "No details")
            analysis = result.get("analysis", {})

            report_lines.append(f"### {model_name}")
            report_lines.append(f"- **Status**: {status.upper()}")
            report_lines.append(f"- **Summary**: {message}")
            report_lines.append(
                "- **Shape**: "
                f"{analysis.get('total_rows', 0)}"
                " rows x "
                f"{analysis.get('total_columns', 0)}"
                " columns",
            )
            report_lines.append(
                f"- **Numeric Columns**: {analysis.get('numeric_columns', 0)}",
            )
            report_lines.append(
                f"- **Text Columns**: {analysis.get('text_columns', 0)}",
            )
            report_lines.append(
                f"- **Empty Columns**: {analysis.get('empty_columns', 0)}",
            )

            if analysis.get("data_quality_score", 0) > 0:
                report_lines.append(".1%")
                report_lines.append(".1%")

            # Sample numeric values
            sample_values = analysis.get("sample_numeric_values", {})
            if sample_values:
                report_lines.append("- **Sample Values**:")
                for col, values in list(sample_values.items())[
                    :3
                ]:  # Show first 3 columns
                    report_lines.append(
                        f"  - {col}: {values[:3]}",
                    )  # Show first 3 values

            report_lines.append("")

        # Recommendations
        report_lines.append("## Recommendations")
        report_lines.append("")

        if good_models == total_models:
            report_lines.append(
                "✅ **All models have good data integrity.** Proceed with Phase "
                "4 data population.",
            )
        elif good_models > 0:
            report_lines.append(
                "⚠️ **"
                f"{good_models}"
                "/"
                f"{total_models}"
                " models have good integrity.** Review and fix remaining "
                "models before Phase 4.",
            )
        else:
            report_lines.append(
                "❌ **No models have good data integrity.** Critical issues must"
                " be resolved before proceeding.",
            )

        return "\n".join(report_lines)


def main() -> None:
    """Validate the corrected workbook data."""
    excel_path = (
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )

    if not Path(excel_path).exists():
        logger.error("Excel file not found: %s", excel_path)
        return

    validator = DataIntegrityValidator(excel_path)
    results = validator.validate_all_models()

    # Generate and save report
    report = validator.generate_integrity_report(results)
    report_path = Path("DATA_INTEGRITY_VALIDATION_REPORT.md")
    report_path.write_text(report)

    sys.stdout.writelines((str("\n" + "=" * 60), "\n"))
    sys.stdout.writelines(("DATA INTEGRITY VALIDATION RESULTS", "\n"))
    sys.stdout.writelines((str("=" * 60), "\n"))

    for model_name, result in results.items():
        status = result.get("status", "unknown")
        message = result.get("message", "No details")
        analysis = result.get("analysis", {})

        status_emoji = {
            "good_integrity": "✅",
            "sparse_data": "⚠️",
            "mostly_zero": "⚠️",
            "all_zero_values": "❌",
            "no_numeric_data": "❌",
            "error": "❌",
        }.get(status, "❓")

        sys.stdout.writelines((f"{status_emoji} {model_name}: {message}", "\n"))

        if analysis:
            numeric_cols = analysis.get("numeric_columns", 0)
            quality_score = analysis.get("data_quality_score", 0)
            if numeric_cols > 0:
                sys.stdout.writelines(
                    (f"    📊 Quality Score: {quality_score:.1f}%", "\n"),
                )

    sys.stdout.writelines((f"\n📄 Detailed report saved to: {report_path}", "\n"))


if __name__ == "__main__":
    main()
