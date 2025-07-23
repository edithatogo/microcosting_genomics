import pandas as pd

# Define the file path
file_path = '/home/doughnut/github/unimelb-phd-phase_1/data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx'

# Read all sheets into a dictionary of dataframes
dfs = pd.read_excel(file_path, sheet_name=None)

# Print the names of the dataframes
print(dfs.keys())
