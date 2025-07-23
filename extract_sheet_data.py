import openpyxl
import csv
import os
from openpyxl.cell import MergedCell

# Define the output directory
output_dir = '/home/doughnut/github/unimelb-phd-phase-1/data/extracted'
os.makedirs(output_dir, exist_ok=True)

# Load the workbook to get formulas
workbook = openpyxl.load_workbook('/home/doughnut/github/unimelb-phd-phase-1/data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm', data_only=False)

# Select the sheet
sheet_name = 'Detailed Table'
sheet = workbook[sheet_name]

# Define file paths
values_file_path = os.path.join(output_dir, f'{sheet_name}_values.csv')
formulas_file_path = os.path.join(output_dir, f'{sheet_name}_formulas.csv')

# Extract formulas
with open(formulas_file_path, 'w', newline="") as f:
    c = csv.writer(f)
    for row in sheet.rows:
        row_data = []
        for cell in row:
            if isinstance(cell, MergedCell):
                row_data.append('')  # Write empty string for merged cells
            else:
                row_data.append(cell.value)
        c.writerow(row_data)

# Now get values by loading with data_only=True
workbook_values = openpyxl.load_workbook('/home/doughnut/github/unimelb-phd-phase-1/data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm', data_only=True)
sheet_values = workbook_values[sheet_name]

# Extract values
with open(values_file_path, 'w', newline="") as f:
    c = csv.writer(f)
    for row in sheet_values.rows:
        row_data = []
        for cell in row:
            if isinstance(cell, MergedCell):
                row_data.append('')  # Write empty string for merged cells
            else:
                row_data.append(cell.value)
        c.writerow(row_data)

print(f"Extracted values to {values_file_path}")
print(f"Extracted formulas to {formulas_file_path}")