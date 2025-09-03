#!/usr/bin/env python3
"""
Script to prepare translated tables for publication with metadata.
"""

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.config import load_config


def create_table_metadata(df, table_name, description=""):
    """Create metadata for a table.
    
    Args:
        df (pd.DataFrame): The DataFrame containing the table data
        table_name (str): Name of the table
        description (str): Description of the table
        
    Returns:
        dict: Metadata dictionary
    """
    metadata = {
        "table_name": table_name,
        "description": description,
        "created_date": datetime.now().isoformat(),
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": []
    }
    
    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
        }
        
        # Add unique count for categorical columns
        if df[col].dtype == 'object':
            col_info["unique_count"] = int(df[col].nunique())
            # Add sample values for context
            sample_values = df[col].dropna().unique()[:5].tolist()
            col_info["sample_values"] = sample_values
        
        metadata["columns"].append(col_info)
    
    return metadata


def prepare_publication_tables():
    """Prepare all tables for publication with metadata."""
    print("Preparing tables for publication...")
    
    try:
        # Load configuration
        config = load_config()
        print("Configuration loaded successfully")
        
        # Define paths
        data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        publication_dir = Path(__file__).resolve().parents[1] / "publication"
        publication_dir.mkdir(exist_ok=True)
        
        print(f"Looking for prepared data in {data_dir}")
        
        # Process all parquet files
        parquet_files = list(data_dir.glob("*.parquet"))
        print(f"Found {len(parquet_files)} parquet files")
        
        processed_count = 0
        
        for parquet_file in parquet_files:
            table_name = parquet_file.stem
            print(f"Processing {table_name}...")
            
            try:
                # Load the data
                df = pd.read_parquet(parquet_file)
                print(f"  Loaded {len(df)} rows and {len(df.columns)} columns")
                
                # Save as CSV for publication
                csv_file = publication_dir / f"{table_name}.csv"
                df.to_csv(csv_file, index=False)
                print(f"  Saved CSV to {csv_file}")
                
                # Create metadata
                description = f"Translated table from Excel workbook: {table_name}"
                metadata = create_table_metadata(df, table_name, description)
                
                # Save metadata as JSON
                metadata_file = publication_dir / f"{table_name}_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                print(f"  Saved metadata to {metadata_file}")
                
                processed_count += 1
                
            except Exception as e:
                print(f"  Error processing {table_name}: {e}")
                continue
        
        print(f"\nSuccessfully prepared {processed_count} tables for publication")
        print(f"Publication files saved to {publication_dir}")
        
        # Create a README for the publication directory
        readme_content = f"""# Publication Tables

This directory contains the translated tables from the Excel workbook prepared for publication.

## Contents

- CSV files: The translated tables in CSV format for easy use outside Excel
- JSON metadata files: Metadata for each table including column information and data types

## Processing Information

- Processed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Source data directory: {data_dir}
- Number of tables processed: {processed_count}

## Table Descriptions

"""
        
        # Add table descriptions to README
        for parquet_file in parquet_files:
            table_name = parquet_file.stem
            readme_content += f"- {table_name}.csv: Translated table from Excel\n"
        
        readme_content += "\n## Usage\n\nThese tables can be used for research, analysis, and reporting on microcosting for rare disease genomics.\n"
        
        readme_file = publication_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        print(f"Created README.md in {publication_dir}")
        
        return 0
        
    except Exception as e:
        print(f"Error preparing publication tables: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main function."""
    return prepare_publication_tables()


if __name__ == "__main__":
    sys.exit(main())