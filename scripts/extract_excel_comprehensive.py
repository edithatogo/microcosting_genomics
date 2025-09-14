#!/usr/bin/env python3
"""
Comprehensive Excel Data Extraction with Cross-Sheet References

This script properly extracts data from Excel workbooks by resolving cross-sheet
references and preserving calculated values.
"""

import openpyxl
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveExcelExtractor:
    """Extracts data from Excel with proper cross-sheet reference resolution."""

    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)
        self.wb = None
        self.data_cache = {}

    def load_workbook(self):
        """Load Excel workbook with calculated values."""
        logger.info(f"Loading Excel workbook: {self.excel_path}")
        self.wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        logger.info(f"Loaded {len(self.wb.sheetnames)} sheets")

    def extract_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """Extract data from a specific sheet."""
        if self.wb is None:
            self.load_workbook()

        if sheet_name in self.data_cache:
            return self.data_cache[sheet_name]

        ws = self.wb[sheet_name]

        # Convert to pandas DataFrame
        data = []
        for row in ws.iter_rows(values_only=True):
            data.append(row)

        df = pd.DataFrame(data)
        self.data_cache[sheet_name] = df

        logger.info(f"Extracted {sheet_name}: {df.shape}")
        return df

    def resolve_cross_sheet_reference(self, formula: str) -> Optional[float]:
        """Resolve a cross-sheet reference like 'SheetName'!A1 to its calculated value."""
        if not formula or not isinstance(formula, str):
            return None

        # Match pattern like 'Sheet Name'!A1 or 'Sheet Name'!AN5
        pattern = r"'([^']+)'!([A-Z]+)(\d+)"
        match = re.match(pattern, formula.strip())

        if not match:
            return None

        sheet_name, col_letter, row_num = match.groups()

        try:
            # Get the referenced sheet
            ref_df = self.extract_sheet_data(sheet_name)
            if ref_df.empty:
                return None

            # Convert column letter to index (A=0, B=1, etc.)
            col_index = self.column_letter_to_index(col_letter)

            # Convert row number to 0-based index
            row_index = int(row_num) - 1  # Excel is 1-based, pandas is 0-based

            if row_index >= len(ref_df) or col_index >= len(ref_df.columns):
                return None

            value = ref_df.iloc[row_index, col_index]

            # Try to convert to numeric
            if pd.notna(value):
                try:
                    return float(str(value))
                except (ValueError, TypeError):
                    return None

        except Exception as e:
            logger.debug(f"Could not resolve reference {formula}: {e}")

        return None

    def column_letter_to_index(self, letter: str) -> int:
        """Convert Excel column letter to 0-based index."""
        result = 0
        for char in letter.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1

    def process_standardized_data(self, model_name: str) -> pd.DataFrame:
        """Process standardized CSV data and resolve cross-sheet references."""
        csv_path = Path(f"data/standardized/{model_name.replace(' ', '_').replace('(', '').replace(')', '')}_standardized.csv")

        if not csv_path.exists():
            logger.error(f"Standardized file not found: {csv_path}")
            return pd.DataFrame()

        # Load the standardized data
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded standardized {model_name}: {df.shape}")

        # Process each cell that contains a formula
        processed_df = df.copy()

        for row_idx in range(len(processed_df)):
            for col_idx, col_name in enumerate(processed_df.columns):
                cell_value = processed_df.iloc[row_idx, col_idx]

                if pd.notna(cell_value) and isinstance(cell_value, str):
                    # Check if it looks like an Excel formula
                    if cell_value.startswith("='") and "'!" in cell_value:
                        # Try to resolve the cross-sheet reference
                        resolved_value = self.resolve_cross_sheet_reference(cell_value)

                        if resolved_value is not None:
                            processed_df.iloc[row_idx, col_idx] = resolved_value
                            logger.debug(f"Resolved {cell_value} -> {resolved_value}")
                        else:
                            logger.debug(f"Could not resolve {cell_value}")

        # Convert appropriate columns to numeric
        for col in processed_df.columns:
            if col not in ['Test', 'Category', 'Sub-Category', 'Step']:  # Keep text columns as text
                try:
                    processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce')
                except (ValueError, TypeError):
                    pass

        return processed_df

    def extract_all_models(self) -> Dict[str, pd.DataFrame]:
        """Extract and process all genomic models."""
        models = ["Panel", "WES (P)", "WES (T)", "WGS (P)", "WGS (T)"]
        extracted_data = {}

        for model_name in models:
            logger.info(f"Processing model: {model_name}")
            df = self.process_standardized_data(model_name)

            if not df.empty:
                extracted_data[model_name] = df
                logger.info(f"Successfully processed {model_name}: {df.shape}")

        return extracted_data

    def validate_extracted_data(self, extracted_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """Validate the extracted data quality."""
        validation_results = {}

        for model_name, df in extracted_data.items():
            # Count numeric columns with actual values
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            meaningful_numeric = 0
            total_numeric_values = 0

            for col in numeric_cols:
                non_zero_count = (df[col].notna() & (df[col] != 0)).sum()
                if non_zero_count > 0:
                    meaningful_numeric += 1
                    total_numeric_values += non_zero_count

            validation_results[model_name] = {
                'rows': len(df),
                'columns': len(df.columns),
                'numeric_columns': len(numeric_cols),
                'meaningful_numeric_columns': meaningful_numeric,
                'total_numeric_values': total_numeric_values,
                'data_quality_score': (meaningful_numeric / max(len(numeric_cols), 1)) * 100
            }

        return validation_results

    def save_extracted_data(self, extracted_data: Dict[str, pd.DataFrame], output_dir: str = "data/extracted_proper"):
        """Save the properly extracted data."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for model_name, df in extracted_data.items():
            filename = f"{model_name.replace(' ', '_').replace('(', '').replace(')', '')}_extracted.csv"
            filepath = output_path / filename

            df.to_csv(filepath, index=False)
            logger.info(f"Saved {model_name} to {filepath}")

def main():
    """Main extraction function."""
    excel_path = "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"

    if not Path(excel_path).exists():
        logger.error(f"Excel file not found: {excel_path}")
        return

    # Extract data with cross-sheet reference resolution
    extractor = ComprehensiveExcelExtractor(excel_path)
    extracted_data = extractor.extract_all_models()

    # Validate results
    validation = extractor.validate_extracted_data(extracted_data)

    # Save extracted data
    extractor.save_extracted_data(extracted_data)

    # Print summary
    print("\n" + "="*60)
    print("COMPREHENSIVE EXCEL DATA EXTRACTION RESULTS")
    print("="*60)

    total_rows = sum(result['rows'] for result in validation.values())
    total_values = sum(result['total_numeric_values'] for result in validation.values())
    print(f"Total rows processed: {total_rows}")
    print(f"Total numeric values extracted: {total_values}")
    print(f"Models processed: {len(extracted_data)}")

    print("\nModel Details:")
    for model_name, result in validation.items():
        print(f"  {model_name}:")
        print(f"    Rows: {result['rows']}")
        print(f"    Columns: {result['columns']}")
        print(f"    Numeric columns: {result['numeric_columns']}")
        print(f"    Meaningful data: {result['meaningful_numeric_columns']} columns")
        print(f"    Total values: {result['total_numeric_values']}")
        print(f"    Data quality: {result['data_quality_score']:.1f}%")
    print("\n✅ Comprehensive data extraction complete!")

if __name__ == "__main__":
    main()
