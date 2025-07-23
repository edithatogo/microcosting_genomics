import pandas as pd

def find_formula():
    """
    Finds a simple multiplication formula in the detailed_table_formulas.parquet file.
    A simple formula is defined as one that contains a '*' and does not contain a '['.
    """
    df = pd.read_parquet('data/prepared/detailed_table_formulas.parquet')
    for col_name in df.columns:
        for i, cell_value in df[col_name].items():
            if isinstance(cell_value, str) and '*' in cell_value and '[' not in cell_value:
                print(f"Found simple formula at row {i}, column '{col_name}': {cell_value}")
                return

if __name__ == '__main__':
    find_formula()
