"""Unified data management for microcosting analysis.

This module provides a consistent interface for loading, saving, and managing
all data sheets in the microcosting analysis, ensuring consistent treatment
of all sheets regardless of their source or purpose.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

from .config import load_config
from .logging_config import get_logger
from .type_specifications import get_type_spec, apply_type_conversions, validate_dataframe_types

logger = get_logger(__name__)


class DataManager:
    """Manages all data sheets with consistent handling across formats.

    This class provides a unified interface for loading, saving, and managing
    all data sheets in the microcosting analysis. It ensures consistent treatment
    of all sheets regardless of their source or purpose.

    Attributes:
        config (dict): Configuration data loaded from config.yaml
        data_dir (Path): Base directory for all data files
        prepared_dir (Path): Directory for prepared data files
        publication_dir (Path): Directory for publication-ready files
        supported_formats (List[str]): List of supported file formats
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the DataManager.

        Args:
            data_dir (Path, optional): Base data directory. If None, uses default location.
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.config = load_config()
        
        if data_dir is None:
            self.data_dir = Path(__file__).resolve().parents[2] / "data"
        else:
            self.data_dir = Path(data_dir)
            
        self.prepared_dir = self.data_dir / "prepared"
        self.publication_dir = Path(__file__).resolve().parents[2] / "publication"
        
        # Create directories if they don't exist
        self.prepared_dir.mkdir(parents=True, exist_ok=True)
        self.publication_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported formats for consistent handling
        self.supported_formats = ["parquet", "csv"]
        
        self.logger.info("DataManager initialized with data directory: %s", self.data_dir)

    def get_sheet_names(self) -> List[str]:
        """Get list of all available sheet names from configuration.

        Returns:
            List[str]: List of sheet names configured for processing
        """
        workbook_key = self.config.get("default_workbook", "main")
        try:
            sheets = list(self.config["workbooks"][workbook_key]["sheets"].keys())
            self.logger.info("Found %d configured sheets: %s", len(sheets), sheets)
            return sheets
        except KeyError as e:
            self.logger.error("Configuration error: %s", e)
            return []

    def load_sheet(self, sheet_name: str, file_format: str = "parquet") -> Optional[pd.DataFrame]:
        """Load a specific sheet in the specified format.

        Args:
            sheet_name (str): Name of the sheet to load
            file_format (str, optional): Format to load ('parquet' or 'csv'). Defaults to 'parquet'.

        Returns:
            Optional[pd.DataFrame]: DataFrame containing the sheet data, or None if not found
        """
        if file_format not in self.supported_formats:
            self.logger.error("Unsupported format: %s", file_format)
            return None
            
        # Sanitize sheet name for file naming
        sanitized_name = self._sanitize_sheet_name(sheet_name)
        file_path = self.prepared_dir / f"{sanitized_name}.{file_format}"
        
        if not file_path.exists():
            self.logger.warning("File not found: %s", file_path)
            return None
            
        try:
            if file_format == "parquet":
                df = pd.read_parquet(file_path)
            else:  # csv
                df = pd.read_csv(file_path)
                
            self.logger.info("Loaded sheet '%s' from %s with shape %s", 
                           sheet_name, file_path, df.shape)
            return df
        except Exception as e:
            self.logger.error("Error loading sheet '%s' from %s: %s", 
                            sheet_name, file_path, e)
            return None

    def save_sheet(self, sheet_name: str, df: pd.DataFrame, 
                   formats: Optional[List[str]] = None) -> bool:
        """Save a sheet in specified formats with consistent naming.

        Args:
            sheet_name (str): Name of the sheet to save
            df (pd.DataFrame): DataFrame containing the sheet data
            formats (List[str], optional): Formats to save ('parquet', 'csv'). 
                                         If None, saves in all supported formats.

        Returns:
            bool: True if successfully saved, False otherwise
        """
        if formats is None:
            formats = self.supported_formats
            
        # Validate formats
        invalid_formats = [f for f in formats if f not in self.supported_formats]
        if invalid_formats:
            self.logger.error("Invalid formats specified: %s", invalid_formats)
            return False
            
        # Sanitize sheet name for file naming
        sanitized_name = self._sanitize_sheet_name(sheet_name)
        success = True
        
        # Fix duplicate column names before saving
        df_clean = self._fix_duplicate_columns(df)
        
        for file_format in formats:
            try:
                file_path = self.prepared_dir / f"{sanitized_name}.{file_format}"
                
                if file_format == "parquet":
                    df_clean.to_parquet(file_path, index=False)
                else:  # csv
                    df_clean.to_csv(file_path, index=False)
                    
                self.logger.info("Saved sheet '%s' to %s with shape %s", 
                               sheet_name, file_path, df_clean.shape)
            except Exception as e:
                self.logger.error("Error saving sheet '%s' to %s: %s", 
                                sheet_name, file_path, e)
                success = False
                
        return success

    def save_for_publication(self, sheet_name: str, df: pd.DataFrame, 
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save a sheet and its metadata for publication with consistent formatting.

        Args:
            sheet_name (str): Name of the sheet to save
            df (pd.DataFrame): DataFrame containing the sheet data
            metadata (Dict[str, Any], optional): Metadata about the sheet

        Returns:
            bool: True if successfully saved, False otherwise
        """
        # Sanitize sheet name for file naming
        sanitized_name = self._sanitize_sheet_name(sheet_name)
        success = True
        
        # Fix duplicate column names before saving
        df_clean = self._fix_duplicate_columns(df)
        
        try:
            # Save data in CSV format for publication
            csv_path = self.publication_dir / f"{sanitized_name}.csv"
            df_clean.to_csv(csv_path, index=False)
            self.logger.info("Saved publication data for '%s' to %s", 
                           sheet_name, csv_path)
                           
            # Save data dictionary
            dictionary_path = self.publication_dir / f"{sanitized_name}_dictionary.csv"
            self._create_data_dictionary(df_clean, dictionary_path)
            
            # Save metadata if provided
            if metadata:
                metadata_path = self.publication_dir / f"{sanitized_name}_metadata.json"
                self._save_metadata(metadata, metadata_path)
                
        except Exception as e:
            self.logger.error("Error saving publication data for sheet '%s': %s", 
                            sheet_name, e)
            success = False
            
        return success

    def _sanitize_sheet_name(self, sheet_name: str) -> str:
        """Sanitize sheet name for use in file names.

        Args:
            sheet_name (str): Original sheet name

        Returns:
            str: Sanitized sheet name suitable for file naming
        """
        # Replace problematic characters and standardize naming
        sanitized = "".join(c for c in sheet_name if c.isalnum() or c in (" ", "_", "-"))
        sanitized = sanitized.strip().lower().replace(" ", "_").replace("-", "_")
        # Handle special cases like starting with numbers
        if sanitized and sanitized[0].isdigit():
            sanitized = f"sheet_{sanitized}"
        return sanitized

    def _fix_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix duplicate column names in a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with potential duplicate column names

        Returns:
            pd.DataFrame: DataFrame with unique column names
        """
        if isinstance(df.columns, pd.MultiIndex):
            return self._fix_multiindex_columns(df)
        else:
            return self._fix_regular_columns(df)

    def _fix_multiindex_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix duplicate column names in a MultiIndex DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with MultiIndex columns

        Returns:
            pd.DataFrame: DataFrame with unique column names
        """
        try:
            new_columns = []
            for col in df.columns:
                new_col = self._convert_multiindex_tuple_to_string(col)
                new_columns.append(new_col)

            df_copy = df.copy()
            df_copy.columns = new_columns
            return self._ensure_unique_columns(df_copy)
        except Exception as e:
            self.logger.warning("Error handling MultiIndex columns: %s", e)
            # Fallback to generic column names
            df_copy = df.copy()
            df_copy.columns = [f"col_{i}" for i in range(len(df.columns))]
            return df_copy

    def _convert_multiindex_tuple_to_string(self, col: Any) -> str:
        """Convert a MultiIndex tuple to a string column name.

        Args:
            col (Any): MultiIndex column (tuple or other type)

        Returns:
            str: String representation of the column name
        """
        if not isinstance(col, tuple):
            return str(col) if pd.notna(col) else "unnamed"

        parts = []
        for part in col:
            if pd.notna(part) and str(part).strip():
                parts.append(self._convert_part_to_string(part))

        return "_".join(parts) if parts else "unnamed"

    def _convert_part_to_string(self, part: Any) -> str:
        """Convert a MultiIndex part to string with proper type handling.

        Args:
            part (Any): Part to convert

        Returns:
            str: String representation
        """
        import numpy as np

        if isinstance(part, (np.bool_, bool)):
            return str(part)
        elif isinstance(part, (int, float, np.integer, np.floating)):
            if isinstance(part, (int, np.integer)) or (hasattr(part, 'is_integer') and part.is_integer()):
                return str(int(part))
            else:
                return str(part)
        else:
            return str(part)

    def _fix_regular_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix duplicate column names in a regular index DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with regular index columns

        Returns:
            pd.DataFrame: DataFrame with unique column names
        """
        df_copy = df.copy()
        columns = list(df_copy.columns)

        # Check for duplicates and handle them
        seen = {}
        new_columns = []
        for col in columns:
            col_str = str(col) if pd.notna(col) else "unnamed"
            if col_str in seen:
                seen[col_str] += 1
                new_col = f"{col_str}_{seen[col_str]}"
            else:
                seen[col_str] = 1
                new_col = col_str
            new_columns.append(new_col)

        # Only rename if there are actual duplicates
        if len(set(new_columns)) != len(new_columns):
            df_copy.columns = new_columns

        return self._ensure_unique_columns(df_copy)

    def _ensure_unique_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all column names are unique by adding suffixes if needed.

        Args:
            df (pd.DataFrame): DataFrame that may have duplicate columns

        Returns:
            pd.DataFrame: DataFrame with guaranteed unique column names
        """
        columns = list(df.columns)
        seen = {}
        final_columns = []

        for col in columns:
            col_str = str(col) if pd.notna(col) else "unnamed"
            if col_str in seen:
                seen[col_str] += 1
                new_col = f"{col_str}_{seen[col_str]}"
            else:
                seen[col_str] = 1
                new_col = col_str
            final_columns.append(new_col)

        df_copy = df.copy()
        df_copy.columns = final_columns
        return df_copy

    def _create_data_dictionary(self, df: pd.DataFrame, output_path: Path) -> None:
        """Create a data dictionary for a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame to create dictionary for
            output_path (Path): Path to save the dictionary
        """
        dictionary_data = []
        for col in df.columns:
            dictionary_data.append({
                "column_name": col,
                "data_type": str(df[col].dtype),
                "sample_values": str(df[col].dropna().head(3).tolist()),
                "null_count": int(df[col].isnull().sum()),
                "unique_count": int(df[col].nunique()) if df[col].dtype == 'object' else None
            })
        
        dictionary_df = pd.DataFrame(dictionary_data)
        dictionary_df.to_csv(output_path, index=False)
        self.logger.info("Created data dictionary at %s", output_path)

    def _save_metadata(self, metadata: Dict[str, Any], output_path: Path) -> None:
        """Save metadata to a JSON file.

        Args:
            metadata (Dict[str, Any]): Metadata to save
            output_path (Path): Path to save the metadata
        """
        import json
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        self.logger.info("Saved metadata at %s", output_path)

    def list_available_sheets(self) -> Dict[str, List[str]]:
        """List all available sheets and their available formats.

        Returns:
            Dict[str, List[str]]: Dictionary mapping sheet names to available formats
        """
        available_sheets = {}
        
        # Check prepared directory
        if self.prepared_dir.exists():
            for file_path in self.prepared_dir.iterdir():
                if file_path.is_file():
                    name_parts = file_path.stem.split('.')
                    sheet_name = '.'.join(name_parts[:-1]) if len(name_parts) > 1 else name_parts[0]
                    file_format = file_path.suffix.lstrip('.')
                    
                    if sheet_name not in available_sheets:
                        available_sheets[sheet_name] = []
                    if file_format not in available_sheets[sheet_name]:
                        available_sheets[sheet_name].append(file_format)
                        
        self.logger.info("Found %d available sheets", len(available_sheets))
        return available_sheets

    def validate_sheet_types(self, sheet_name: str, df: pd.DataFrame) -> List[str]:
        """Validate data types for a sheet against type specifications.

        Args:
            sheet_name (str): Name of the sheet to validate
            df (pd.DataFrame): DataFrame to validate

        Returns:
            List[str]: List of validation error messages
        """
        errors = []

        # Get column mapping for this sheet
        workbook_key = self.config.get("default_workbook", "main")
        try:
            sheet_config = self.config["workbooks"][workbook_key]["sheets"][sheet_name]
            column_mapping = sheet_config.get("column_mapping", {})
        except KeyError:
            self.logger.warning("No column mapping found for sheet: %s", sheet_name)
            return errors

        # Build type specifications for mapped columns
        type_specs = {}
        for _, standard_col in column_mapping.items():
            type_spec = get_type_spec(standard_col)
            if type_spec:
                type_specs[standard_col] = type_spec

        # Validate types if we have specifications
        if type_specs:
            try:
                validation_errors = validate_dataframe_types(df, type_specs)
                errors.extend(validation_errors)
            except Exception as e:
                errors.append(f"Error during type validation: {e}")

        return errors

    def apply_sheet_type_conversions(self, sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Apply type conversions for a sheet based on type specifications.

        Args:
            sheet_name (str): Name of the sheet
            df (pd.DataFrame): DataFrame to convert

        Returns:
            pd.DataFrame: DataFrame with applied type conversions
        """
        # Get column mapping for this sheet
        workbook_key = self.config.get("default_workbook", "main")
        try:
            sheet_config = self.config["workbooks"][workbook_key]["sheets"][sheet_name]
            column_mapping = sheet_config.get("column_mapping", {})
        except KeyError:
            self.logger.warning("No column mapping found for sheet: %s", sheet_name)
            return df

        # Build type specifications for mapped columns
        type_specs = {}
        for _, standard_col in column_mapping.items():
            type_spec = get_type_spec(standard_col)
            if type_spec:
                type_specs[standard_col] = type_spec

        # Apply type conversions if we have specifications
        if type_specs:
            try:
                df_converted = apply_type_conversions(df, type_specs)
                self.logger.info("Applied type conversions for sheet: %s", sheet_name)
                return df_converted
            except Exception as e:
                self.logger.error("Error applying type conversions for %s: %s", sheet_name, e)
                return df
        else:
            return df


def main():
    """Main function for testing the DataManager."""
    print("Testing DataManager...")
    
    # Initialize DataManager
    dm = DataManager()
    
    # List configured sheets
    sheets = dm.get_sheet_names()
    print(f"Configured sheets: {sheets}")
    
    # List available sheets
    available = dm.list_available_sheets()
    print(f"Available sheets: {available}")
    
    # Try to load a sheet if any exist
    if sheets:
        sheet_name = sheets[0]
        df = dm.load_sheet(sheet_name)
        if df is not None:
            print(f"Successfully loaded '{sheet_name}' with shape {df.shape}")
        else:
            print(f"Failed to load '{sheet_name}'")
    
    print("DataManager test complete.")


if __name__ == "__main__":
    main()