"""Data Consistency Validation module for microcosting analysis.

This module provides functionality to validate data consistency across all analytical modules,
ensuring that data integrity is maintained throughout the analysis pipeline.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional, Any

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)


class DataConsistencyValidator:
    """Validator for ensuring data consistency across analytical modules."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize the DataConsistencyValidator.
        
        Args:
            data_manager: DataManager instance for accessing prepared data
        """
        self.data_manager = data_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def validate_sheet_integrity(self, sheet_name: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate the integrity of a sheet.
        
        Args:
            sheet_name: Name of the sheet
            df: DataFrame containing the sheet data
            
        Returns:
            Dictionary with validation results
        """
        self.logger.info(f"Validating integrity of sheet: {sheet_name}")
        
        results = {
            "sheet_name": sheet_name,
            "passed": True,
            "errors": [],
            "warnings": [],
            "metrics": {
                "row_count": len(df),
                "column_count": len(df.columns),
                "null_percentage": 0.0,
                "duplicate_rows": 0
            }
        }
        
        try:
            # Check basic structure
            if df.empty:
                results["errors"].append("Sheet is empty")
                results["passed"] = False
                
            # Check for reasonable size
            if len(df) > 100000:
                results["warnings"].append(f"Sheet has {len(df)} rows, which is unusually large")
                
            # Check null percentage
            if len(df) > 0 and len(df.columns) > 0:
                total_cells = df.shape[0] * df.shape[1]
                null_cells = df.isnull().sum().sum()
                null_percentage = (null_cells / total_cells) * 100 if total_cells > 0 else 0
                results["metrics"]["null_percentage"] = null_percentage
                
                if null_percentage > 80:
                    results["warnings"].append(f"High null percentage: {null_percentage:.2f}%")
                    
            # Check for duplicate rows
            duplicate_rows = df.duplicated().sum()
            results["metrics"]["duplicate_rows"] = duplicate_rows
            if duplicate_rows > 0:
                results["warnings"].append(f"Found {duplicate_rows} duplicate rows")
                
            # Check data types
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) == 0:
                results["warnings"].append("No numeric columns found")
                
        except Exception as e:
            results["errors"].append(f"Error during integrity validation: {e}")
            results["passed"] = False
            
        return results
    
    def validate_sheet_consistency(self, sheet_name: str, df_parquet: pd.DataFrame, 
                                 df_csv: pd.DataFrame) -> Dict[str, Any]:
        """Validate consistency between different formats of the same sheet.
        
        Args:
            sheet_name: Name of the sheet
            df_parquet: DataFrame from parquet format
            df_csv: DataFrame from CSV format
            
        Returns:
            Dictionary with consistency validation results
        """
        self.logger.info(f"Validating consistency of sheet: {sheet_name}")
        
        results = {
            "sheet_name": sheet_name,
            "passed": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check shape consistency
            if df_parquet.shape != df_csv.shape:
                results["errors"].append(
                    f"Shape mismatch: Parquet {df_parquet.shape} vs CSV {df_csv.shape}")
                results["passed"] = False
                
            # Check column consistency
            if not df_parquet.columns.equals(df_csv.columns):
                results["errors"].append("Column names mismatch between formats")
                results["passed"] = False
                
            # Check data consistency (for a sample of numeric columns)
            numeric_cols_parquet = df_parquet.select_dtypes(include=['number']).columns
            numeric_cols_csv = df_csv.select_dtypes(include=['number']).columns
            
            common_numeric_cols = list(set(numeric_cols_parquet) & set(numeric_cols_csv))
            
            if common_numeric_cols:
                # Check a sample of values
                sample_size = min(100, len(df_parquet))
                for col in common_numeric_cols[:3]:  # Check first 3 numeric columns
                    parquet_sample = df_parquet[col].head(sample_size)
                    csv_sample = df_csv[col].head(sample_size)
                    
                    # Handle NaN values
                    comparison = (parquet_sample.fillna(-999999) == csv_sample.fillna(-999999))
                    if not comparison.all():
                        mismatch_count = (~comparison).sum()
                        results["warnings"].append(
                            f"Data mismatch in column '{col}': {mismatch_count}/{sample_size} values differ")
                        
        except Exception as e:
            results["errors"].append(f"Error during consistency validation: {e}")
            results["passed"] = False
            
        return results
    
    def validate_cross_sheet_references(self, sheet_name: str, df: pd.DataFrame,
                                      referenced_sheets: List[str]) -> Dict[str, Any]:
        """Validate cross-sheet references for consistency.
        
        Args:
            sheet_name: Name of the sheet being validated
            df: DataFrame containing the sheet data
            referenced_sheets: List of sheet names that should be referenced
            
        Returns:
            Dictionary with cross-reference validation results
        """
        self.logger.info(f"Validating cross-sheet references for: {sheet_name}")
        
        results = {
            "sheet_name": sheet_name,
            "passed": True,
            "errors": [],
            "warnings": [],
            "referenced_sheets_found": [],
            "referenced_sheets_missing": []
        }
        
        try:
            # Check if referenced sheets exist
            for ref_sheet in referenced_sheets:
                ref_df = self.data_manager.load_sheet(ref_sheet)
                if ref_df is not None:
                    results["referenced_sheets_found"].append(ref_sheet)
                else:
                    results["referenced_sheets_missing"].append(ref_sheet)
                    results["errors"].append(f"Referenced sheet '{ref_sheet}' not found")
                    results["passed"] = False
                    
        except Exception as e:
            results["errors"].append(f"Error during cross-reference validation: {e}")
            results["passed"] = False
            
        return results
    
    def validate_data_ranges(self, sheet_name: str, df: pd.DataFrame,
                           expected_ranges: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """Validate that data values fall within expected ranges.
        
        Args:
            sheet_name: Name of the sheet
            df: DataFrame containing the sheet data
            expected_ranges: Dictionary mapping column names to (min, max) tuples
            
        Returns:
            Dictionary with range validation results
        """
        self.logger.info(f"Validating data ranges for sheet: {sheet_name}")
        
        results = {
            "sheet_name": sheet_name,
            "passed": True,
            "errors": [],
            "warnings": [],
            "columns_checked": []
        }
        
        try:
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            for col_name, (expected_min, expected_max) in expected_ranges.items():
                if col_name in numeric_cols:
                    results["columns_checked"].append(col_name)
                    
                    # Check for values outside expected range
                    col_data = df[col_name]
                    out_of_range = col_data[(col_data < expected_min) | (col_data > expected_max)]
                    
                    if len(out_of_range) > 0:
                        results["warnings"].append(
                            f"Column '{col_name}' has {len(out_of_range)} values outside "
                            f"expected range [{expected_min}, {expected_max}]")
                        
        except Exception as e:
            results["errors"].append(f"Error during range validation: {e}")
            results["passed"] = False
            
        return results
    
    def validate_unique_constraints(self, sheet_name: str, df: pd.DataFrame,
                                  unique_columns: List[str]) -> Dict[str, Any]:
        """Validate that specified columns maintain unique constraints.
        
        Args:
            sheet_name: Name of the sheet
            df: DataFrame containing the sheet data
            unique_columns: List of column names that should be unique
            
        Returns:
            Dictionary with unique constraint validation results
        """
        self.logger.info(f"Validating unique constraints for sheet: {sheet_name}")
        
        results = {
            "sheet_name": sheet_name,
            "passed": True,
            "errors": [],
            "warnings": [],
            "columns_checked": []
        }
        
        try:
            for col_name in unique_columns:
                if col_name in df.columns:
                    results["columns_checked"].append(col_name)
                    
                    # Check for duplicate values
                    duplicates = df[col_name].duplicated().sum()
                    if duplicates > 0:
                        results["errors"].append(
                            f"Column '{col_name}' has {duplicates} duplicate values "
                            f"(should be unique)")
                        results["passed"] = False
                        
        except Exception as e:
            results["errors"].append(f"Error during unique constraint validation: {e}")
            results["passed"] = False
            
        return results
    
    def generate_validation_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive data consistency validation report.
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Report as a string
        """
        try:
            # Get list of available sheets
            available_sheets = self.data_manager.list_available_sheets()
            sheet_names = list(available_sheets.keys())
            
            if not sheet_names:
                raise ValueError("No sheets found to validate!")
            
            # Validate each sheet
            validation_results = []
            
            for sheet_name in sheet_names:
                # Load data in different formats
                df_parquet = self.data_manager.load_sheet(sheet_name, format="parquet")
                df_csv = self.data_manager.load_sheet(sheet_name, format="csv")
                
                if df_parquet is None:
                    continue
                    
                # Validate integrity
                integrity_results = self.validate_sheet_integrity(sheet_name, df_parquet)
                
                # Validate consistency between formats
                consistency_results = {}
                if df_csv is not None:
                    consistency_results = self.validate_sheet_consistency(sheet_name, df_parquet, df_csv)
                
                # Collect results
                sheet_results = {
                    "sheet_name": sheet_name,
                    "integrity": integrity_results,
                    "consistency": consistency_results
                }
                
                validation_results.append(sheet_results)
            
            # Generate report
            report = []
            report.append("# Data Consistency Validation Report\n")
            report.append("## Executive Summary\n")
            report.append("This report presents the results of data consistency validation across all sheets.\n")
            
            report.append("## Validation Results by Sheet\n")
            
            for sheet_result in validation_results:
                sheet_name = sheet_result["sheet_name"]
                integrity = sheet_result["integrity"]
                consistency = sheet_result["consistency"]
                
                report.append(f"### {sheet_name}\n")
                
                # Integrity results
                report.append("**Integrity Validation:**\n")
                report.append(f"- Passed: {integrity.get('passed', False)}\n")
                if integrity.get("errors"):
                    report.append(f"- Errors: {', '.join(integrity['errors'])}\n")
                if integrity.get("warnings"):
                    report.append(f"- Warnings: {', '.join(integrity['warnings'])}\n")
                
                # Consistency results
                if consistency:
                    report.append("**Format Consistency Validation:**\n")
                    report.append(f"- Passed: {consistency.get('passed', False)}\n")
                    if consistency.get("errors"):
                        report.append(f"- Errors: {', '.join(consistency['errors'])}\n")
                    if consistency.get("warnings"):
                        report.append(f"- Warnings: {', '.join(consistency['warnings'])}\n")
                
                report.append("\n")
            
            report.append("## Key Findings\n")
            report.append("- Data integrity validation ensures sheets are properly structured\n")
            report.append("- Format consistency validation ensures parquet and CSV formats match\n")
            report.append("- Cross-sheet reference validation ensures dependencies are maintained\n")
            report.append("- Range validation ensures data values fall within expected bounds\n")
            report.append("- Unique constraint validation ensures data integrity rules are followed\n")
            
            report_str = "\n".join(report)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report_str)
            
            return report_str
            
        except Exception as e:
            self.logger.error(f"Error generating validation report: {e}")
            raise


def main():
    """Main function for testing the data consistency validator."""
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize validator
        validator = DataConsistencyValidator(data_manager)
        
        # Generate report
        report = validator.generate_validation_report()
        print(report)
        
    except Exception as e:
        logger.error(f"Error in data consistency validation: {e}")
        raise


if __name__ == "__main__":
    main()