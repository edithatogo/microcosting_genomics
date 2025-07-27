import pandas as pd
import openpyxl
from unimelb_phd_phase_1.calculation_engine import CalculationEngine
from unimelb_phd_phase_1.formula_parser import parse_formula

def main():
    """
    This script replicates the calculations from the 'Detailed Table' sheet of the microcosting
    Excel file and saves the results to a parquet file.
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

    results_data = []
    # Iterate through each row of our ground truth data
    for index, row in ground_truth_df.iterrows():
        # The Excel row is the DataFrame index + 3 (1-based index, plus 2 header rows)
        excel_row = index + 3
        
        # The Excel column is the DataFrame column index + 1 (1-based index)
        excel_col_letter = openpyxl.utils.get_column_letter(unit_cost_col_idx + 1)
        
        cell_ref = f"{excel_col_letter}{excel_row}"

        # Get the formula from the raw excel file using our engine's method
        formula = engine.get_cell_formula(sheet_name, cell_ref)

        calculated_value = 0
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

        cost_category = row.get('Cost_Category', 'Unknown')
        
        result_row = {
            'Test_Type': row.get('Test_Type', ''),
            'Cost_Category': cost_category,
            'Cost_Sub_Category': row.get('Cost_Sub_Category', ''),
            'Cost_Step': row.get('Cost_Step', ''),
            'unit_cost_labour': 0,
            'unit_cost_equipment': 0,
            'unit_cost_consumables': 0
        }

        if cost_category == 'Labour':
            result_row['unit_cost_labour'] = calculated_value
        elif cost_category == 'Equipment':
            result_row['unit_cost_equipment'] = calculated_value
        elif cost_category == 'Consumables':
            result_row['unit_cost_consumables'] = calculated_value
            
        results_data.append(result_row)

    # Create a DataFrame from the results
    calculated_df = pd.DataFrame(results_data)

    # Save the calculated costs to a parquet file
    calculated_df.to_parquet('data/calculated_costs_tidy.parquet', index=False)

    print("\nCalculations replicated and saved to 'data/calculated_costs_tidy.parquet'.")

if __name__ == "__main__":
    main()

