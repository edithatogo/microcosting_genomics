# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Unified data management for microcosting analysis.

This module provides a consistent interface for loading, saving, and managing
all data sheets in the microcosting analysis, ensuring consistent treatment
of all sheets regardless of their source or purpose.
"""

import json
import math
import sys
from numbers import Integral, Real
from pathlib import Path
from typing import Any, Protocol, cast, runtime_checkable
lazy from collections.abc import Iterable, Iterator

import polars as pl

from .config import load_config
from .logging_config import get_logger
from .type_specifications import (
    TypeSpecification,
    apply_type_conversions,
    get_type_spec,
    validate_dataframe_types,
)

logger = get_logger(__name__)


@runtime_checkable
class HeaderTable(Protocol):
    """Narrow import contract for legacy workbook header fixtures."""

    @property
    def columns(self) -> Iterable[object]:
        """Expose the source header levels without assuming scalar types."""
        ...

    def itertuples(
        self,
        *,
        index: bool,
        name: None,
    ) -> Iterator[tuple[object, ...]]:
        """Iterate row values in their retained source order."""
        ...


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


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

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize the DataManager.

        Args:
            data_dir (Path, optional): Base directory, or the existing default.

        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.config = load_config()

        module_path = Path(__file__).resolve()
        source_root = module_path.parents[2]
        # An editable checkout retains its historical project-root defaults;
        # an installed package uses the caller's working directory instead of
        # writing data and reports inside the Python installation.
        workspace = (
            source_root
            if module_path.parent.parent.name == "src"
            and (source_root / "pyproject.toml").is_file()
            else Path.cwd()
        )
        if data_dir is None:
            self.data_dir = workspace / "data"
        else:
            self.data_dir = Path(data_dir)

        self.prepared_dir = self.data_dir / "prepared"
        self.publication_dir = workspace / "publication"

        # Create directories if they don't exist
        self.prepared_dir.mkdir(parents=True, exist_ok=True)
        self.publication_dir.mkdir(parents=True, exist_ok=True)

        # Supported formats for consistent handling
        self.supported_formats = ["parquet", "csv"]

        self.logger.info(
            "DataManager initialized with data directory: %s",
            self.data_dir,
        )

    def get_sheet_names(self) -> list[str]:
        """Get list of all available sheet names from configuration.

        Returns:
            List[str]: List of sheet names configured for processing

        """
        workbook_key = self.config.get("default_workbook", "main")
        try:
            sheets = list(
                self.config.get("workbooks", {})[workbook_key].get("sheets", {}).keys(),
            )
        except KeyError:
            self.logger.exception("Configuration error")
            return []
        self.logger.info("Found %d configured sheets: %s", len(sheets), sheets)
        return sheets

    def load_sheet_polars(
        self,
        sheet_name: str,
        file_format: str = "parquet",
        *,
        csv_schema: dict[str, pl.DataType | type[pl.DataType]] | None = None,
    ) -> pl.DataFrame | None:
        """Read native typed tables; CSV requires explicit schema at ingestion.

        Parquet is the preferred typed interchange. CSV requires a complete
        declared schema rather than guessing identifier or date types.
        """
        if file_format not in self.supported_formats:
            return None
        path = (
            self.prepared_dir / f"{self._sanitize_sheet_name(sheet_name)}.{file_format}"
        )
        if not path.exists():
            return None
        if file_format == "parquet":
            return pl.read_parquet(path)
        if csv_schema is None:
            message = "Native CSV ingestion requires an explicit field schema"
            raise ValueError(message)
        return pl.read_csv(path, schema=csv_schema)

    def save_sheet_polars(
        self,
        sheet_name: str,
        frame: pl.DataFrame,
        formats: list[str] | None = None,
    ) -> bool:
        """Save native Polars tables without pandas or silent dtype conversion."""
        selected = formats if formats is not None else self.supported_formats
        if any(kind not in self.supported_formats for kind in selected):
            return False
        for kind in selected:
            path = self.prepared_dir / f"{self._sanitize_sheet_name(sheet_name)}.{kind}"
            if kind == "parquet":
                frame.write_parquet(path)
            else:
                frame.write_csv(path)
        return True

    def load_sheet(
        self,
        sheet_name: str,
        file_format: str = "parquet",
        *,
        csv_schema: dict[str, pl.DataType | type[pl.DataType]] | None = None,
    ) -> pl.DataFrame | None:
        """Read a native Polars table with explicit CSV field contracts."""
        return self.load_sheet_polars(sheet_name, file_format, csv_schema=csv_schema)

    def save_sheet(
        self,
        sheet_name: str,
        df: pl.DataFrame,
        formats: list[str] | None = None,
    ) -> bool:
        """Save a sheet in specified formats with consistent naming.

        Args:
            sheet_name (str): Name of the sheet to save
            df (pl.DataFrame): DataFrame containing the sheet data
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
            file_path = self.prepared_dir / f"{sanitized_name}.{file_format}"
            try:
                if file_format == "parquet":
                    df_clean.write_parquet(file_path)
                else:  # csv
                    df_clean.write_csv(file_path)

                self.logger.info(
                    "Saved sheet '%s' to %s with shape %s",
                    sheet_name,
                    file_path,
                    df_clean.shape,
                )
            except Exception:
                self.logger.exception(
                    "Error saving sheet '%s' to %s",
                    sheet_name,
                    file_path,
                )
                success = False

        return success

    def save_for_publication(
        self,
        sheet_name: str,
        df: pl.DataFrame,
        metadata: dict[str, Any] | None = None,
        *,
        include_examples: bool = False,
    ) -> bool:
        """Save a sheet and its metadata for publication with consistent formatting.

        Args:
            sheet_name (str): Name of the sheet to save
            df (pl.DataFrame): DataFrame containing the sheet data
            metadata (Dict[str, Any], optional): Metadata about the sheet
            include_examples: Include source examples only when explicitly selected.

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
            df_clean.write_csv(csv_path)
            self.logger.info(
                "Saved publication data for '%s' to %s",
                sheet_name,
                csv_path,
            )

            # Save data dictionary
            dictionary_path = self.publication_dir / f"{sanitized_name}_dictionary.csv"
            self._create_data_dictionary(
                df_clean,
                dictionary_path,
                include_examples=include_examples,
            )

            # Save metadata if provided
            if metadata:
                metadata_path = self.publication_dir / f"{sanitized_name}_metadata.json"
                self._save_metadata(metadata, metadata_path)

        except Exception:
            self.logger.exception(
                "Error saving publication data for sheet '%s'",
                sheet_name,
            )
            success = False

        return success

    @staticmethod
    def _sanitize_sheet_name(sheet_name: str) -> str:
        """Retain the established private filename helper for existing callers."""
        return DataManager.sanitize_sheet_name(sheet_name)

    @staticmethod
    def sanitize_sheet_name(sheet_name: str) -> str:
        """Sanitize sheet name for use in file names.

        Args:
            sheet_name (str): Original sheet name

        Returns:
            str: Sanitized sheet name suitable for file naming

        """
        # Replace problematic characters and standardize naming
        sanitized = "".join(
            c for c in sheet_name if c.isalnum() or c in (" ", "_", "-")
        )
        sanitized = sanitized.strip().lower().replace(" ", "_").replace("-", "_")
        # Handle special cases like starting with numbers
        if sanitized and sanitized[0].isdigit():
            sanitized = f"sheet_{sanitized}"
        return sanitized

    def _fix_duplicate_columns(self, df: object) -> pl.DataFrame:
        """Retain the existing compatibility hook for external header records."""
        return self.normalize_headers(df)

    def normalize_headers(self, df: object) -> pl.DataFrame:
        """Normalise external workbook labels before constructing a native frame."""
        if isinstance(df, pl.DataFrame):
            return df.clone()
        if not isinstance(df, HeaderTable):
            message = "Expected a Polars frame or a workbook header table"
            raise TypeError(message)
        names: list[str] = []
        used: set[str] = set()
        for label in df.columns:
            base = self._convert_multiindex_tuple_to_string(label)
            name = base
            suffix = 1
            while name in used:
                suffix += 1
                name = f"{base}_{suffix}"
            used.add(name)
            names.append(name)
        rows = list(df.itertuples(index=False, name=None))
        return pl.DataFrame(rows, schema=names, orient="row", strict=False)

    def _convert_multiindex_tuple_to_string(self, col: object) -> str:
        """Flatten supplied header levels without losing numeric labels."""
        if not isinstance(col, tuple):
            return "unnamed" if _missing(col) else str(col)
        parts = [
            self._convert_part_to_string(part)
            for part in cast("tuple[object, ...]", col)
            if not _missing(part) and str(part).strip()
        ]
        return "_".join(parts) if parts else "unnamed"

    def _convert_part_to_string(self, part: object) -> str:
        """Retain integral header labels without an artificial decimal suffix."""
        if isinstance(part, bool):
            return str(part)
        if isinstance(part, Integral):
            return str(int(part))
        if isinstance(part, Real):
            value = float(part)
            return str(int(value)) if value.is_integer() else str(value)
        return str(part)

    def _fix_multiindex_columns(self, df: object) -> pl.DataFrame:
        """Normalise multi-level source labels at the input boundary."""
        return self._fix_duplicate_columns(df)

    def _fix_regular_columns(self, df: object) -> pl.DataFrame:
        """Normalise flat source labels at the input boundary."""
        return self._fix_duplicate_columns(df)

    def _ensure_unique_columns(self, df: object) -> pl.DataFrame:
        """Resolve collisions deterministically before native construction."""
        return self._fix_duplicate_columns(df)

    def _create_data_dictionary(
        self,
        df: pl.DataFrame,
        output_path: Path,
        *,
        include_examples: bool = False,
    ) -> None:
        """Create a data dictionary for a DataFrame.

        Args:
            df (pl.DataFrame): DataFrame to create dictionary for
            output_path (Path): Path to save the dictionary
            include_examples: Include source examples only when explicitly selected.

        """
        dictionary_data: list[dict[str, str | int | None]] = [
            {
                "column_name": col,
                "data_type": str(df[col].dtype),
                "sample_values": str(df[col].drop_nulls().head(3).to_list())
                if include_examples
                else "",
                "null_count": int(df[col].null_count()),
                "unique_count": int(df[col].drop_nulls().n_unique())
                if df[col].dtype == pl.String
                else None,
            }
            for col in df.columns
        ]

        dictionary_df = pl.DataFrame(dictionary_data)
        dictionary_df.write_csv(output_path)
        self.logger.info("Created data dictionary at %s", output_path)

    def _save_metadata(self, metadata: dict[str, Any], output_path: Path) -> None:
        """Save metadata to a JSON file.

        Args:
            metadata (Dict[str, Any]): Metadata to save
            output_path (Path): Path to save the metadata

        """
        with output_path.open("w") as f:
            json.dump(metadata, f, indent=2, default=str)
        self.logger.info("Saved metadata at %s", output_path)

    def list_available_sheets(self) -> dict[str, list[str]]:
        """List all available sheets and their available formats.

        Returns:
            Dict[str, List[str]]: Dictionary mapping sheet names to available formats

        """
        available_sheets: dict[str, list[str]] = {}

        # Check prepared directory
        if self.prepared_dir.exists():
            for file_path in self.prepared_dir.iterdir():
                if file_path.is_file():
                    name_parts = file_path.stem.split(".")
                    sheet_name = (
                        ".".join(name_parts[:-1])
                        if len(name_parts) > 1
                        else name_parts[0]
                    )
                    file_format = file_path.suffix.lstrip(".")

                    if sheet_name not in available_sheets:
                        available_sheets[sheet_name] = []
                    if file_format not in available_sheets[sheet_name]:
                        available_sheets[sheet_name].append(file_format)

        self.logger.info("Found %d available sheets", len(available_sheets))
        return available_sheets

    def validate_sheet_types(self, sheet_name: str, df: pl.DataFrame) -> list[str]:
        """Validate data types for a sheet against type specifications.

        Args:
            sheet_name (str): Name of the sheet to validate
            df (pl.DataFrame): DataFrame to validate

        Returns:
            List[str]: List of validation error messages

        """
        errors: list[str] = []

        # Get column mapping for this sheet
        workbook_key = self.config.get("default_workbook", "main")
        try:
            sheet_config = self.config.get("workbooks", {})[workbook_key].get(
                "sheets",
                {},
            )[sheet_name]
            column_mapping = sheet_config.get("column_mapping", {})
        except KeyError:
            self.logger.warning("No column mapping found for sheet: %s", sheet_name)
            return errors

        # Build type specifications for mapped columns
        type_specs: dict[str, TypeSpecification] = {}
        for standard_col in column_mapping.values():
            type_spec = get_type_spec(standard_col)
            if type_spec:
                type_specs[standard_col] = type_spec

        # Validate types if we have specifications
        if type_specs:
            try:
                validation_errors = validate_dataframe_types(df, type_specs)
                errors.extend(validation_errors)
            except Exception as e:
                self.logger.exception("Type validation failed for sheet %s", sheet_name)
                errors.append(f"Error during type validation: {e}")

        return errors

    def apply_sheet_type_conversions(
        self,
        sheet_name: str,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """Apply type conversions for a sheet based on type specifications.

        Args:
            sheet_name (str): Name of the sheet
            df (pl.DataFrame): DataFrame to convert

        Returns:
            pl.DataFrame: DataFrame with applied type conversions

        """
        # Get column mapping for this sheet
        workbook_key = self.config.get("default_workbook", "main")
        try:
            sheet_config = self.config.get("workbooks", {})[workbook_key].get(
                "sheets",
                {},
            )[sheet_name]
            column_mapping = sheet_config.get("column_mapping", {})
        except KeyError:
            self.logger.warning("No column mapping found for sheet: %s", sheet_name)
            return df

        # Build type specifications for mapped columns
        type_specs: dict[str, TypeSpecification] = {}
        for standard_col in column_mapping.values():
            type_spec = get_type_spec(standard_col)
            if type_spec:
                type_specs[standard_col] = type_spec

        if not type_specs:
            return df
        try:
            df_converted = apply_type_conversions(df, type_specs)
            self.logger.info("Applied type conversions for sheet: %s", sheet_name)
        except Exception:
            self.logger.exception("Error applying type conversions for %s", sheet_name)
            return df
        return df_converted


def _write_line(message: str) -> None:
    """Preserve one line of the existing command-line demonstration output."""
    sys.stdout.write(message + "\n")


def main() -> None:
    """Exercise the existing DataManager command-line demonstration."""
    _write_line("Testing DataManager...")

    # Initialize DataManager
    dm = DataManager()

    # List configured sheets
    sheets = dm.get_sheet_names()
    _write_line(f"Configured sheets: {sheets}")

    # List available sheets
    available = dm.list_available_sheets()
    _write_line(f"Available sheets: {available}")

    # Try to load a sheet if any exist
    if sheets:
        sheet_name = sheets[0]
        df = dm.load_sheet(sheet_name)
        if df is not None:
            _write_line(f"Successfully loaded '{sheet_name}' with shape {df.shape}")
        else:
            _write_line(f"Failed to load '{sheet_name}'")

    _write_line("DataManager test complete.")


if __name__ == "__main__":
    main()
