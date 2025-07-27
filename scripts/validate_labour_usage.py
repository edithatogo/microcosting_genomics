
import pandas as pd
from unimelb_phd_phase_1.calculation_engine import CalculationEngine

def validate_sheet(sheet_name):
    """
    Validates the calculation engine's output for a specific sheet against the ground truth.
    """
    print(f"--- Validating Sheet: {sheet_name} ---")
    
    # Initialize the engine
    engine = CalculationEngine()

    # Get the ground truth values from the original Excel file
    ground_truth_df = engine.get_ground_truth(sheet_name)
    if ground_truth_df is None:
        print(f"Could not load ground truth for sheet: {sheet_name}")
        return

    # Run the engine to calculate the values
    calculated_df = engine.run_engine(sheet_name)
    if calculated_df is None:
        print(f"Engine failed to run on sheet: {sheet_name}")
        return

    # Compare the results
    discrepancies = []
    for r_idx in range(ground_truth_df.shape[0]):
        for c_idx in range(ground_truth_df.shape[1]):
            excel_value = ground_truth_df.iloc[r_idx, c_idx]
            calculated_value = calculated_df.iloc[r_idx, c_idx]
            
            # Simple comparison, can be improved for float tolerance
            if str(excel_value) != str(calculated_value):
                formula = engine.get_cell_formula(sheet_name, f"{chr(ord('A')+c_idx)}{r_idx+1}")
                discrepancies.append({
                    'cell': f"{chr(ord('A')+c_idx)}{r_idx+1}",
                    'formula': formula,
                    'excel_value': excel_value,
                    'calculated_value': calculated_value
                })

    if discrepancies:
        print("Discrepancies found:")
        for d in discrepancies:
            print(d)
    else:
        print(f"Success! No discrepancies found for sheet: {sheet_name}")

if __name__ == "__main__":
    validate_sheet('Labour - Usage - VCGS')
