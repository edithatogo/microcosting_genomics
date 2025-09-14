"""
Extractor Components for Genomics Microcosting Data Pipeline

This module contains concrete implementations of extractor components
for various data source types used in the genomics microcosting project.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

import pandas as pd
import openpyxl

from .data_pipeline import Extractor
from .config import load_config


class ExcelExtractor(Extractor):
    """Extractor for Excel files with support for multi-level headers."""

    def __init__(self,
                 name: str,
                 source_path: Union[str, Path],
                 sheet_configs: Optional[Dict] = None,
                 workbook_key: str = "validation"):
        super().__init__(name, source_path)

        if sheet_configs is None:
            config = load_config()
            self.sheet_configs = config["workbooks"][workbook_key]["sheets"]
        else:
            self.sheet_configs = sheet_configs

        self.workbook_key = workbook_key

    def extract(self) -> Dict[str, pd.DataFrame]:
        """Extract data from Excel file sheets."""
        self.logger.info(f"Extracting data from {self.source_path}")

        # Load workbook
        wb = openpyxl.load_workbook(filename=self.source_path, data_only=True)

        extracted_data = {}

        try:
            for sheet_name, sheet_config in self.sheet_configs.items():
                if sheet_name not in wb.sheetnames:
                    self.logger.warning(f"Sheet '{sheet_name}' not found in workbook, skipping")
                    continue

                self.logger.debug(f"Extracting sheet: {sheet_name}")
                df = self._extract_sheet(wb[sheet_name], sheet_config)
                extracted_data[sheet_name] = df

        finally:
            wb.close()

        self.logger.info(f"Extracted {len(extracted_data)} sheets")
        return extracted_data

    def _extract_sheet(self, worksheet, sheet_config: Dict) -> pd.DataFrame:
        """Extract a single sheet with proper header processing."""
        header_rows = sheet_config.get("header_rows", 1)
        data_starts_at = sheet_config.get("data_starts_at", header_rows + 1)

        # Convert worksheet to DataFrame
        data = []
        for row in worksheet.iter_rows(values_only=True):
            data.append(row)

        df_raw = pd.DataFrame(data)

        if header_rows > 0:
            # Enhanced header processing with duplicate removal
            header_df = df_raw.iloc[:header_rows].copy()
            header_df = header_df.ffill(axis=0)

            columns = []
            for i in range(header_df.shape[1]):
                parts = []
                for row_idx in range(header_rows):
                    val = header_df.iloc[row_idx, i]
                    if pd.notna(val) and str(val).strip() not in ['None', 'nan', '']:
                        parts.append(str(val).strip())

                # Remove duplicates while preserving order
                seen = set()
                unique_parts = []
                for part in parts:
                    if part not in seen:
                        unique_parts.append(part)
                        seen.add(part)

                name = " ".join(unique_parts).replace("nan", "").strip()
                name = " ".join(name.split())  # Normalize whitespace

                if not name:
                    name = f"unnamed_{i}"
                columns.append(name)

            # Ensure column names are unique
            columns = self._create_unique_column_names(columns)
        else:
            columns = [f"col_{i}" for i in range(len(df_raw.columns))]

        df = df_raw.iloc[data_starts_at - 1 :].reset_index(drop=True)
        df.columns = columns

        # Apply type conversion
        string_columns = sheet_config.get("string_columns", [])
        for col in df.columns:
            if col in string_columns:
                continue  # Keep as string
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def _create_unique_column_names(self, columns: List[str]) -> List[str]:
        """Ensure column names are unique by appending a suffix if required."""
        seen: dict[str, int] = {}
        unique_columns = []
        for col in columns:
            if col in seen:
                seen[col] += 1
                unique_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 1
                unique_columns.append(col)
        return unique_columns


class CSVExtractor(Extractor):
    """Extractor for CSV files."""

    def __init__(self,
                 name: str,
                 source_path: Union[str, Path],
                 **kwargs):
        super().__init__(name, source_path)
        self.kwargs = kwargs

    def extract(self) -> pd.DataFrame:
        """Extract data from CSV file."""
        self.logger.info(f"Extracting data from CSV: {self.source_path}")

        default_kwargs = {
            'encoding': 'utf-8',
            'low_memory': False
        }
        default_kwargs.update(self.kwargs)

        df = pd.read_csv(self.source_path, **default_kwargs)
        self.logger.info(f"Extracted {len(df)} rows from CSV")
        return df


class ParquetExtractor(Extractor):
    """Extractor for Parquet files."""

    def __init__(self,
                 name: str,
                 source_path: Union[str, Path],
                 **kwargs):
        super().__init__(name, source_path)
        self.kwargs = kwargs

    def extract(self) -> pd.DataFrame:
        """Extract data from Parquet file."""
        self.logger.info(f"Extracting data from Parquet: {self.source_path}")

        df = pd.read_parquet(self.source_path, **self.kwargs)
        self.logger.info(f"Extracted {len(df)} rows from Parquet")
        return df


class MultiSourceExtractor(Extractor):
    """Extractor that can handle multiple data sources."""

    def __init__(self, name: str, source_paths: List[Union[str, Path]]):
        super().__init__(name, source_paths[0])  # Use first path as primary
        self.source_paths = [Path(p) for p in source_paths]

    def extract(self) -> List[Any]:
        """Extract data from multiple sources."""
        self.logger.info(f"Extracting data from {len(self.source_paths)} sources")

        extracted_data = []
        for path in self.source_paths:
            if path.suffix.lower() == '.xlsx' or path.suffix.lower() == '.xlsm':
                extractor = ExcelExtractor(f"excel_{path.stem}", path)
                data = extractor.extract()
            elif path.suffix.lower() == '.csv':
                extractor = CSVExtractor(f"csv_{path.stem}", path)
                data = extractor.extract()
            elif path.suffix.lower() == '.parquet':
                extractor = ParquetExtractor(f"parquet_{path.stem}", path)
                data = extractor.extract()
            else:
                self.logger.warning(f"Unsupported file type: {path}")
                continue

            extracted_data.append(data)

        return extracted_data