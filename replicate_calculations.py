import pandas as pd
import openpyxl
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.formula_parser import parse_formula

def main():
    """
    This script replicates the calculations from the 'Detailed Table' sheet of the microcosting
    Excel file and compares them against the original values.
    """
    print("Starting calculation replication...")

    # Initialize the calculation engine
    engine = CalculationEngine()
    sheet_name = 'Detailed Table'

    # Load the ground truth data for comparison
    ground_truth_df = pd.read_parquet('data/prepared/ground_truth.parquet')

    # Find the column index for the 'Unit Cost' estimate from the cleaned headers
    unit_cost_col_name = 'Estimates Estimate_3'
    try:
        unit_cost_col_idx = ground_truth_df.columns.get_loc(unit_cost_col_name)
    except KeyError:
        print(f"Error: The ground truth data does not have the expected column: {unit_cost_col_name}")
        return

    calculated_results = []
    # Iterate through each row of our ground truth data
    for index, row in ground_truth_df.iterrows():
        # The Excel row is the DataFrame index + 3 (1-based index, plus 2 header rows)
        excel_row = index + 3
        
        # The Excel column is the DataFrame column index + 1 (1-based index)
        excel_col_letter = openpyxl.utils.get_column_letter(unit_cost_col_idx + 1)
        
        cell_ref = f"{excel_col_letter}{excel_row}"

        # Get the formula from the raw excel file using our engine's method
        formula = engine.get_cell_formula(sheet_name, cell_ref)

        if isinstance(formula, str) and formula.startswith('='):
            # If we have a formula, execute it
            parsed_formula = parse_formula(formula)
            if parsed_formula['type'] == 'unknown':
                print(f"Unknown formula: {formula}")
                calculated_value = "UNSUPPORTED"
            else:
                calculated_value = engine.execute_formula(parsed_formula, sheet_name, cell_ref)
        else:
            # If there's no formula, the value is just the value
            calculated_value = formula

        calculated_results.append(calculated_value)

    # Add the results to the DataFrame for comparison
    ground_truth_df['Calculated_Value'] = calculated_results

    print("\nReplication Results (Original vs. Calculated):")
    print(ground_truth_df[[unit_cost_col_name, 'Calculated_Value']])

if __name__ == "__main__":
    main()
