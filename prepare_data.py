import pandas as pd
import numpy as np

def create_unique_column_names(columns):
    """
    Given a list of column names, ensures each name is unique by appending a suffix if needed.
    """
    seen = {}
    unique_columns = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            unique_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 1
            unique_columns.append(col)
    return unique_columns

def main():
    """
    This main function orchestrates the process of reading a complex Excel file,
    cleaning its headers, and saving the processed data to a Parquet file.
    """
    source_file = 'data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm'
    sheet_name = 'Detailed Table'
    output_file = 'data/prepared/ground_truth.parquet'

    print(f"Preparing ground truth data from {source_file}...")

    # 1. Read the header rows separately
    header_df = pd.read_excel(source_file, sheet_name=sheet_name, header=None, nrows=3)

    # 2. Construct the new column names manually and robustly
    # Forward fill the first row to handle merged cells
    header_df.iloc[0] = header_df.iloc[0].ffill()
    
    new_columns = []
    for i in range(header_df.shape[1]):
        # Combine row 0 and 1 for the main part of the header
        h1 = str(header_df.iloc[0, i]) if pd.notna(header_df.iloc[0, i]) else ''
        h2 = str(header_df.iloc[1, i]) if pd.notna(header_df.iloc[1, i]) else ''
        
        # The third row is a sub-header
        h3 = str(header_df.iloc[2, i]) if pd.notna(header_df.iloc[2, i]) else ''

        # Combine them, cleaning up extra spaces
        full_header = f"{h1} {h2} {h3}".replace('nan', '').strip()
        full_header = ' '.join(full_header.split()) # Consolidate whitespace
        
        if not full_header:
            full_header = f"unnamed_{i}"
            
        new_columns.append(full_header)

    # 3. Ensure all column names are unique
    unique_columns = create_unique_column_names(new_columns)

    # 4. Read the data, skipping the header rows, and assign the new column names
    df = pd.read_excel(source_file, sheet_name=sheet_name, header=None, skiprows=3)
    df.columns = unique_columns

    # 5. Coerce all columns to numeric where possible
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 6. Save the cleaned DataFrame
    df.to_parquet(output_file)

    print(f"Ground truth data has been prepared and saved to {output_file}")


if __name__ == "__main__":
    main()
