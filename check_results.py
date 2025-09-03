from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.sheet_manager import SheetManager
import pandas as pd

def main():
    # Load the ground truth data
    ground_truth_path = "data/prepared/ground_truth.parquet"
    ground_truth_df = pd.read_parquet(ground_truth_path)
    
    print("Ground truth shape:", ground_truth_df.shape)
    print("Ground truth columns:", ground_truth_df.columns.tolist())
    
    # Initialize the CalculationEngine
    sheet_manager = SheetManager()
    engine = CalculationEngine(sheet_manager)

    # Run the engine to get the calculated results
    results_df, errors = engine.run_engine()
    
    print("Results shape:", results_df.shape)
    print("Results columns (first 10):", results_df.columns.tolist()[:10])
    
    # Find the unit cost column
    unit_cost_col = None
    for col in results_df.columns:
        if isinstance(col, tuple) and 'Unit Cost (AUD $/unit)' in str(col):
            unit_cost_col = col
            break
    
    print("Unit cost column:", unit_cost_col)
    if unit_cost_col:
        print("Unit cost data type:", type(results_df[unit_cost_col]))
        print("Unit cost shape:", results_df[unit_cost_col].shape)
        print("First 5 values:", results_df[unit_cost_col].head())

if __name__ == "__main__":
    main()