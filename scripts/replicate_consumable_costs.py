"""Replicate the consumable cost calculations from the extracted CSV."""

from pathlib import Path
import pandas as pd
import numpy as np

# Load the data, reading all as string initially
DATA_DIR = Path(__file__).resolve().parents[0] / 'data' / 'extracted'
df = pd.read_csv(DATA_DIR / 'Cons -  Costs and Util - VCGS_values.csv', header=2, dtype=str)

# Drop empty rows
df.dropna(how='all', inplace=True)
df.reset_index(drop=True, inplace=True)

# A bit of cleaning of column names
df.columns = [
    'Stage', 'Step', 'Details', 'Consumables', 'Unit Cost', 'Units per',
    '50x (WES)', '80x (WES)', '30x (WGS)', 'Other', '50x', '80x', '30x',
    'Comments', 'Source', 'Reagent Discounts (30%)', 'Reagent Discounts (70%)'
]


# Convert relevant columns to numeric
numeric_cols = ['Unit Cost', 'Units per', '50x (WES)', '80x (WES)', '30x (WGS)', 'Other', '50x', '80x', '30x']
for col in numeric_cols:
    if df[col].dtype == 'object':
        df[col] = df[col].str.replace(r'[^0-9.-]', '', regex=True)
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Replicate the simple calculation for 'Other' column: =E5*F5
# E is 'Unit Cost', F is 'Units per'
df['Calculated Other'] = df['Unit Cost'] * df['Units per']

# Replicate the '50x', '80x', and '30x' calculations
# Formula for '50x' is =E62*F62*G62
# E is 'Unit Cost', F is 'Units per', G is '50x (WES)'
df['Calculated 50x'] = df['Unit Cost'] * df['Units per'] * df['50x (WES)']
df['Calculated 80x'] = df['Unit Cost'] * df['Units per'] * df['80x (WES)']
df['Calculated 30x'] = df['Unit Cost'] * df['Units per'] * df['30x (WGS)']


# Display the first few rows of the cleaned data and calculations
print("Cleaned Data and Initial Calculations:")
print(df[[
    'Consumables', 'Unit Cost', 'Units per', 'Other', 'Calculated Other',
    '50x (WES)', '50x', 'Calculated 50x',
    '80x (WES)', '80x', 'Calculated 80x',
    '30x (WGS)', '30x', 'Calculated 30x'
]].head())
