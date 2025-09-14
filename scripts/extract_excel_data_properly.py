#!/usr/bin/env python3
"""
Proper Excel Data Extraction with Calculated Values

This script extracts data from the Excel workbook preserving all calculated values
instead of formulas, addressing the critical data integrity issue.
"""

import openpyxl
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExcelDataExtractor:
    """Extracts calculated values from Excel workbook."""

    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)
        self.wb = None

    def load_workbook(self, data_only: bool = True):
        """Load Excel workbook with calculated values."""
        logger.info(f"Loading Excel workbook: {self.excel_path}")
        self.wb = openpyxl.load_workbook(self.excel_path, data_only=data_only)
        logger.info(f"Loaded {len(self.wb.sheetnames)} sheets")

    def extract_labour_usage_data(self) -> pd.DataFrame:
        """Extract labour usage data with calculated values."""
        if self.wb is None:
            self.load_workbook()

        ws = self.wb['Labour - Usage - VCGS']

        # Convert to pandas DataFrame
        data = []
        for row in ws.iter_rows(values_only=True):
            data.append(row)

        df = pd.DataFrame(data)

        # Clean up the data - skip header rows
        df_clean = df.iloc[3:].reset_index(drop=True)  # Skip first 3 rows (headers)

        # Set proper column names from row 0 (after skipping headers)
        column_names = []
        header_row = df.iloc[2]  # Row 2 contains the actual headers
        for col_name in header_row:
            if col_name is None or str(col_name).strip() == '':
                column_names.append(f"Unnamed_{len(column_names)}")
            else:
                column_names.append(str(col_name).strip())

        df_clean.columns = column_names

        # Convert numeric columns
        for col in df_clean.columns:
            try:
                # Try to convert to numeric
                numeric_series = pd.to_numeric(df_clean[col], errors='coerce')
                if numeric_series.notna().sum() > 0:  # If we have numeric data
                    df_clean[col] = numeric_series
            except (ValueError, TypeError):
                pass  # Keep as object if conversion fails

        logger.info(f"Extracted Labour Usage data: {df_clean.shape}")
        return df_clean

    def split_by_test_type(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Split the detailed table by test type (Panel, WES, WGS)."""
        test_types = {}

        # Get unique test types
        unique_tests = df['Test'].dropna().unique()
        logger.info(f"Found test types: {list(unique_tests)}")

        for test_type in unique_tests:
            if pd.isna(test_type):
                continue

            # Filter data for this test type
            test_df = df[df['Test'] == test_type].copy()

            # Clean up empty rows
            test_df = test_df.dropna(how='all')

            # Map to our model naming convention
            model_name = self.map_test_type_to_model(test_type)
            test_types[model_name] = test_df

            logger.info(f"Extracted {model_name}: {test_df.shape}")

        return test_types

    def map_test_type_to_model(self, test_type: str) -> str:
        """Map Excel test type to our model naming convention."""
        test_type = str(test_type).lower()

        if 'panel' in test_type:
            return 'Panel'
        elif 'wes' in test_type and 'p' in test_type:
            return 'WES (P)'
        elif 'wes' in test_type and 't' in test_type:
            return 'WES (T)'
        elif 'wgs' in test_type and 'p' in test_type:
            return 'WGS (P)'
        elif 'wgs' in test_type and 't' in test_type:
            return 'WGS (T)'
        else:
            return str(test_type).title()

    def standardize_columns(self, df: pd.DataFrame, model_name: str) -> pd.DataFrame:
        """Standardize column names to match template requirements."""
        # Define column mapping
        column_mapping = {
            'Test': 'Test',
            'Category': 'Category',
            'Sub-Category': 'Sub-Category',
            'Step': 'Item',  # Map Step to Item
            'Quantity of Use per Test': 'Units',
            'Price (AUD $/unit)': 'Unit Cost (AUD $/unit)',
            'Unit Cost (AUD $/unit)': 'Unit Cost (AUD $/unit)',
        }

        # Rename columns
        df_renamed = df.rename(columns=column_mapping)

        # Add missing required columns with default values
        required_columns = [
            'Test', 'Category', 'Sub-Category', 'Item', 'Unit Cost (AUD $/unit)',
            'Units', 'Total Cost (AUD)', 'Notes', 'Supplier', 'Catalogue Number',
            'Batch/Lot Number', 'Expiry Date', 'Storage Conditions', 'Quality Control',
            'References'
        ]

        for col in required_columns:
            if col not in df_renamed.columns:
                if col == 'Test':
                    df_renamed[col] = model_name
                elif col in ['Unit Cost (AUD $/unit)', 'Units', 'Total Cost (AUD)']:
                    df_renamed[col] = 0.0
                else:
                    df_renamed[col] = ''

        # Calculate Total Cost if Unit Cost and Units are available
        if 'Unit Cost (AUD $/unit)' in df_renamed.columns and 'Units' in df_renamed.columns:
            try:
                unit_cost_numeric = pd.to_numeric(df_renamed['Unit Cost (AUD $/unit)'], errors='coerce')
                units_numeric = pd.to_numeric(df_renamed['Units'], errors='coerce')
                df_renamed['Total Cost (AUD)'] = unit_cost_numeric * units_numeric
            except Exception as e:
                logger.warning(f"Could not calculate Total Cost: {e}")
                df_renamed['Total Cost (AUD)'] = 0.0

        # Reorder columns to match template
        df_ordered = df_renamed[required_columns]

        return df_ordered

    def save_extracted_data(self, test_data: Dict[str, pd.DataFrame], output_dir: str = "data/extracted_correct"):
        """Save extracted data to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for model_name, df in test_data.items():
            filename = f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}_extracted.csv"
            filepath = output_path / filename

            df.to_csv(filepath, index=False)
            logger.info(f"Saved {model_name} to {filepath}")

    def validate_extracted_data(self, test_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """Validate that extracted data has meaningful numeric values."""
        validation_results = {}

        for model_name, df in test_data.items():
            # Check for numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            total_numeric = len(numeric_cols)

            # Check for non-zero values
            meaningful_data = 0
            total_rows = len(df)

            for col in numeric_cols:
                try:
                    non_zero_count = int((df[col].notna() & (df[col] != 0)).sum())
                    if non_zero_count > 0:
                        meaningful_data += 1
                except (TypeError, AttributeError):
                    # If there's any issue with the sum operation, assume no meaningful data
                    pass

            # Check for required columns
            required_cols = ['Test', 'Category', 'Item', 'Unit Cost (AUD $/unit)', 'Units']
            present_required = sum(1 for col in required_cols if col in df.columns)

            validation_results[model_name] = {
                'rows': total_rows,
                'columns': len(df.columns),
                'numeric_columns': total_numeric,
                'meaningful_numeric_columns': meaningful_data,
                'required_columns_present': present_required,
                'data_quality_score': (meaningful_data / max(total_numeric, 1)) * 100
            }

        return validation_results

def main():
    """Main extraction function."""
    excel_path = "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"

    if not Path(excel_path).exists():
        logger.error(f"Excel file not found: {excel_path}")
        return

    # Extract data
    extractor = ExcelDataExtractor(excel_path)
    labour_df = extractor.extract_labour_usage_data()

    # Split by test type
    test_data = extractor.split_by_test_type(labour_df)

    # Standardize and save
    standardized_data = {}
    for model_name, df in test_data.items():
        standardized_df = extractor.standardize_columns(df, model_name)
        standardized_data[model_name] = standardized_df

    # Save extracted data
    extractor.save_extracted_data(standardized_data)

    # Validate results
    validation = extractor.validate_extracted_data(standardized_data)

    # Print summary
    print("\n" + "="*60)
    print("EXCEL DATA EXTRACTION RESULTS")
    print("="*60)

    total_rows = sum(result['rows'] for result in validation.values())
    print(f"Total rows extracted: {total_rows}")
    print(f"Models extracted: {len(standardized_data)}")

    print("\nModel Details:")
    for model_name, result in validation.items():
        print(f"  {model_name}:")
        print(f"    Rows: {result['rows']}")
        print(f"    Columns: {result['columns']}")
        print(f"    Numeric columns: {result['numeric_columns']}")
        print(f"    Meaningful data: {result['meaningful_numeric_columns']} columns")
        print(f"    Data quality: {result['data_quality_score']:.1f}%")
    print("\n✅ Data extraction complete with calculated values preserved!")

if __name__ == "__main__":
    main()
