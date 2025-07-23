import pandas as pd

# Read the detailed sheet from the Excel file with a multi-level header
df = pd.read_excel('/home/doughnut/github/unimelb-phd-phase_1/data/Microcosting Study - Supp Tables - R1 v1 (20231119).xlsx', sheet_name='1. Detailed Table', header=[0, 1])

# Flatten the multi-level column headers
df.columns = ['_ '.join(col).strip() for col in df.columns.values]

# Melt the dataframe to long format
df_long = df.melt(id_vars=[col for col in df.columns if 'Unnamed' in col], var_name='variable', value_name='value')

# Convert the 'value' column to string type
df_long['value'] = df_long['value'].astype(str)

# Save the long format dataframe to a parquet file
df_long.to_parquet('/home/doughnut/github/unimelb-phd-phase_1/data/detailed_table.parquet')

print('Successfully converted the detailed table to a long format parquet file.')