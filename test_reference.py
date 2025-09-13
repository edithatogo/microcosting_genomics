#!/usr/bin/env python3
"""Test cross-sheet reference resolution."""

import openpyxl
import re

# Load workbook
wb = openpyxl.load_workbook('data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm', data_only=True)

# Test resolving a specific reference
formula = "='Labour - Usage - VCGS'!C5"
print(f'Testing formula: {formula}')

# Match pattern
pattern = r"'([^']+)'!([A-Z]+)(\d+)"
match = re.match(pattern, formula.strip())

if match:
    sheet_name, col_letter, row_num = match.groups()
    print(f'Sheet: {sheet_name}')
    print(f'Column: {col_letter}')
    print(f'Row: {row_num}')

    # Get the sheet
    ws = wb[sheet_name]

    # Convert column letter to index
    col_index = 0
    for char in col_letter.upper():
        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
    col_index -= 1

    print(f'Column index: {col_index}')

    # Get the value
    row_index = int(row_num) - 1
    print(f'Row index: {row_index}')

    # Get all data from the sheet first
    data = []
    for row in ws.iter_rows(values_only=True):
        data.append(row)

    import pandas as pd
    df = pd.DataFrame(data)
    print(f'Sheet shape: {df.shape}')

    if row_index < len(df) and col_index < len(df.columns):
        value = df.iloc[row_index, col_index]
        print(f'Value at [{row_index}, {col_index}]: {value}')
        print(f'Value type: {type(value)}')
    else:
        print(f'Index out of bounds: row {row_index}/{len(df)}, col {col_index}/{len(df.columns)}')
else:
    print('No match found')
