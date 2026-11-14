# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Extractor Components for Genomics Microcosting Data Pipeline.

This module contains concrete implementations of extractor components
for various data source types used in the genomics microcosting project.
"""

import re
from pathlib import Path
from typing import Unpack

import openpyxl
import polars as pl
lazy from openpyxl.worksheet.worksheet import Worksheet

from .config import SheetConfig, load_config
from .data_pipeline import Extractor
from .type_specifications import DataType, get_type_spec
lazy from .reader_options import CSVReadOptions, ParquetReadOptions


class ExcelExtractor(Extractor):
    """Extractor for Excel files with support for multi-level headers."""

    def __init__(
        self,
        name: str,
        source_path: str | Path,
        sheet_configs: dict[str, SheetConfig] | None = None,
        workbook_key: str = "validation",
    ) -> None:
        """Retain explicit sheet contracts or select the configured workbook."""
        super().__init__(name, source_path)

        if sheet_configs is None:
            config = load_config()
            workbook_config = config.get("workbooks", {})[workbook_key]
            if "sheets" not in workbook_config:
                message = "sheets"
                raise KeyError(message)
            self.sheet_configs = workbook_config["sheets"]
        else:
            self.sheet_configs = sheet_configs

        self.workbook_key = workbook_key

    def extract(self) -> dict[str, pl.DataFrame]:
        """Extract data from Excel file sheets."""
        self.logger.info("Extracting data from %s", self.source_path)

        # Load workbook
        wb = openpyxl.load_workbook(filename=self.source_path, data_only=True)

        extracted_data: dict[str, pl.DataFrame] = {}

        try:
            for sheet_name, sheet_config in self.sheet_configs.items():
                if sheet_name not in wb.sheetnames:
                    self.logger.warning(
                        "Sheet '%s' not found in workbook, skipping",
                        sheet_name,
                    )
                    continue

                self.logger.debug("Extracting sheet: %s", sheet_name)
                df = self._extract_sheet(wb[sheet_name], sheet_config)
                extracted_data[sheet_name] = df

        finally:
            wb.close()

        self.logger.info("Extracted %s sheets", len(extracted_data))
        return extracted_data

    def _extract_sheet(
        self,
        worksheet: Worksheet,
        sheet_config: SheetConfig,
    ) -> pl.DataFrame:
        """Extract a single sheet with proper header processing."""
        header_rows = sheet_config.get("header_rows", 1)
        data_starts_at = sheet_config.get("data_starts_at", header_rows + 1)

        rows = list(worksheet.iter_rows(values_only=True))
        columns: list[str] = []
        for index in range(len(rows[0]) if rows else 0):
            parts: list[str] = []
            last: object = None
            for row in rows[:header_rows]:
                value = row[index] if row[index] is not None else last
                if value is not None:
                    last = value
                    text = str(value).strip()
                    if text not in {"None", "nan", ""} and text not in parts:
                        parts.append(text)
            columns.append(" ".join(parts) or f"unnamed_{index}")
        columns = self._create_unique_column_names(columns)
        text_columns = sheet_config.get("string_columns", [])
        series: list[pl.Series] = []
        for index, name in enumerate(columns):
            normalised = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            canonical = sheet_config.get("column_mapping", {}).get(name, normalised)
            specification = get_type_spec(canonical)
            declared_text = specification is not None and specification.data_type in {
                DataType.STRING,
                DataType.CATEGORICAL,
            }
            values = [row[index] for row in rows[data_starts_at - 1 :]]
            if (
                declared_text
                or re.search(
                    r"(?:^|_)source(?:_\d+)?$",
                    re.sub(r"[^a-z0-9]+", "_", name.lower()),
                )
                or name in text_columns
                or re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") in text_columns
            ):
                series.append(
                    pl.Series(
                        name,
                        [str(v) if v is not None else None for v in values],
                        dtype=pl.String,
                    ),
                )
            else:
                parsed: list[float | None] = []
                for value in values:
                    try:
                        parsed.append(
                            float(value)
                            if isinstance(value, (str, int, float))
                            else None,
                        )
                    except ValueError:
                        parsed.append(None)
                series.append(pl.Series(name, parsed, dtype=pl.Float64))
        return pl.DataFrame(series)

    def _create_unique_column_names(self, columns: list[str]) -> list[str]:
        """Ensure column names are unique by appending a suffix if required."""
        used: set[str] = set()
        names: list[str] = []
        for base in columns:
            name = base
            suffix = 0
            while name in used:
                suffix += 1
                name = f"{base}_{suffix}"
            used.add(name)
            names.append(name)
        return names


class CSVExtractor(Extractor):
    """Extractor for CSV files."""

    def __init__(
        self,
        name: str,
        source_path: str | Path,
        **kwargs: Unpack[CSVReadOptions],
    ) -> None:
        """Retain keyword options for the native schema-qualified CSV reader."""
        super().__init__(name, source_path)
        self.kwargs: CSVReadOptions = kwargs

    def extract(self) -> pl.DataFrame:
        """Extract data from CSV file."""
        self.logger.info("Extracting data from CSV: %s", self.source_path)

        default_kwargs: CSVReadOptions = {"encoding": "utf-8"}
        default_kwargs.update(self.kwargs)

        if "schema" not in self.kwargs and "schema_overrides" not in self.kwargs:
            message = "Raw CSV extraction requires a declared schema or field overrides"
            raise ValueError(message)
        df = pl.read_csv(self.source_path, **default_kwargs)
        self.logger.info("Extracted %s rows from CSV", len(df))
        return df


class ParquetExtractor(Extractor):
    """Extractor for Parquet files."""

    def __init__(
        self,
        name: str,
        source_path: str | Path,
        **kwargs: Unpack[ParquetReadOptions],
    ) -> None:
        """Retain keyword options for the native Parquet reader."""
        super().__init__(name, source_path)
        self.kwargs: ParquetReadOptions = kwargs

    def extract(self) -> pl.DataFrame:
        """Extract data from Parquet file."""
        self.logger.info("Extracting data from Parquet: %s", self.source_path)

        df = pl.read_parquet(self.source_path, **self.kwargs)
        self.logger.info("Extracted %s rows from Parquet", len(df))
        return df


class MultiSourceExtractor(Extractor):
    """Extractor that can handle multiple data sources."""

    def __init__(self, name: str, source_paths: list[str | Path]) -> None:
        """Keep source order and use the first path as the primary identity."""
        super().__init__(name, source_paths[0])  # Use first path as primary
        self.source_paths = [Path(p) for p in source_paths]

    def extract(self) -> list[pl.DataFrame | dict[str, pl.DataFrame]]:
        """Extract data from multiple sources."""
        self.logger.info("Extracting data from %s sources", len(self.source_paths))

        extracted_data: list[pl.DataFrame | dict[str, pl.DataFrame]] = []
        for path in self.source_paths:
            if path.suffix.lower() == ".xlsx" or path.suffix.lower() == ".xlsm":
                extractor = ExcelExtractor(f"excel_{path.stem}", path)
                data = extractor.extract()
            elif path.suffix.lower() == ".csv":
                extractor = CSVExtractor(f"csv_{path.stem}", path)
                data = extractor.extract()
            elif path.suffix.lower() == ".parquet":
                extractor = ParquetExtractor(f"parquet_{path.stem}", path)
                data = extractor.extract()
            else:
                self.logger.warning("Unsupported file type: %s", path)
                continue

            extracted_data.append(data)

        return extracted_data
