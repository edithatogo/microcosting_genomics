

import pandas as pd

# Load the Detailed Table data
detailed_table_path = '/home/doughnut/github/unimelb-phd-phase-1/data/extracted/Detailed Table_values.csv'
df_detailed = pd.read_csv(detailed_table_path, header=2)
df_detailed.dropna(how='all', inplace=True)
df_detailed.reset_index(drop=True)

# Load the Labour Costs data
labour_costs_path = '/home/doughnut/github/unimelb-phd-phase-1/data/extracted/Labour - Costs - VCGS_values.csv'
df_labour = pd.read_csv(labour_costs_path, header=1)
df_labour.dropna(how='all', inplace=True)
df_labour.reset_index(drop=True)

# Clean up column names
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


# Get unique values
detailed_steps = df_detailed['Step'].unique()
labour_labels = df_labour['Label'].unique()

print("Unique Steps in Detailed Table:")
for step in detailed_steps:
    print(f"- {step}")

print("\nUnique Labels in Labour Costs:")
for label in labour_labels:
    print(f"- {label}")

