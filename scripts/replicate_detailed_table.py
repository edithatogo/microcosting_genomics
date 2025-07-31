
"""Replicate the detailed table calculations using extracted CSV files."""

from pathlib import Path
import pandas as pd
import numpy as np

# The data directory lives at the repository root under ``data/extracted``.
# ``parents[1]`` points one level above ``scripts`` (the repo root).
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "extracted"

# Load the Detailed Table data
df_detailed = pd.read_csv(DATA_DIR / 'Detailed Table_values.csv', header=2)
df_detailed.dropna(how='all', inplace=True)
df_detailed.reset_index(drop=True, inplace=True)

# Clean up detailed table column names
detailed_columns = [
    'Test', 'Category', 'Sub-Category', 'Step',
    'Quantity LL', 'Quantity Estimate', 'Quantity UL', 'Quantity Source',
    'Price LL', 'Price Estimate', 'Price UL', 'Price Source',
    'Unit Cost LL', 'Unit Cost Estimate', 'Unit Cost UL',
    'DSA Price LL', 'DSA Price Estimate', 'DSA Price UL',
    'DSA Unit Cost LL', 'DSA Unit Cost Estimate', 'DSA Unit Cost UL',
    'VIC Cost LL', 'VIC Cost Estimate', 'VIC Cost UL',
    'SA Cost LL', 'SA Cost Estimate', 'SA Cost UL'
]
df_detailed.columns = detailed_columns[:len(df_detailed.columns)]


# Load the Labour Costs data
df_labour = pd.read_csv(DATA_DIR / 'Labour - Costs - VCGS_values.csv', header=1)
df_labour.dropna(how='all', inplace=True)
df_labour.reset_index(drop=True, inplace=True)

# Clean up labour costs column names
labour_columns = [
    'Jurisdiction', 'Personnel type', 'Label', 'Award', 'Grade(s)',
    'Distribution desc', 'References', 'Rate of Pay (weekly, 38h) desc',
    'Year', 'Superannuation Rate (%)', 'Hours per week', 'Average productive time (%)',
    'Average Penalties %', 'Public Holiday Penalty Percentage', 'Private Practice Loading',
    'Attraction and Retention Allowance', 'Sick Leave Percentage',
    'Professional Development Allowance', 'Annual Leave Entitlement (Weeks)',
    'Annual Leave Loading (%)', 'Indexation per annum (%)',
    'Base Salary LL', 'Base Salary Mid-point', 'Base Salary UL',
    'Base Salary + Costs LL', 'Base Salary + Costs Mid-point', 'Base Salary + Costs UL',
    'Base Salary + Costs (hourly) LL', 'Base Salary + Costs (hourly) Mid-point',
    'Base Salary + Costs (hourly) UL'
]
df_labour.columns = labour_columns

# Load the mapping
df_mapping = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "step_to_label_mapping.csv")

# Merge the mapping with the detailed table
df_detailed = pd.merge(df_detailed, df_mapping, on='Step', how='left')

# Now, let's get the first calculation right
# We'll focus on the 'Registration' step
registration_step = df_detailed[df_detailed['Step'] == 'Registration'].iloc[0]
registration_label = registration_step['Label']
labour_row = df_labour[(df_labour['Label'] == registration_label) & (df_labour['Jurisdiction'] == 'VIC')].iloc[0]

# Replicate the 'Price Estimate' calculation
# This should be 'Base Salary + Costs (hourly) Mid-point'
calculated_price = labour_row['Base Salary + Costs (hourly) Mid-point']
original_price = registration_step['Price Estimate']

print(f"For step 'Registration':")
print(f"  - Mapped Label: {registration_label}")
print(f"  - Calculated Price Estimate: {calculated_price}")
print(f"  - Original Price Estimate: {original_price}")

# Replicate the 'Unit Cost Estimate'
# This is 'Quantity Estimate' * 'Price Estimate'
calculated_unit_cost = registration_step['Quantity Estimate'] * calculated_price
original_unit_cost = registration_step['Unit Cost Estimate']

print(f"\nFor step 'Registration':")
print(f"  - Calculated Unit Cost Estimate: {calculated_unit_cost}")
print(f"  - Original Unit Cost Estimate: {original_unit_cost}")
