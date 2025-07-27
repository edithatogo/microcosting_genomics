import pandas as pd
from pathlib import Path
from unimelb_phd_phase_1.calculation_engine import CalculationEngine


def validate_simple_tables() -> None:
    """Validate simple reference tables using CalculationEngine."""
    engine = CalculationEngine()

    data_dir = Path(__file__).resolve().parents[0] / "data" / "prepared"
    tables = {
        "2. Labor Prices": data_dir / "2._labor_prices.parquet",
        "3. Estimates": data_dir / "3._estimates.parquet",
    }

    for sheet_name, parquet_path in tables.items():
        print(f"\n--- Validating {sheet_name} ---")
        ground_truth = pd.read_parquet(parquet_path)

        results, errors = engine.run_engine(sheet_name, fail_on_error=False)
        if errors:
            print("Errors while computing formulas:")
            for e in errors:
                print(e)

        gt_aligned, res_aligned = ground_truth.align(results, join="inner", axis=1)
        diff = (gt_aligned - res_aligned).abs()

        print(f"Total cells compared: {diff.size}")
        print(f"Number of differences: {(diff > 1e-6).sum().sum()}")
        print(f"Maximum absolute difference: {diff.max().max()}")
        print(f"Mean absolute difference: {diff.mean().mean()}")


if __name__ == "__main__":
    validate_simple_tables()
