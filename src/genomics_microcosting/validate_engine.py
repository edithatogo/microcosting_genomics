# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Validation script for the genomics microcosting calculation engine.

This script compares the output of the CalculationEngine against ground truth data
to validate accuracy and identify any discrepancies.
"""

import concurrent.futures
import hashlib
import json
import logging
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, NotRequired, TypedDict

import openpyxl
import polars as pl
from pydantic import TypeAdapter, ValidationError

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager
from genomics_microcosting.t1_baseline_lineage import BASELINE_SHA256

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)


class ValidationConfig(TypedDict):
    """Execution and acceptance settings for the workbook comparator."""

    significant_error_threshold: float
    percentage_error_threshold: float
    max_display_columns: int
    export_results: bool
    output_dir: str
    cache_dir: str
    max_workers: int
    chunk_size: int
    use_cache: bool


class DataQuality(TypedDict):
    """Presence and zero counts retained separately from numeric differences."""

    presence_disagreements: int
    gt_nulls: int
    res_nulls: int
    gt_zeros: int
    res_zeros: int
    valid_comparisons: int
    gt_zeros_in_valid: int
    res_zeros_in_valid: int


class ColumnComparison(TypedDict):
    """One complete positional numeric comparison."""

    gt_column: str
    res_column: str
    comparisons: int
    mean_abs_error: float
    mean_percentage_error: float
    max_abs_error: float
    max_percentage_error: float
    significant_abs_errors: int
    significant_pct_errors: int
    abs_error_percentiles: dict[float, float | None]
    pct_error_percentiles: dict[float, float | None]
    data_quality: DataQuality


class SummaryMetrics(TypedDict, total=False):
    """Numeric acceptance metrics; an empty record means unavailable validation."""

    total_comparisons: int
    significant_errors: int
    presence_disagreements: int
    total_columns_validated: int
    error_rate_percent: float
    weighted_mean_abs_error: float


class ValidationResults(TypedDict):
    """Validation progress with optional measurements recorded only when available."""

    timestamp: str
    success: bool
    ground_truth_loaded: bool
    engine_initialized: bool
    engine_run: bool
    validation_performed: bool
    metrics: SummaryMetrics
    errors: list[str]
    column_matches: dict[str, str]
    validation_details: list[ColumnComparison]
    ground_truth_shape: NotRequired[tuple[int, int]]
    results_shape: NotRequired[tuple[int, int]]
    engine_execution_time: NotRequired[float]
    total_execution_time: NotRequired[float]
    engine_errors: NotRequired[list[str]]
    engine_warnings: NotRequired[list[str]]
    source_marker_counts: NotRequired[dict[str, int]]
    verified_engine_markers: NotRequired[int]


class CachedComparisons(TypedDict):
    """Validated JSON cache envelope; malformed records are cache misses."""

    timestamp: float
    result: list[ColumnComparison]


CACHE_ADAPTER = TypeAdapter(CachedComparisons)
CACHE_LIFETIME_SECONDS = 3600
MINIMUM_COLUMN_MATCH_SCORE = 10

# Validation configuration
VALIDATION_CONFIG: ValidationConfig = {
    "significant_error_threshold": 0.01,  # Absolute difference threshold
    "percentage_error_threshold": 1.0,  # Percentage difference threshold (%)
    "max_display_columns": 10,  # Max columns to display in reports
    "export_results": True,  # Whether to export detailed results
    "output_dir": os.environ.get(
        "MICROCOSTING_OUTPUT_DIR",
        "validation_results",
    ),  # Directory for output files
    "cache_dir": str(
        Path(os.environ.get("MICROCOSTING_OUTPUT_DIR", ".private-runs"))
        / "validation-cache",
    ),  # Cache directory for intermediate results
    "max_workers": 4,  # Maximum parallel workers
    "chunk_size": 1000,  # Process data in chunks for memory efficiency
    "use_cache": False,  # Whether to use caching for performance
}


def get_cache_key(data_hash: str, operation: str) -> str:
    """Generate a cache key for the given data and operation."""
    return hashlib.sha256(f"{data_hash}_{operation}".encode()).hexdigest()


def load_from_cache(cache_key: str) -> list[ColumnComparison] | None:
    """Load cached result if available and valid."""
    if not VALIDATION_CONFIG["use_cache"]:
        return None

    cache_dir = Path(VALIDATION_CONFIG["cache_dir"])
    cache_file = cache_dir / f"{cache_key}.json"

    if cache_file.exists():
        try:
            cached_data = CACHE_ADAPTER.validate_json(
                cache_file.read_bytes(),
                strict=True,
            )
            if 0 <= time.time() - cached_data["timestamp"] < CACHE_LIFETIME_SECONDS:
                logger.info("Loaded cached result for %s", cache_key)
                return cached_data["result"]
            logger.info("Cache expired for %s", cache_key)
        except OSError, ValidationError:
            logger.warning("Failed to load cache %s", cache_key)

    return None


def save_to_cache(cache_key: str, result: list[ColumnComparison]) -> None:
    """Save result to cache."""
    if not VALIDATION_CONFIG["use_cache"]:
        return

    cache_dir = Path(VALIDATION_CONFIG["cache_dir"])
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"{cache_key}.json"

    try:
        cached_data = {
            "timestamp": time.time(),
            "result": result,
        }
        with cache_file.open("w") as f:
            json.dump(cached_data, f)
        logger.debug("Cached result for %s", cache_key)
    except (OSError, TypeError) as e:
        logger.warning("Failed to save cache %s: %s", cache_key, e)


def create_dataframe_hash(df: pl.DataFrame) -> str:
    """Hash every value and the ordered schema; previews are not cache identity."""
    digest = hashlib.sha256()
    digest.update(repr((df.shape, list(df.schema.items()))).encode())
    for row in df.iter_rows():
        # Workbook results contain mixed native Excel scalars in Object columns.
        # Tag values by type and length so delimiters cannot alias adjacent cells.
        for value in row:
            payload = repr(
                (type(value).__module__, type(value).__qualname__, value),
            ).encode()
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
    return digest.hexdigest()


def load_ground_truth() -> pl.DataFrame | None:
    """Load the ground truth data from prepared parquet files."""
    ground_truth_paths = [
        "data/prepared/detailed_table.parquet",
        "data/prepared/ground_truth.parquet",
    ]

    for path in ground_truth_paths:
        path_obj = (
            Path(os.environ.get("MICROCOSTING_PREPARED_DIR", "data/prepared"))
            / Path(path).name
        )
        if path_obj.exists():
            try:
                start_time = time.time()
                df = pl.read_parquet(path_obj)
                load_time = time.time() - start_time

                logger.info("Loaded ground truth from %s", path)
                logger.info("Ground truth shape: %s", df.shape)
                logger.info("Ground truth columns: %s", len(df.columns))
                logger.info(
                    "Ground truth memory usage: %s MB",
                    format(df.estimated_size("mb"), ".1f"),
                )
                logger.info("Load time: %s seconds", format(load_time, ".2f"))

                # Basic data quality checks
                null_counts = sum(df.null_count().row(0))
                if null_counts > 0:
                    logger.warning("Ground truth contains %s null values", null_counts)

            except Exception:
                logger.exception("Error loading %s", path)
                continue
            else:
                return df

    logger.error("No ground truth data found in expected locations")
    return None


def _source_marker(source: object, target: object, location: str) -> int:
    if isinstance(source, str):
        if source.startswith("#") or target is not None:
            msg = f"Unaccounted source marker at {location}"
            raise ValueError(msg)
        return 1
    if source is None:
        if target is not None:
            msg = f"Unexpected target at {location}"
            raise ValueError(msg)
        return 0
    if not (
        isinstance(source, int | float)
        and isinstance(target, int | float)
        and math.isclose(source, target, rel_tol=1e-12, abs_tol=1e-9)
    ):
        msg = f"Ground truth differs from source at {location}"
        raise ValueError(msg)
    return 0


def verify_ground_truth_source(
    reference: pl.DataFrame,
    workbook_path: Path,
    expected_sha256: str,
) -> dict[str, int]:
    """Verify retained numeric targets against the exact workbook cached cells."""
    if hashlib.sha256(workbook_path.read_bytes()).hexdigest() != expected_sha256:
        msg = "Ground truth workbook identity mismatch"
        raise ValueError(msg)
    columns = {
        "Unit Cost (AUD $/unit) LL": 12,
        "Estimate_3": 13,
        "UL_3": 14,
    }
    if not set(columns) <= set(reference.columns):
        msg = "Required ground truth unit-cost columns are missing"
        raise ValueError(msg)
    workbook = openpyxl.load_workbook(workbook_path, data_only=True, read_only=True)
    try:
        sheet = workbook["Detailed Table"]
        rows = sheet.iter_rows(min_row=5, max_col=15, values_only=True)
        counts = dict.fromkeys(columns, 0)
        row_count = 0
        for index, row in enumerate(rows):
            if index >= reference.height:
                msg = "Ground truth row count does not match source workbook"
                raise ValueError(msg)
            row_count += 1
            for column, source_index in columns.items():
                source = row[source_index]
                target = reference[column][index]
                counts[column] += _source_marker(
                    source,
                    target,
                    f"row {index + 5}: {column}",
                )
        if row_count != reference.height:
            msg = "Ground truth row count does not match source workbook"
            raise ValueError(msg)
        return counts
    finally:
        workbook.close()


def verify_engine_markers(result: pl.DataFrame, workbook_path: Path) -> int:
    """Require literal source unit-cost markers to survive engine evaluation."""
    columns = {
        "Estimates Unit Cost (AUD $/unit) LL": 12,
        "Estimates Unit Cost (AUD $/unit) Estimate": 13,
        "Estimates Unit Cost (AUD $/unit) UL": 14,
    }
    if not set(columns) <= set(result.columns):
        msg = "Required result unit-cost columns are missing"
        raise ValueError(msg)
    workbook = openpyxl.load_workbook(workbook_path, data_only=True, read_only=True)
    try:
        rows = workbook["Detailed Table"].iter_rows(
            min_row=5,
            max_col=15,
            values_only=True,
        )
        checked = 0
        row_count = 0
        for index, row in enumerate(rows):
            if index >= result.height:
                msg = "Result row count does not match source workbook"
                raise ValueError(msg)
            row_count += 1
            for column, source_index in columns.items():
                source = row[source_index]
                if isinstance(source, str):
                    if source.startswith("#") or result[column][index] != source:
                        msg = f"Source marker differs at row {index + 5}: {column}"
                        raise ValueError(msg)
                    checked += 1
        if row_count != result.height:
            msg = "Result row count does not match source workbook"
            raise ValueError(msg)
        return checked
    finally:
        workbook.close()


def find_unit_cost_columns(df: pl.DataFrame) -> list[str]:
    """Find all columns that contain unit cost information."""
    unit_cost_cols: list[str] = []
    cost_keywords = ["unit cost", "unit_cost", "cost", "price", "amount"]

    for col in df.columns:
        col_str = str(col).lower()
        if any(keyword in col_str for keyword in cost_keywords):
            unit_cost_cols.append(col)

    logger.info("Found %s potential unit cost columns", len(unit_cost_cols))
    if unit_cost_cols:
        logger.info("Sample unit cost columns:")
        for col in unit_cost_cols[: VALIDATION_CONFIG["max_display_columns"]]:
            logger.info("  - %s", col)

    return unit_cost_cols


def match_columns(gt_cols: list[str], result_cols: list[str]) -> dict[str, str]:
    """Match ground truth columns to result columns using intelligent matching."""
    matches: dict[str, str] = {}

    for gt_col in gt_cols:
        gt_col_lower = str(gt_col).lower()

        # Find best match based on similarity
        best_match = None
        best_score = 0

        for res_col in result_cols:
            res_col_lower = str(res_col).lower()

            # Exact match gets highest score
            if gt_col_lower == res_col_lower:
                best_match = res_col
                best_score = 100
                break

            # Partial match scoring
            score = 0
            gt_words = set(gt_col_lower.split())
            res_words = set(res_col_lower.split())

            # Common words
            common_words = gt_words.intersection(res_words)
            score += len(common_words) * 20

            # Substring matches
            if any(word in res_col_lower for word in gt_words):
                score += 10

            if score > best_score:
                best_score = score
                best_match = res_col

        if best_match and best_score > MINIMUM_COLUMN_MATCH_SCORE:  # Minimum threshold
            matches[gt_col] = best_match
            logger.info(
                "Matched '%s' -> '%s' (score: %s)",
                gt_col,
                best_match,
                best_score,
            )
        else:
            logger.warning("No good match found for ground truth column: %s", gt_col)

    return matches


def validate_calculation_engine() -> ValidationResults:
    """Validate the CalculationEngine against the ground truth data.

    Returns:
        Dictionary containing validation results and metrics

    """
    logger.info("=== Genomics Microcosting Engine Validation ===")
    start_time = time.time()

    results: ValidationResults = {
        "timestamp": datetime.now(UTC).isoformat(),
        "success": False,
        "ground_truth_loaded": False,
        "engine_initialized": False,
        "engine_run": False,
        "validation_performed": False,
        "metrics": {},
        "errors": [],
        "column_matches": {},
        "validation_details": [],
    }

    try:
        _validate_into(results)
    except Exception as error:
        results["errors"].append(f"Unexpected error during validation: {error}")
        logger.exception("Validation failed with unexpected error")

    finally:
        total_time = time.time() - start_time
        results["total_execution_time"] = total_time
        logger.info("Validation completed in %s seconds", format(total_time, ".2f"))
        if VALIDATION_CONFIG["export_results"]:
            export_validation_results(results)

    return results


def _validate_into(results: ValidationResults) -> None:
    """Load inputs and run the engine, retaining explicit failure progress."""
    # Load ground truth data
    ground_truth_df = load_ground_truth()
    if ground_truth_df is None:
        results["errors"].append("Cannot proceed without ground truth data")
        return

    results["ground_truth_loaded"] = True
    results["ground_truth_shape"] = ground_truth_df.shape

    # Find unit cost columns in ground truth
    gt_unit_cost_cols = find_unit_cost_columns(ground_truth_df)
    if not gt_unit_cost_cols:
        results["errors"].append("No unit cost columns found in ground truth data")
        return

    # Initialize the CalculationEngine
    try:
        sheet_manager = SheetManager(
            prepared_data_path=os.environ.get("MICROCOSTING_PREPARED_DIR"),
        )
        engine = CalculationEngine(sheet_manager)
        logger.info("CalculationEngine initialized successfully")
        results["engine_initialized"] = True
    except Exception as e:
        logger.exception("CalculationEngine initialization failed")
        results["errors"].append(f"Error initializing CalculationEngine: {e}")
        return

    try:
        results["source_marker_counts"] = verify_ground_truth_source(
            ground_truth_df,
            sheet_manager.excel_file_path,
            BASELINE_SHA256,
        )
    except (OSError, ValueError, KeyError) as e:
        results["errors"].append(f"Ground truth source verification failed: {e}")
        return

    # Try to run the engine
    try:
        engine_start = time.time()
        results_df, errors = engine.run_engine("Detailed Table")
        engine_time = time.time() - engine_start

        results["engine_run"] = True
        results["engine_execution_time"] = engine_time

        if results_df is None:
            results["errors"].append(
                "Engine returned None - no results to validate",
            )
            if errors:
                results["engine_errors"] = errors
            return

        if errors:
            logger.warning("Warnings during calculation:")
            for error in errors:
                logger.warning("  - %s", error)
            results["engine_warnings"] = errors

    except Exception as e:
        results["errors"].append(f"Error running CalculationEngine: {e}")
        logger.exception("Engine execution failed")
        return

    compare_source_and_engine(
        ground_truth_df,
        results_df,
        results,
        sheet_manager.excel_file_path,
    )


def compare_source_and_engine(
    ground_truth_df: pl.DataFrame,
    results_df: pl.DataFrame,
    results: ValidationResults,
    workbook_path: Path,
) -> None:
    """Check literal markers before accepting numeric engine comparisons."""
    try:
        results["verified_engine_markers"] = verify_engine_markers(
            results_df,
            workbook_path,
        )
    except (OSError, ValueError, KeyError) as e:
        results["errors"].append(f"Engine marker verification failed: {e}")
    else:
        compare_engine_results(ground_truth_df, results_df, results)


def compare_engine_results(
    ground_truth_df: pl.DataFrame,
    results_df: pl.DataFrame,
    results: ValidationResults,
) -> None:
    """Compare available engine outputs and record numeric acceptance metrics."""
    logger.info("Engine results shape: %s", results_df.shape)
    results["results_shape"] = results_df.shape
    # The retained workbook export has duplicate multi-level headers flattened
    # to Estimate_3 and UL_3. Keyword matching silently omitted both columns.
    column_matches = {
        "Unit Cost (AUD $/unit) LL": "Estimates Unit Cost (AUD $/unit) LL",
        "Estimate_3": "Estimates Unit Cost (AUD $/unit) Estimate",
        "UL_3": "Estimates Unit Cost (AUD $/unit) UL",
    }
    results["column_matches"] = column_matches
    if not set(column_matches) <= set(ground_truth_df.columns) or not set(
        column_matches.values(),
    ) <= set(results_df.columns):
        results["errors"].append(
            "Required lower, midpoint and upper unit-cost columns are missing",
        )
        return
    identity = ("Test", "Category", "Sub-Category", "Step")
    if (
        ground_truth_df.height != results_df.height
        or not set(identity) <= set(ground_truth_df.columns)
        or not set(identity) <= set(results_df.columns)
        or any(
            expected is not None and expected != actual
            for column in identity
            for expected, actual in zip(
                ground_truth_df[column].to_list(),
                results_df[column].to_list(),
                strict=True,
            )
        )
    ):
        results["errors"].append("Ground truth and result row identities do not align")
        return

    # Perform validation
    validation_results = perform_validation_parallel(
        ground_truth_df,
        results_df,
        column_matches,
    )
    results["validation_details"] = validation_results
    results["validation_performed"] = True

    # Calculate summary metrics
    results["metrics"] = calculate_summary_metrics(validation_results)

    results["success"] = validation_succeeded(
        results["metrics"],
        len(validation_results),
        len(column_matches),
    )


def perform_validation_parallel(
    gt_df: pl.DataFrame,
    res_df: pl.DataFrame,
    column_matches: dict[str, str],
) -> list[ColumnComparison]:
    """Perform detailed validation on matched columns using parallel processing."""
    validation_results: list[ColumnComparison] = []

    # Create data hash for caching
    gt_hash = create_dataframe_hash(gt_df)
    res_hash = create_dataframe_hash(res_df)
    comparison_policy = {
        "version": 2,
        "absolute_threshold": VALIDATION_CONFIG["significant_error_threshold"],
        "percentage_threshold": VALIDATION_CONFIG["percentage_error_threshold"],
        "column_matches": column_matches,
    }
    data_hash = f"{gt_hash}_{res_hash}_{json.dumps(comparison_policy, sort_keys=True)}"

    # Check cache for entire validation result
    cache_key = get_cache_key(data_hash, "validation_results")
    cached_result = load_from_cache(cache_key)
    if cached_result:
        logger.info("Using cached validation results")
        return cached_result

    logger.info(
        "Performing parallel validation on %s column pairs",
        len(column_matches),
    )

    # Prepare column pairs for parallel processing
    column_pairs = list(column_matches.items())

    # Use ThreadPoolExecutor for I/O bound operations
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=VALIDATION_CONFIG["max_workers"],
    ) as executor:
        # Submit all validation tasks
        future_to_pair = {
            executor.submit(
                compare_columns_optimized,
                gt_df,
                res_df,
                gt_col,
                res_col,
            ): (gt_col, res_col)
            for gt_col, res_col in column_pairs
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_pair):
            gt_col, res_col = future_to_pair[future]
            try:
                result = future.result()
                if result:
                    validation_results.append(result)
                    logger.info("Completed validation for %s vs %s", gt_col, res_col)
            except Exception:
                logger.exception("Validation failed for %s vs %s", gt_col, res_col)

    # Cache the results
    save_to_cache(cache_key, validation_results)

    logger.info(
        "Parallel validation completed: %s successful comparisons",
        len(validation_results),
    )
    return validation_results


def _numeric_series(series: pl.Series) -> pl.Series:
    """Coerce Excel mixed cells to numeric values without changing source values."""
    values: list[float | None] = []
    for value in series.to_list():
        try:
            number = float(value) if value is not None else None
        except TypeError, ValueError:
            number = None
        values.append(number)
    return pl.Series(series.name, values, dtype=pl.Float64).fill_nan(None)


def _required_numeric_statistic(value: object) -> float:
    """Reject absent or nonnumeric aggregates instead of inventing zero error."""
    if not isinstance(value, (float, int)) or isinstance(value, bool):
        message = "Numeric comparison statistic is unavailable"
        raise TypeError(message)
    return float(value)


def compare_columns_optimized(
    gt_df: pl.DataFrame,
    res_df: pl.DataFrame,
    gt_col: str,
    res_col: str,
) -> ColumnComparison | None:
    """Compare aligned values, preserving null-presence disagreements."""
    if gt_df.height != res_df.height:
        message = "Reference and calculated row counts differ"
        raise ValueError(message)
    gt = _numeric_series(gt_df[gt_col])
    res = _numeric_series(res_df[res_col])
    valid = gt.is_not_null() & res.is_not_null()
    comparisons = int(valid.sum())
    if not comparisons:
        return None
    left, right = gt.filter(valid), res.filter(valid)
    difference = left - right
    absolute = difference.abs()
    percentage = pl.DataFrame({"gt": left, "delta": difference}).select(
        pl.when(pl.col("gt") != 0)
        .then(100 * pl.col("delta") / pl.col("gt"))
        .otherwise(pl.col("delta").abs())
        .alias("pct"),
    )["pct"]
    finite = percentage.filter(percentage.is_finite()).abs()
    quantiles = (0.25, 0.5, 0.75, 0.95)
    return {
        "gt_column": gt_col,
        "res_column": res_col,
        "comparisons": comparisons,
        "mean_abs_error": _required_numeric_statistic(absolute.mean()),
        "mean_percentage_error": _required_numeric_statistic(finite.mean())
        if len(finite)
        else float("inf"),
        "max_abs_error": _required_numeric_statistic(absolute.max()),
        "max_percentage_error": _required_numeric_statistic(finite.max())
        if len(finite)
        else float("inf"),
        "significant_abs_errors": int(
            (absolute > VALIDATION_CONFIG["significant_error_threshold"]).sum(),
        ),
        "significant_pct_errors": int(
            (finite > VALIDATION_CONFIG["percentage_error_threshold"]).sum(),
        ),
        "abs_error_percentiles": {
            q: absolute.quantile(q, interpolation="linear") for q in quantiles
        },
        "pct_error_percentiles": {
            q: finite.quantile(q, interpolation="linear") for q in quantiles
        },
        "data_quality": {
            "presence_disagreements": int((gt.is_null() != res.is_null()).sum()),
            "gt_nulls": gt.null_count(),
            "res_nulls": res.null_count(),
            "gt_zeros": int((gt == 0).sum()),
            "res_zeros": int((res == 0).sum()),
            "valid_comparisons": comparisons,
            "gt_zeros_in_valid": int((left == 0).sum()),
            "res_zeros_in_valid": int((right == 0).sum()),
        },
    }


def validation_succeeded(
    metrics: Mapping[str, object],
    completed: int,
    expected: int,
) -> bool:
    """Require complete numeric and presence checks before declaring success."""
    total = metrics.get("total_comparisons")
    return (
        isinstance(total, int)
        and total > 0
        and completed == expected
        and metrics.get("significant_errors") == 0
        and metrics.get("presence_disagreements") == 0
    )


def calculate_summary_metrics(
    validation_results: list[ColumnComparison],
) -> SummaryMetrics:
    """Calculate summary metrics from validation results."""
    if not validation_results:
        return {}

    total_comparisons = sum(r["comparisons"] for r in validation_results)
    significant_errors = sum(r["significant_abs_errors"] for r in validation_results)
    total_abs_error = sum(
        r["mean_abs_error"] * r["comparisons"] for r in validation_results
    )

    metrics: SummaryMetrics = {
        "total_comparisons": total_comparisons,
        "significant_errors": significant_errors,
        "presence_disagreements": sum(
            row["data_quality"]["presence_disagreements"] for row in validation_results
        ),
        "total_columns_validated": len(validation_results),
        "error_rate_percent": (significant_errors / total_comparisons * 100)
        if total_comparisons > 0
        else 0,
        "weighted_mean_abs_error": (total_abs_error / total_comparisons)
        if total_comparisons > 0
        else 0,
    }

    return metrics


def export_validation_results(results: ValidationResults) -> None:
    """Export validation results to files."""
    output_dir = Path(VALIDATION_CONFIG["output_dir"])
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    # Export summary as JSON
    summary_file = output_dir / f"validation_summary_{timestamp}.json"
    with summary_file.open("w") as f:
        json.dump(results, f, indent=2, default=str)

    # Export detailed results as CSV if available
    if results.get("validation_details"):
        details_df = pl.DataFrame(
            [
                {
                    key: json.dumps(value) if isinstance(value, dict) else value
                    for key, value in row.items()
                }
                for row in results["validation_details"]
            ],
        )
        details_file = output_dir / f"validation_details_{timestamp}.csv"
        details_df.write_csv(details_file)

    logger.info("Validation results exported to %s", output_dir)


def compare_columns_detailed(
    gt_df: pl.DataFrame,
    res_df: pl.DataFrame,
    gt_col: str,
    res_col: str,
) -> ColumnComparison | None:
    """Use the same qualified comparator for legacy detailed validation calls."""
    return compare_columns_optimized(gt_df, res_df, gt_col, res_col)


def main() -> ValidationResults:
    """Run validation and log its summary."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    results = validate_calculation_engine()

    logger.info("=== Validation Summary ===")
    if results["success"] and not results["metrics"].get("error_rate_percent", 0):
        metrics = results["metrics"]
        logger.info("Selected detailed-table unit-cost comparisons passed")
        logger.info("Total comparisons: %s", metrics.get("total_comparisons", 0))
        logger.info("Columns validated: %s", metrics.get("total_columns_validated", 0))
        logger.info("Error rate: %.2f%%", metrics.get("error_rate_percent", 0))
        logger.info(
            "Mean absolute error: %.6f",
            metrics.get("weighted_mean_abs_error", 0),
        )
        logger.info(
            "Execution time: %.2f seconds",
            results.get("total_execution_time", 0),
        )
    else:
        logger.error("Validation failed")
        for error in results.get("errors", []):
            logger.error("%s", error)

    return results


def validate_engine() -> int:
    """Return a failing process status for incomplete or disagreeing comparisons."""
    result = main()
    metrics = result.get("metrics", {})
    return (
        0
        if result.get("success")
        and metrics.get("total_comparisons", 0)
        and not metrics.get("error_rate_percent", 0)
        and not metrics.get("presence_disagreements", 0)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(validate_engine())
