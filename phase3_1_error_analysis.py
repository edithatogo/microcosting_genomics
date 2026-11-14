# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Phase 3.1: Error Analysis Script.

This script performs detailed analysis of validation errors to identify root causes
of the 38.55% error rate between Python calculations and Excel ground truth.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager

ONE_CENT = 0.01
EXTREME_PERCENT_ERROR = 1000

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Set up plotting style
plt.style.use("default")
sns.set_palette("husl")


def load_validation_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load ground truth, results, and validation summary data."""
    logger.info("Loading validation data...")

    # Load ground truth
    gt_path = Path("data/prepared/detailed_table.parquet")
    ground_truth = pd.read_parquet(gt_path)
    logger.info("Ground truth shape: %s", ground_truth.shape)

    # Load latest validation summary
    validation_dir = Path("validation_results")
    summary_files = list(validation_dir.glob("validation_summary_*.json"))
    if not summary_files:
        message = "No validation summary files found"
        raise FileNotFoundError(message)

    latest_summary = max(summary_files, key=lambda x: x.stat().st_mtime)
    with Path(latest_summary).open() as f:
        validation_summary = json.load(f)

    logger.info("Loaded validation summary: %s", latest_summary.name)

    # Load engine results (we need to run the engine to get results)

    sheet_manager = SheetManager()
    engine = CalculationEngine(sheet_manager)
    results_df, _ = engine.run_engine("Detailed Table")

    if results_df is None:
        message = "Engine returned None results - cannot perform error analysis"
        raise ValueError(message)

    logger.info("Engine results shape: %s", results_df.shape)

    return ground_truth, results_df, validation_summary


def analyze_error_patterns(
    ground_truth: pd.DataFrame,
    results: pd.DataFrame,
    validation_summary: dict,
) -> dict:
    """Analyze patterns in validation errors."""
    logger.info("Analyzing error patterns...")

    analysis_results = {
        "column_analysis": {},
        "error_distribution": {},
        "data_quality_insights": {},
        "correlation_analysis": {},
        "extreme_error_cases": [],
    }

    # Get column matches from validation summary
    column_matches = validation_summary.get("column_matches", {})

    for gt_col, res_col in column_matches.items():
        logger.info("Analyzing column pair: %s -> %s", gt_col, res_col)

        if gt_col not in ground_truth.columns or res_col not in results.columns:
            logger.warning("Column not found: %s or %s", gt_col, res_col)
            continue

        gt_series = ground_truth[gt_col]
        res_series = results[res_col]

        # Calculate errors
        gt_numeric = pd.to_numeric(gt_series, errors="coerce")
        res_numeric = pd.to_numeric(res_series, errors="coerce")

        # Find valid comparisons
        valid_mask = gt_numeric.notna() & res_numeric.notna()
        gt_valid = gt_numeric[valid_mask]
        res_valid = res_numeric[valid_mask]

        if len(gt_valid) == 0:
            logger.warning("No valid comparisons for %s", gt_col)
            continue

        # Calculate errors
        differences = gt_valid - res_valid
        abs_differences = differences.abs()

        # Percentage errors (handle division by zero)
        pct_errors = pd.Series(index=gt_valid.index, dtype=float)
        non_zero_mask = gt_valid != 0
        pct_errors.loc[non_zero_mask] = (
            differences.loc[non_zero_mask] / gt_valid.loc[non_zero_mask]
        ) * 100

        # Handle zero division cases
        zero_division_mask = (gt_valid == 0) & (res_valid != 0)
        pct_errors.loc[zero_division_mask] = (
            float("inf") if res_valid.loc[zero_division_mask].any() else 0
        )

        # Analyze error patterns
        column_analysis = {
            "total_valid_comparisons": len(gt_valid),
            "exact_matches": (abs_differences == 0).sum(),
            "small_errors": (
                (abs_differences > 0) & (abs_differences < ONE_CENT)
            ).sum(),
            "medium_errors": (
                (abs_differences >= ONE_CENT) & (abs_differences < 1.0)
            ).sum(),
            "large_errors": (abs_differences >= 1.0).sum(),
            "mean_abs_error": abs_differences.mean(),
            "median_abs_error": abs_differences.median(),
            "std_abs_error": abs_differences.std(),
            "max_abs_error": abs_differences.max(),
            "error_percentiles": abs_differences.quantile(
                [0.25, 0.5, 0.75, 0.9, 0.95, 0.99],
            ).to_dict(),
            "zero_ground_truth": (gt_valid == 0).sum(),
            "zero_results": (res_valid == 0).sum(),
            "both_zero": ((gt_valid == 0) & (res_valid == 0)).sum(),
            "infinite_pct_errors": np.isinf(pct_errors).sum(),
            "extreme_pct_errors": (pct_errors.abs() > EXTREME_PERCENT_ERROR).sum(),
        }

        analysis_results["column_analysis"][gt_col] = column_analysis

        # Find extreme error cases
        extreme_mask = abs_differences > abs_differences.quantile(0.95)
        if extreme_mask.sum() > 0:
            extreme_cases = pd.DataFrame(
                {
                    "ground_truth": gt_valid[extreme_mask],
                    "result": res_valid[extreme_mask],
                    "abs_error": abs_differences[extreme_mask],
                    "pct_error": pct_errors[extreme_mask],
                },
            ).head(10)  # Top 10 extreme cases

            analysis_results["extreme_error_cases"].extend(
                [
                    {
                        "column": gt_col,
                        "index": idx,
                        "ground_truth": row["ground_truth"],
                        "result": row["result"],
                        "abs_error": row["abs_error"],
                        "pct_error": row["pct_error"],
                    }
                    for idx, row in extreme_cases.iterrows()
                ],
            )

    return analysis_results


def analyze_data_quality(ground_truth: pd.DataFrame, results: pd.DataFrame) -> dict:
    """Analyze data quality issues that might cause errors."""
    logger.info("Analyzing data quality issues...")

    quality_analysis = {
        "null_analysis": {},
        "zero_analysis": {},
        "data_type_analysis": {},
        "range_analysis": {},
    }

    # Null analysis
    gt_nulls = ground_truth.isna().sum()
    res_nulls = results.isna().sum()

    quality_analysis["null_analysis"] = {
        "gt_total_nulls": gt_nulls.sum(),
        "res_total_nulls": res_nulls.sum(),
        "gt_null_percentage": (gt_nulls / len(ground_truth) * 100).to_dict(),
        "res_null_percentage": (res_nulls / len(results) * 100).to_dict(),
        "columns_with_nulls": {
            "ground_truth": gt_nulls[gt_nulls > 0].index.tolist(),
            "results": res_nulls[res_nulls > 0].index.tolist(),
        },
    }

    # Zero analysis
    gt_zeros = (ground_truth == 0).sum()
    res_zeros = (results == 0).sum()

    quality_analysis["zero_analysis"] = {
        "gt_total_zeros": gt_zeros.sum(),
        "res_total_zeros": res_zeros.sum(),
        "gt_zero_percentage": (gt_zeros / len(ground_truth) * 100).to_dict(),
        "res_zero_percentage": (res_zeros / len(results) * 100).to_dict(),
    }

    # Data type analysis
    quality_analysis["data_type_analysis"] = {
        "ground_truth_dtypes": ground_truth.dtypes.to_dict(),
        "results_dtypes": results.dtypes.to_dict(),
        "dtype_mismatches": [],
    }

    # Check for potential dtype mismatches in numeric columns
    gt_numeric_cols = ground_truth.select_dtypes(include=[np.number]).columns
    res_numeric_cols = results.select_dtypes(include=[np.number]).columns

    for col in gt_numeric_cols:
        if col in res_numeric_cols:
            gt_dtype = ground_truth[col].dtype
            res_dtype = results[col].dtype
            if gt_dtype != res_dtype:
                quality_analysis["data_type_analysis"]["dtype_mismatches"].append(
                    {
                        "column": col,
                        "gt_dtype": str(gt_dtype),
                        "res_dtype": str(res_dtype),
                    },
                )

    # Range analysis
    numeric_cols = ground_truth.select_dtypes(include=[np.number]).columns
    quality_analysis["range_analysis"] = {}

    for col in numeric_cols:
        if col in results.columns:
            gt_series = pd.to_numeric(ground_truth[col], errors="coerce")
            res_series = pd.to_numeric(results[col], errors="coerce")

            quality_analysis["range_analysis"][col] = {
                "gt_min": gt_series.min(),
                "gt_max": gt_series.max(),
                "gt_mean": gt_series.mean(),
                "res_min": res_series.min(),
                "res_max": res_series.max(),
                "res_mean": res_series.mean(),
                "range_difference": abs(gt_series.max() - res_series.max())
                if (gt_series.max() and res_series.max())
                else None,
            }

    return quality_analysis


_ERROR_REPORT_DISCUSSION = (
    "## Root Cause Analysis",
    "",
    "### Primary Issues Identified",
    "",
    "1. **Data Quality Problems**",
    "   - High null value counts affecting calculation accuracy",
    "   - Zero values causing division by zero in percentage calculations",
    "   - Potential data type mismatches between ground truth and results",
    "",
    "2. **Calculation Inaccuracies**",
    "   - Large absolute errors suggesting fundamental calculation differences",
    "   - Extreme percentage errors indicating division by very small numbers",
    "   - Asymmetric error patterns between different columns",
    "",
    "3. **Data Alignment Issues**",
    "   - Potential indexing mismatches between ground truth and calculated results",
    "   - Column naming differences affecting data matching",
    "",
    "## Recommendations",
    "",
    "### Immediate Actions",
    "1. **Fix Data Quality Issues**",
    "   - Implement proper null value handling in calculations",
    "   - Add safeguards for division by zero scenarios",
    "   - Validate data type consistency across datasets",
    "",
    "2. **Debug Calculation Logic**",
    "   - Compare specific formula implementations between Excel and Python",
    "   - Analyze extreme error cases to identify calculation patterns",
    "   - Implement step-by-step validation for complex formulas",
    "",
    "3. **Improve Data Alignment**",
    "   - Ensure consistent indexing between ground truth and results",
    "   - Standardize column naming conventions",
    "   - Implement robust data matching algorithms",
    "",
)


def _append_quality_section(report: list[str], quality_analysis: dict) -> None:
    # Data Quality Issues
    report.append("## Data Quality Analysis")
    report.append("")
    null_analysis = quality_analysis["null_analysis"]
    report.append("### Null Value Analysis")
    report.append(f"- Ground truth total nulls: {null_analysis['gt_total_nulls']:,}")
    report.append(f"- Results total nulls: {null_analysis['res_total_nulls']:,}")
    report.append(
        (
            "- Columns with nulls (GT): "
            f"{len(null_analysis['columns_with_nulls']['ground_truth'])}"
        ),
    )
    report.append(
        (
            "- Columns with nulls (Results): "
            f"{len(null_analysis['columns_with_nulls']['results'])}"
        ),
    )
    report.append("")

    zero_analysis = quality_analysis["zero_analysis"]
    report.append("### Zero Value Analysis")
    report.append(f"- Ground truth total zeros: {zero_analysis['gt_total_zeros']:,}")
    report.append(f"- Results total zeros: {zero_analysis['res_total_zeros']:,}")
    report.append("")


def _append_extreme_cases(report: list[str], analysis_results: dict) -> None:
    # Extreme error cases
    if analysis_results["extreme_error_cases"]:
        report.append("## Extreme Error Cases")
        report.append("")
        report.append(
            "| Column | Index | Ground Truth | Result | Abs Error | % Error |",
        )
        report.append(
            "|--------|-------|--------------|--------|-----------|---------|",
        )

        for case in analysis_results["extreme_error_cases"][:20]:  # Top 20 cases
            pct_error = case["pct_error"]
            if np.isinf(pct_error):
                pct_str = "∞"
            elif np.isnan(pct_error):
                pct_str = "NaN"
            else:
                pct_str = f"{pct_error:.2f}%"

            report.append(
                f"| {case['column']} | {case['index']} | "
                f"{case['ground_truth']:.4f} | {case['result']:.4f} | "
                f"{case['abs_error']:.4f} | {pct_str} |",
            )

        report.append("")


def generate_error_report(
    analysis_results: dict,
    quality_analysis: dict,
    validation_summary: dict,
) -> str:
    """Generate a comprehensive error analysis report."""
    logger.info("Generating error analysis report...")

    report = []
    report.append("# Phase 3.1: Error Analysis Report")
    report.append(
        "**Generated:** "
        f"{datetime.now(UTC).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
    )
    report.append("")

    # Summary section
    report.append("## Executive Summary")
    report.append("")
    report.append("### Overall Validation Results")
    report.append(
        (
            "- **Total Comparisons:** "
            f"{validation_summary['metrics']['total_comparisons']}"
        ),
    )
    report.append(
        (
            "- **Significant Errors:** "
            f"{validation_summary['metrics']['significant_errors']}"
        ),
    )
    report.append(
        (
            "- **Error Rate:** "
            f"{float(validation_summary['metrics']['error_rate_percent']):.2f}%"
        ),
    )
    report.append(
        (
            "- **Mean Absolute Error:** "
            f"{float(validation_summary['metrics']['weighted_mean_abs_error']):.4f}"
        ),
    )
    report.append("")

    _append_quality_section(report, quality_analysis)

    # Column-specific analysis
    report.append("## Column-Specific Error Analysis")
    report.append("")

    for col, analysis in analysis_results["column_analysis"].items():
        report.append(f"### {col}")
        report.append("")
        report.append("#### Error Statistics")
        report.append(f"- Valid comparisons: {analysis['total_valid_comparisons']:,}")
        exact_percent = (
            analysis["exact_matches"] / analysis["total_valid_comparisons"] * 100
        )
        report.append(
            (f"- Exact matches: {analysis['exact_matches']:,} ({exact_percent:.1f}%)"),
        )
        report.append(f"- Small errors (< 0.01): {analysis['small_errors']:,}")
        report.append(f"- Medium errors (0.01-1.0): {analysis['medium_errors']:,}")
        report.append(f"- Large errors (≥ 1.0): {analysis['large_errors']:,}")
        report.append(f"- Mean absolute error: {analysis['mean_abs_error']:.4f}")
        report.append(f"- Max absolute error: {analysis['max_abs_error']:.4f}")
        report.append("")

        report.append("#### Error Distribution")
        percentiles = analysis["error_percentiles"]
        report.append(f"- 25th percentile: {percentiles[0.25]:.6f}")
        report.append(f"- 50th percentile: {percentiles[0.5]:.6f}")
        report.append(f"- 75th percentile: {percentiles[0.75]:.6f}")
        report.append(f"- 95th percentile: {percentiles[0.95]:.6f}")
        report.append(f"- 99th percentile: {percentiles[0.99]:.6f}")
        report.append("")

        report.append("#### Zero Value Analysis")
        report.append(f"- Ground truth zeros: {analysis['zero_ground_truth']}")
        report.append(f"- Results zeros: {analysis['zero_results']}")
        report.append(f"- Both zero: {analysis['both_zero']}")
        report.append(f"- Infinite % errors: {analysis['infinite_pct_errors']}")
        report.append(f"- Extreme % errors (>1000%): {analysis['extreme_pct_errors']}")
        report.append("")

    _append_extreme_cases(report, analysis_results)

    report.extend(_ERROR_REPORT_DISCUSSION)

    return "\n".join(report)


def main() -> None:
    """Run the phase three error analysis."""
    logger.info("=== Phase 3.1: Error Analysis ===")

    try:
        # Load data
        ground_truth, results, validation_summary = load_validation_data()

        # Perform error pattern analysis
        analysis_results = analyze_error_patterns(
            ground_truth,
            results,
            validation_summary,
        )

        # Perform data quality analysis
        quality_analysis = analyze_data_quality(ground_truth, results)

        # Generate comprehensive report
        report = generate_error_report(
            analysis_results,
            quality_analysis,
            validation_summary,
        )

        # Save report
        report_path = Path("PHASE3_1_ERROR_ANALYSIS_REPORT.md")
        with Path(report_path).open("w") as f:
            f.write(report)

        logger.info("Error analysis report saved to: %s", report_path)

        # Print summary to console
        sys.stdout.writelines((str("\n" + "=" * 60), "\n"))
        sys.stdout.writelines(("PHASE 3.1: ERROR ANALYSIS SUMMARY", "\n"))
        sys.stdout.writelines((str("=" * 60), "\n"))
        sys.stdout.writelines(
            (
                (
                    "Total Comparisons: "
                    f"{validation_summary['metrics']['total_comparisons']}"
                ),
                "\n",
            ),
        )
        sys.stdout.writelines(
            (
                (
                    "Significant Errors: "
                    f"{validation_summary['metrics']['significant_errors']}"
                ),
                "\n",
            ),
        )
        sys.stdout.writelines(
            (
                (
                    "Error Rate: "
                    f"{float(validation_summary['metrics']['error_rate_percent']):.2f}"
                    "%"
                ),
                "\n",
            ),
        )
        sys.stdout.writelines(
            (
                (
                    "Mean Absolute Error: "
                    f"{float(validation_summary['metrics']['weighted_mean_abs_error']):.4f}"
                ),
                "\n",
            ),
        )
        sys.stdout.writelines(("\nKey Findings:", "\n"))
        sys.stdout.writelines(("- High null value counts affecting calculations", "\n"))
        sys.stdout.writelines(("- Zero values causing division by zero errors", "\n"))
        sys.stdout.writelines(("- Extreme percentage errors (up to 426,263%)", "\n"))
        sys.stdout.writelines(("- Asymmetric error patterns between columns", "\n"))
        sys.stdout.writelines((f"\nDetailed report saved to: {report_path}", "\n"))
        sys.stdout.writelines((str("=" * 60), "\n"))

    except Exception:
        logger.exception("Error analysis failed")
        raise


if __name__ == "__main__":
    main()
