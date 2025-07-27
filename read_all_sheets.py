"""Read all sheets from the supplementary workbook into a dictionary."""

from pathlib import Path
import pandas as pd

# Define the file path
DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
file_path = DATA_DIR / 'Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx'

# Read all sheets into a dictionary of dataframes
dfs = pd.read_excel(file_path, sheet_name=None)

# Print the names of the dataframes
print(dfs.keys())
