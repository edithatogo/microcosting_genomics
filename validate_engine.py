"""
Validation script for the genomics microcosting calculation engine.

This script compares the output of the CalculationEngine against ground truth data
to validate accuracy and identify any discrepancies.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import time
import logging
from datetime import datetime
import json
import concurrent.futures
import pickle
import hashlib

from genomics_microcosting.calculation_engine import CalculationEngine
from genomics_microcosting.sheet_manager import SheetManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Validation configuration
VALIDATION_CONFIG = {
    'significant_error_threshold': 0.01,  # Absolute difference threshold
    'percentage_error_threshold': 1.0,    # Percentage difference threshold (%)
    'max_display_columns': 10,            # Max columns to display in reports
    'export_results': True,               # Whether to export detailed results
    'output_dir': 'validation_results',   # Directory for output files
    'cache_dir': '.validation_cache',     # Cache directory for intermediate results
    'max_workers': 4,                     # Maximum parallel workers
    'chunk_size': 1000,                   # Process data in chunks for memory efficiency
    'use_cache': True                     # Whether to use caching for performance
}


def get_cache_key(data_hash: str, operation: str) -> str:
    """Generate a cache key for the given data and operation."""
    return hashlib.sha256(f"{data_hash}_{operation}".encode()).hexdigest()


def load_from_cache(cache_key: str) -> Optional[Any]:
    """Load cached result if available and valid."""
    if not VALIDATION_CONFIG['use_cache']:
        return None

    cache_dir = Path(VALIDATION_CONFIG['cache_dir'])
    cache_file = cache_dir / f"{cache_key}.pkl"

    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                # Check if cache is still valid (within 1 hour)
                if time.time() - cached_data.get('timestamp', 0) < 3600:
                    logger.info(f"Loaded cached result for {cache_key}")
                    return cached_data['result']
                else:
                    logger.info(f"Cache expired for {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_key}: {e}")

    return None


def save_to_cache(cache_key: str, result: Any) -> None:
    """Save result to cache."""
    if not VALIDATION_CONFIG['use_cache']:
        return

    cache_dir = Path(VALIDATION_CONFIG['cache_dir'])
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"{cache_key}.pkl"

    try:
        cached_data = {
            'timestamp': time.time(),
            'result': result
        }
        with open(cache_file, 'wb') as f:
            pickle.dump(cached_data, f)
        logger.debug(f"Cached result for {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to save cache {cache_key}: {e}")


def create_dataframe_hash(df: pd.DataFrame) -> str:
    """Create a hash of the dataframe for caching purposes."""
    # Use shape, column names, and a sample of values for hashing
    hash_components = [
        str(df.shape),
        str(sorted(df.columns.tolist())),
        str(df.dtypes.to_dict()),
        str(df.head(10).to_string())  # Sample of first 10 rows
    ]
    hash_string = "|".join(hash_components)
    return hashlib.sha256(hash_string.encode()).hexdigest()


def load_ground_truth() -> Optional[pd.DataFrame]:
    """Load the ground truth data from prepared parquet files."""
    ground_truth_paths = [
        "data/prepared/detailed_table.parquet",
        "data/prepared/ground_truth.parquet"
    ]

    for path in ground_truth_paths:
        path_obj = Path(path)
        if path_obj.exists():
            try:
                start_time = time.time()
                df = pd.read_parquet(path)
                load_time = time.time() - start_time

                logger.info(f"Loaded ground truth from {path}")
                logger.info(f"Ground truth shape: {df.shape}")
                logger.info(f"Ground truth columns: {len(df.columns)}")
                logger.info(f"Ground truth memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
                logger.info(f"Load time: {load_time:.2f} seconds")

                # Basic data quality checks
                null_counts = df.isnull().sum().sum()
                if null_counts > 0:
                    logger.warning(f"Ground truth contains {null_counts} null values")

                return df
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
                continue

    logger.error("No ground truth data found in expected locations")
    return None


def find_unit_cost_columns(df: pd.DataFrame) -> List[str]:
    """Find all columns that contain unit cost information."""
    unit_cost_cols = []
    cost_keywords = ['unit cost', 'unit_cost', 'cost', 'price', 'amount']

    for col in df.columns:
        col_str = str(col).lower()
        if any(keyword in col_str for keyword in cost_keywords):
            unit_cost_cols.append(col)

    logger.info(f"Found {len(unit_cost_cols)} potential unit cost columns")
    if unit_cost_cols:
        logger.info("Sample unit cost columns:")
        for col in unit_cost_cols[:VALIDATION_CONFIG['max_display_columns']]:
            logger.info(f"  - {col}")

    return unit_cost_cols


def match_columns(gt_cols: List[str], result_cols: List[str]) -> Dict[str, str]:
    """Match ground truth columns to result columns using intelligent matching."""
    matches = {}

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

        if best_match and best_score > 10:  # Minimum threshold
            matches[gt_col] = best_match
            logger.info(f"Matched '{gt_col}' -> '{best_match}' (score: {best_score})")
        else:
            logger.warning(f"No good match found for ground truth column: {gt_col}")

    return matches


def validate_calculation_engine() -> Dict[str, Any]:
    """
    Validates the CalculationEngine against the ground truth data.

    Returns:
        Dictionary containing validation results and metrics
    """
    logger.info("=== Genomics Microcosting Engine Validation ===")
    start_time = time.time()

    results = {
        'timestamp': datetime.now().isoformat(),
        'success': False,
        'ground_truth_loaded': False,
        'engine_initialized': False,
        'engine_run': False,
        'validation_performed': False,
        'metrics': {},
        'errors': [],
        'column_matches': {},
        'validation_details': []
    }

    try:
        # Load ground truth data
        ground_truth_df = load_ground_truth()
        if ground_truth_df is None:
            results['errors'].append("Cannot proceed without ground truth data")
            return results

        results['ground_truth_loaded'] = True
        results['ground_truth_shape'] = ground_truth_df.shape

        # Find unit cost columns in ground truth
        gt_unit_cost_cols = find_unit_cost_columns(ground_truth_df)
        if not gt_unit_cost_cols:
            results['errors'].append("No unit cost columns found in ground truth data")
            return results

        # Initialize the CalculationEngine
        try:
            sheet_manager = SheetManager()
            engine = CalculationEngine(sheet_manager)
            logger.info("CalculationEngine initialized successfully")
            results['engine_initialized'] = True
        except Exception as e:
            results['errors'].append(f"Error initializing CalculationEngine: {e}")
            return results

        # Try to run the engine
        try:
            engine_start = time.time()
            results_df, errors = engine.run_engine("Detailed Table")
            engine_time = time.time() - engine_start

            results['engine_run'] = True
            results['engine_execution_time'] = engine_time

            if results_df is None:
                results['errors'].append("Engine returned None - no results to validate")
                if errors:
                    results['engine_errors'] = errors
                return results

            if errors:
                logger.warning("Warnings during calculation:")
                for error in errors:
                    logger.warning(f"  - {error}")
                results['engine_warnings'] = errors

        except Exception as e:
            results['errors'].append(f"Error running CalculationEngine: {e}")
            logger.error(f"Engine execution failed: {e}")
            return results

        logger.info(f"Engine results shape: {results_df.shape}")
        results['results_shape'] = results_df.shape

        # Find unit cost columns in results
        results_unit_cost_cols = find_unit_cost_columns(results_df)
        if not results_unit_cost_cols:
            results['errors'].append("No unit cost columns found in engine results")
            return results

        # Match columns
        column_matches = match_columns(gt_unit_cost_cols, results_unit_cost_cols)
        results['column_matches'] = column_matches

        if not column_matches:
            results['errors'].append("No column matches could be established")
            return results

        # Perform validation
        validation_results = perform_validation_parallel(ground_truth_df, results_df, column_matches)
        results['validation_details'] = validation_results
        results['validation_performed'] = True

        # Calculate summary metrics
        results['metrics'] = calculate_summary_metrics(validation_results)

        # Export results if configured
        if VALIDATION_CONFIG['export_results']:
            export_validation_results(results)

        results['success'] = True

    except Exception as e:
        results['errors'].append(f"Unexpected error during validation: {e}")
        logger.error(f"Validation failed with unexpected error: {e}")

    finally:
        total_time = time.time() - start_time
        results['total_execution_time'] = total_time
        logger.info(f"Validation completed in {total_time:.2f} seconds")

    return results


def perform_validation_parallel(gt_df: pd.DataFrame, res_df: pd.DataFrame,
                           column_matches: Dict[str, str]) -> List[Dict[str, Any]]:
    """Perform detailed validation on matched columns using parallel processing."""
    validation_results = []

    # Create data hash for caching
    gt_hash = create_dataframe_hash(gt_df)
    res_hash = create_dataframe_hash(res_df)
    data_hash = f"{gt_hash}_{res_hash}"

    # Check cache for entire validation result
    cache_key = get_cache_key(data_hash, "validation_results")
    cached_result = load_from_cache(cache_key)
    if cached_result:
        logger.info("Using cached validation results")
        return cached_result

    logger.info(f"Performing parallel validation on {len(column_matches)} column pairs")

    # Prepare column pairs for parallel processing
    column_pairs = [(gt_col, res_col) for gt_col, res_col in column_matches.items()]

    # Use ThreadPoolExecutor for I/O bound operations
    with concurrent.futures.ThreadPoolExecutor(max_workers=VALIDATION_CONFIG['max_workers']) as executor:
        # Submit all validation tasks
        future_to_pair = {
            executor.submit(compare_columns_optimized, gt_df, res_df, gt_col, res_col): (gt_col, res_col)
            for gt_col, res_col in column_pairs
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_pair):
            gt_col, res_col = future_to_pair[future]
            try:
                result = future.result()
                if result:
                    validation_results.append(result)
                    logger.info(f"Completed validation for {gt_col} vs {res_col}")
            except Exception as e:
                logger.error(f"Validation failed for {gt_col} vs {res_col}: {e}")

    # Cache the results
    save_to_cache(cache_key, validation_results)

    logger.info(f"Parallel validation completed: {len(validation_results)} successful comparisons")
    return validation_results


def compare_columns_optimized(gt_df: pd.DataFrame, res_df: pd.DataFrame,
                           gt_col: str, res_col: str) -> Optional[Dict[str, Any]]:
    """Optimized version of column comparison with better performance."""
    try:
        # Create cache key for this specific comparison
        gt_series = gt_df[gt_col]
        res_series = res_df[res_col]
        data_hash = hashlib.sha256(f"{gt_series.to_string()}_{res_series.to_string()}".encode()).hexdigest()
        cache_key = get_cache_key(data_hash, f"compare_{gt_col}_{res_col}")

        # Check cache first
        cached_result = load_from_cache(cache_key)
        if cached_result:
            return cached_result

        # Extract and clean the data using vectorized operations
        gt_numeric = pd.to_numeric(gt_series, errors='coerce')
        res_numeric = pd.to_numeric(res_series, errors='coerce')

        # Align the series by index if possible
        min_len = min(len(gt_numeric), len(res_numeric))
        gt_clean = gt_numeric.iloc[:min_len]
        res_clean = res_numeric.iloc[:min_len]

        # Find valid comparisons using vectorized operations
        valid_mask = gt_clean.notna() & res_clean.notna()
        comparisons = valid_mask.sum()

        if comparisons == 0:
            logger.warning(f"No valid comparisons possible between {gt_col} and {res_col}")
            return None

        gt_valid = gt_clean[valid_mask]
        res_valid = res_clean[valid_mask]

        # Vectorized calculations for better performance
        differences = gt_valid - res_valid
        abs_differences = differences.abs()

        # Handle percentage errors with vectorized operations
        percentage_errors = pd.Series(index=gt_valid.index, dtype=float)
        non_zero_mask = gt_valid != 0
        percentage_errors.loc[non_zero_mask] = (differences.loc[non_zero_mask] / gt_valid.loc[non_zero_mask]) * 100
        percentage_errors.loc[~non_zero_mask] = abs_differences.loc[~non_zero_mask]

        # Calculate metrics using numpy for better performance
        mean_abs_error = abs_differences.mean()
        finite_pct_errors = percentage_errors[np.isfinite(percentage_errors)]
        mean_percentage_error = finite_pct_errors.abs().mean() if len(finite_pct_errors) > 0 else float('inf')
        max_abs_error = abs_differences.max()
        max_percentage_error = finite_pct_errors.abs().max() if len(finite_pct_errors) > 0 else float('inf')

        # Count significant errors using vectorized operations
        significant_abs_errors = (abs_differences > VALIDATION_CONFIG['significant_error_threshold']).sum()
        significant_pct_errors = (finite_pct_errors.abs() > VALIDATION_CONFIG['percentage_error_threshold']).sum()

        # Calculate percentiles efficiently
        abs_error_percentiles = abs_differences.quantile([0.25, 0.5, 0.75, 0.95]).to_dict()
        if len(finite_pct_errors) > 0:
            pct_error_percentiles = finite_pct_errors.abs().quantile([0.25, 0.5, 0.75, 0.95]).to_dict()
        else:
            pct_error_percentiles = {'0.25': float('inf'), '0.5': float('inf'), '0.75': float('inf'), '0.95': float('inf')}

        result = {
            'gt_column': gt_col,
            'res_column': res_col,
            'comparisons': comparisons,
            'mean_abs_error': mean_abs_error,
            'mean_percentage_error': mean_percentage_error,
            'max_abs_error': max_abs_error,
            'max_percentage_error': max_percentage_error,
            'significant_abs_errors': significant_abs_errors,
            'significant_pct_errors': significant_pct_errors,
            'abs_error_percentiles': abs_error_percentiles,
            'pct_error_percentiles': pct_error_percentiles,
            'data_quality': {
                'gt_nulls': gt_series.isnull().sum(),
                'res_nulls': res_series.isnull().sum(),
                'gt_zeros': (gt_series == 0).sum(),
                'res_zeros': (res_series == 0).sum(),
                'valid_comparisons': comparisons,
                'gt_zeros_in_valid': (gt_valid == 0).sum(),
                'res_zeros_in_valid': (res_valid == 0).sum()
            }
        }

        # Cache the result
        save_to_cache(cache_key, result)

        return result

    except Exception as e:
        logger.error(f"Error comparing columns {gt_col} vs {res_col}: {e}")
        return None


def calculate_summary_metrics(validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary metrics from validation results."""
    if not validation_results:
        return {}

    total_comparisons = sum(r['comparisons'] for r in validation_results)
    significant_errors = sum(r['significant_abs_errors'] for r in validation_results)
    total_abs_error = sum(r['mean_abs_error'] * r['comparisons'] for r in validation_results)

    metrics = {
        'total_comparisons': total_comparisons,
        'significant_errors': significant_errors,
        'total_columns_validated': len(validation_results),
        'error_rate_percent': (significant_errors / total_comparisons * 100) if total_comparisons > 0 else 0,
        'weighted_mean_abs_error': (total_abs_error / total_comparisons) if total_comparisons > 0 else 0
    }

    return metrics


