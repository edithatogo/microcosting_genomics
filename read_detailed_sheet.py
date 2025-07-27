"""Convert the detailed sheet to a long-format parquet file."""

from pathlib import Path
import pandas as pd

# Read the detailed sheet from the Excel file with a multi-level header
DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
df = pd.read_excel(
    DATA_DIR / 'Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm',
    sheet_name='1. Detailed Table',
    header=[0, 1],
)

# Flatten the multi-level column headers
df.columns = ['_ '.join(col).strip() for col in df.columns.values]

# Melt the dataframe to long format
df_long = df.melt(id_vars=[col for col in df.columns if 'Unnamed' in col], var_name='variable', value_name='value')

# Convert the 'value' column to string type
df_long['value'] = df_long['value'].astype(str)

# Save the long format dataframe to a parquet file
df_long.to_parquet(DATA_DIR / 'detailed_table.parquet')

print('Successfully converted the detailed table to a long format parquet file.')
