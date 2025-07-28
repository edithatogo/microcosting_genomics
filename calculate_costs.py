"""Calculate costs using prepared input tables.

Data files are expected in the repository ``data`` directory located at
``Path(__file__).resolve().parents[0] / 'data'``.
"""

from pathlib import Path
import pandas as pd

# Load the data
DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
detailed_table = pd.read_parquet(DATA_DIR / 'detailed_table.parquet')
supp_wb = DATA_DIR / 'Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm'
labor_prices = pd.read_excel(supp_wb, sheet_name='2. Labor Prices')
equipment_throughput = pd.read_excel(supp_wb, sheet_name='4. DSA - Equipment Throughput')
overheads = pd.read_excel(supp_wb, sheet_name='5. DSA - Overheads')
consumable_discounts = pd.read_excel(supp_wb, sheet_name='6. DSA - Consumable Discounts')

# Clean the column names
detailed_table.columns = detailed_table.columns.str.replace(r'Unnamed: \d+_level_\d', '', regex=True)
detailed_table.columns = detailed_table.columns.str.strip()

# Calculate Labour Costs
# This is a simplified example, and the actual logic will be more complex
# and will need to parse the formulas from the excel sheet.

# For now, I will just print a message indicating that the next step is to
# implement the formula parsing logic.

print('Next step: Implement formula parsing and calculation logic.')