def export_validation_results(results: Dict[str, Any]) -> None:
    """Export validation results to files."""
    output_dir = Path(VALIDATION_CONFIG['output_dir'])
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Export summary as JSON
    summary_file = output_dir / f"validation_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Export detailed results as CSV if available
    if results.get('validation_details'):
        details_df = pd.DataFrame(results['validation_details'])
        details_file = output_dir / f"validation_details_{timestamp}.csv"
        details_df.to_csv(details_file, index=False)

    logger.info(f"Validation results exported to {output_dir}")


def compare_columns_detailed(gt_df: pd.DataFrame, res_df: pd.DataFrame,
                         gt_col: str, res_col: str) -> Optional[Dict[str, Any]]:
    """Compare two columns and calculate detailed validation metrics."""

    try:
        # Extract and clean the data
        gt_series = pd.to_numeric(gt_df[gt_col], errors='coerce')
        res_series = pd.to_numeric(res_df[res_col], errors='coerce')

        # Align the series by index if possible
        min_len = min(len(gt_series), len(res_series))
        gt_clean = gt_series.iloc[:min_len]
        res_clean = res_series.iloc[:min_len]

        # Find valid comparisons
        valid_mask = gt_clean.notna() & res_clean.notna()
        comparisons = valid_mask.sum()

        if comparisons == 0:
            logger.warning(f"No valid comparisons possible between {gt_col} and {res_col}")
            return None

        gt_valid = gt_clean[valid_mask]
        res_valid = res_clean[valid_mask]

        # Calculate metrics
        differences = gt_valid - res_valid
        abs_differences = differences.abs()
        
        # Handle percentage errors carefully to avoid division by zero
        # For zero ground truth values, use absolute difference as percentage error
        percentage_errors = pd.Series(index=gt_valid.index, dtype=float)
        non_zero_mask = gt_valid != 0
        percentage_errors[non_zero_mask] = (differences[non_zero_mask] / gt_valid[non_zero_mask]) * 100
        # For zero ground truth values, use absolute difference (can't divide by zero)
        percentage_errors[~non_zero_mask] = abs_differences[~non_zero_mask]

        mean_abs_error = abs_differences.mean()
        # Only calculate mean percentage error for non-infinite values
        finite_pct_errors = percentage_errors[np.isfinite(percentage_errors)]
        mean_percentage_error = finite_pct_errors.abs().mean() if len(finite_pct_errors) > 0 else float('inf')
        max_abs_error = abs_differences.max()
        max_percentage_error = finite_pct_errors.abs().max() if len(finite_pct_errors) > 0 else float('inf')

        # Count significant errors (only for finite percentage errors)
        significant_abs_errors = (abs_differences > VALIDATION_CONFIG['significant_error_threshold']).sum()
        significant_pct_errors = (finite_pct_errors.abs() > VALIDATION_CONFIG['percentage_error_threshold']).sum()

        # Calculate percentiles (only for finite values)
        abs_error_percentiles = abs_differences.quantile([0.25, 0.5, 0.75, 0.95]).to_dict()
        if len(finite_pct_errors) > 0:
            pct_error_percentiles = finite_pct_errors.abs().quantile([0.25, 0.5, 0.75, 0.95]).to_dict()
        else:
            pct_error_percentiles = {'0.25': float('inf'), '0.5': float('inf'), '0.75': float('inf'), '0.95': float('inf')}

        logger.info(f"  Valid comparisons: {comparisons}")
        logger.info(f"  Ground truth zeros: {(gt_valid == 0).sum()}")
        logger.info(f"  Results zeros: {(res_valid == 0).sum()}")
        logger.info(f"  Mean absolute error: {mean_abs_error:.6f}")
        logger.info(f"  Mean percentage error: {mean_percentage_error:.2f}%")
        logger.info(f"  Max absolute error: {max_abs_error:.6f}")
        logger.info(f"  Max percentage error: {max_percentage_error:.2f}%")
        logger.info(f"  Significant errors (abs > {VALIDATION_CONFIG['significant_error_threshold']}): {significant_abs_errors}")
        logger.info(f"  Significant errors (pct > {VALIDATION_CONFIG['percentage_error_threshold']}%): {significant_pct_errors}")

        return {
            'gt_column': gt_col,
            'res_column': res_col,
            'comparisons': comparisons,
            'mean_abs_error': mean_abs_error,
            'mean_percentage_error': mean_percentage_error,
            'max_abs_error': max_abs_error,
            'max_percentage_error': max_percentage_error,
            'significant_abs_errors': significant_abs_errors,
            'significant_pct_errors': significant_pct_errors,
            'abs_error_percentiles': abs_error_percentiles,
            'pct_error_percentiles': pct_error_percentiles,
            'data_quality': {
                'gt_nulls': gt_series.isnull().sum(),
                'res_nulls': res_series.isnull().sum(),
                'gt_zeros': (gt_series == 0).sum(),
                'res_zeros': (res_series == 0).sum(),
                'valid_comparisons': comparisons,
                'gt_zeros_in_valid': (gt_valid == 0).sum(),
                'res_zeros_in_valid': (res_valid == 0).sum()
            }
        }

    except Exception as e:
        logger.error(f"Error comparing columns {gt_col} vs {res_col}: {e}")
        return None


def main():
    """Main entry point."""
    results = validate_calculation_engine()

    # Print summary
    print("\n=== Validation Summary ===")
    if results['success']:
        metrics = results['metrics']
        print(f"✅ Validation completed successfully")
        print(f"Total comparisons: {metrics.get('total_comparisons', 0)}")
        print(f"Columns validated: {metrics.get('total_columns_validated', 0)}")
        print(f"Error rate: {metrics.get('error_rate_percent', 0):.2f}%")
        print(f"Mean absolute error: {metrics.get('weighted_mean_abs_error', 0):.6f}")
        print(f"Execution time: {results.get('total_execution_time', 0):.2f} seconds")
    else:
        print(f"❌ Validation failed")
        for error in results.get('errors', []):
            print(f"  - {error}")

    return results


if __name__ == "__main__":
    main()