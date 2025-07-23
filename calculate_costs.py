import pandas as pd

# Load the data
detailed_table = pd.read_parquet('/home/doughnut/github/unimelb-phd-phase_1/data/detailed_table.parquet')
labor_prices = pd.read_excel('/home/doughnut/github/unimelb-phd-phase_1/data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx', sheet_name='2. Labor Prices')
equipment_throughput = pd.read_excel('/home/doughnut/github/unimelb-phd-phase_1/data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx', sheet_name='4. DSA - Equipment Throughput')
overheads = pd.read_excel('/home/doughnut/github/unimelb-phd-phase_1/data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx', sheet_name='5. DSA - Overheads')
consumable_discounts = pd.read_excel('/home/doughnut/github/unimelb-phd-phase_1/data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx', sheet_name='6. DSA - Consumable Discounts')

# Clean the column names
detailed_table.columns = detailed_table.columns.str.replace(r'Unnamed: \d+_level_\d', '', regex=True)
detailed_table.columns = detailed_table.columns.str.strip()

# Calculate Labour Costs
# This is a simplified example, and the actual logic will be more complex
# and will need to parse the formulas from the excel sheet.

# For now, I will just print a message indicating that the next step is to
# implement the formula parsing logic.

print('Next step: Implement formula parsing and calculation logic.')
