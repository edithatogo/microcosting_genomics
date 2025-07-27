"""Read all sheets from the supplementary workbook into a dictionary."""

from pathlib import Path
import pandas as pd

# Define the file path
DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
file_path = DATA_DIR / 'Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm'

# Read all sheets into a dictionary of dataframes
dfs = pd.read_excel(file_path, sheet_name=None)

# Print the names of the dataframes
print(dfs.keys())
